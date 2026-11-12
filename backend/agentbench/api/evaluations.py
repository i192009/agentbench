import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.api.common import access, audit, editor, owned, page, public
from agentbench.database import Baseline, CaseResultRow, EvaluationRun, RunEvent, User, get_db, transaction
from agentbench.evaluation.quality_gates import apply_gate
from agentbench.evaluation.regression import aggregate, compare
from agentbench.reports import export_report, report_dict
from agentbench.schemas import GatePolicy, Page, RunRequest
from agentbench.services.runs import create_run, results_for

router = APIRouter(prefix="/projects/{project_id}", tags=["Evaluations"])


@router.post("/runs", status_code=201)
async def new_run(
    project_id: str, body: RunRequest, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    run = await create_run(db, project_id, body)
    audit(db, user, "run.created", run.id)
    await db.commit()
    return public(run)


@router.post("/runs/{run_id}/start", status_code=202)
async def start(
    project_id: str, run_id: str, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    from agentbench.workers import evaluate

    run = await owned(db, EvaluationRun, run_id, project_id)
    if run.status not in {"CREATED", "QUEUED"}:
        raise HTTPException(409, "Run has already started or is terminal")
    run.status = "QUEUED"
    audit(db, user, "run.queued", run.id)
    await db.commit()
    # The persisted queue state is the outbox. Beat redispatches after broker outages.
    dispatched = True
    try:
        await asyncio.to_thread(evaluate.apply_async, args=[run_id], retry=False)
    except Exception:
        dispatched = False
    return {"id": run.id, "status": run.status, "dispatched": dispatched}


@router.get("/runs", response_model=Page)
async def runs(
    project_id: str,
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    query = select(EvaluationRun).where(EvaluationRun.project_id == project_id)
    if status:
        query = query.where(EvaluationRun.status == status)
    # List rows omit large immutable snapshots, retaining configuration labels.
    result = await page(db, query.order_by(EvaluationRun.created_at.desc()), offset, limit)
    for row in result["items"]:
        snapshot = row.pop("snapshot")
        row["agent"] = snapshot["agent"]["name"]
        row["version"] = snapshot["agent"]["version"]
        row["dataset"] = snapshot["dataset"]["name"]
        row["mode"] = snapshot["request"]["mode"]
    return result


@router.get("/runs/{run_id}")
async def run_detail(
    project_id: str, run_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)
) -> dict:
    return public(await owned(db, EvaluationRun, run_id, project_id))


@router.post("/runs/{run_id}/cancel")
async def cancel(
    project_id: str, run_id: str, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    run = await owned(db, EvaluationRun, run_id, project_id)
    if run.status in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELLED"}:
        raise HTTPException(409, "Run is terminal")
    run.cancel_requested = True
    if run.status in {"CREATED", "QUEUED"}:
        run.status = "CANCELLED"
    audit(db, user, "run.cancel.requested", run.id)
    await db.commit()
    return {"status": run.status, "cancel_requested": True}


@router.get("/runs/{run_id}/results", response_model=Page)
async def case_results(
    project_id: str,
    run_id: str,
    failed_only: bool = False,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    await owned(db, EvaluationRun, run_id, project_id)
    query = select(CaseResultRow).where(CaseResultRow.run_id == run_id)
    if failed_only:
        query = query.where(CaseResultRow.passed.is_(False))
    return await page(db, query.order_by(CaseResultRow.case_id), offset, limit)


@router.get("/runs/{run_id}/results/{case_id}/trace")
async def trace(
    project_id: str,
    run_id: str,
    case_id: str,
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await owned(db, EvaluationRun, run_id, project_id)
    row = await db.scalar(
        select(CaseResultRow).where(CaseResultRow.run_id == run_id, CaseResultRow.case_id == case_id)
    )
    if not row:
        raise HTTPException(404, "Case result not found")
    return row.body


@router.get("/runs/{run_id}/events")
async def events(
    project_id: str,
    run_id: str,
    request: Request,
    after: str | None = None,
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    await owned(db, EvaluationRun, run_id, project_id)
    # Cursor is a persisted event timestamp+UUID. Batch size bounds streaming memory.
    cursor = after or request.headers.get("Last-Event-ID")
    await db.rollback()

    async def stream():
        nonlocal cursor
        for _ in range(900):
            if await request.is_disconnected():
                return
            async with transaction() as session:
                query = select(RunEvent).where(RunEvent.run_id == run_id)
                if cursor:
                    previous = await session.get(RunEvent, cursor)
                    if previous and previous.run_id == run_id:
                        query = query.where(
                            (RunEvent.created_at > previous.created_at)
                            | ((RunEvent.created_at == previous.created_at) & (RunEvent.id > previous.id))
                        )
                batch = (
                    await session.scalars(query.order_by(RunEvent.created_at, RunEvent.id).limit(100))
                ).all()
                run = await session.get(EvaluationRun, run_id)
                status = run.status
            for item in batch:
                cursor = item.id
                yield f"id: {item.id}\nevent: {item.kind}\ndata: {json.dumps(item.data)}\n\n"
            if status in {"COMPLETED", "COMPLETED_WITH_ERRORS", "CANCELLED", "FAILED"} and len(batch) < 100:
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/comparisons")
async def comparison(
    project_id: str,
    baseline_id: str,
    candidate_id: str,
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
) -> dict:
    baseline = await owned(db, EvaluationRun, baseline_id, project_id)
    candidate = await owned(db, EvaluationRun, candidate_id, project_id)
    if baseline.snapshot["dataset_checksum"] != candidate.snapshot["dataset_checksum"]:
        raise HTTPException(422, "Paired comparison requires identical dataset checksums")
    if baseline.status not in {"COMPLETED", "COMPLETED_WITH_ERRORS"} or candidate.status not in {
        "COMPLETED",
        "COMPLETED_WITH_ERRORS",
    }:
        raise HTTPException(409, "Both runs must be completed before comparison")
    return compare(await results_for(db, baseline_id), await results_for(db, candidate_id))


@router.post("/runs/{run_id}/baseline", status_code=201)
async def pin_baseline(
    project_id: str, run_id: str, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    run = await owned(db, EvaluationRun, run_id, project_id)
    if run.status != "COMPLETED" or run.summary.get("gate", {}).get("status") != "PASS":
        raise HTTPException(409, "Only completed passing runs may be promoted")
    row = Baseline(
        project_id=project_id, dataset_version_id=run.dataset_version_id, run_id=run.id, actor_id=user.id
    )
    db.add(row)
    audit(db, user, "baseline.promoted", run.id)
    await db.commit()
    return public(row)


@router.get("/baselines", response_model=Page)
async def baselines(project_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)):
    return await page(
        db, select(Baseline).where(Baseline.project_id == project_id).order_by(Baseline.created_at.desc())
    )


@router.post("/runs/{run_id}/gate")
async def gate(
    project_id: str,
    run_id: str,
    body: GatePolicy,
    user: User = Depends(editor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    run = await owned(db, EvaluationRun, run_id, project_id)
    result = apply_gate(
        aggregate(await results_for(db, run_id)),
        body,
        run.total,
        {c["category"] for c in run.snapshot["dataset"]["cases"]},
        run.summary.get("comparison"),
    )
    audit(db, user, "gate.evaluated", run.id, result=result)
    await db.commit()
    return result


@router.get("/runs/{run_id}/export")
async def export(
    project_id: str,
    run_id: str,
    format: str = Query("json", pattern="^(json|md|csv)$"),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    run = await owned(db, EvaluationRun, run_id, project_id)
    report = report_dict(run.id, run.snapshot, run.summary, await results_for(db, run_id))
    return Response(
        export_report(report, format),
        media_type={"json": "application/json", "md": "text/markdown", "csv": "text/csv"}[format],
        headers={"Content-Disposition": f'attachment; filename="agentbench-{run.id}.{format}"'},
    )


@router.get("/analytics")
async def analytics(
    project_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)
) -> dict:
    rows = (
        await db.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.project_id == project_id)
            .order_by(EvaluationRun.created_at.desc())
            .limit(100)
        )
    ).all()
    total = await db.scalar(
        select(func.count()).select_from(EvaluationRun).where(EvaluationRun.project_id == project_id)
    )
    return {
        "total_runs": total,
        "window": "latest 100 runs",
        "runs": [
            {
                "id": r.id,
                "created_at": r.created_at,
                "agent": r.snapshot["agent"]["name"],
                "version": r.snapshot["agent"]["version"],
                "model": r.snapshot["agent"]["model"],
                "prompt_version": r.snapshot["agent"]["prompt_version"],
                "status": r.status,
                "summary": r.summary,
            }
            for r in rows
        ],
    }
