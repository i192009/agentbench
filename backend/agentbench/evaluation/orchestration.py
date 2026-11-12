import asyncio
import copy
from time import perf_counter

import structlog
from opentelemetry.propagate import extract
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from agentbench.agents.adapters import error_execution, execute
from agentbench.config import settings
from agentbench.database import CaseResultRow, EvaluationRun, RunEvent, transaction
from agentbench.evaluation.extensions import LiveJudge, deepeval_metrics, judge_metric, ragas_metrics
from agentbench.evaluation.quality_gates import apply_gate
from agentbench.evaluation.regression import aggregate, compare
from agentbench.evaluation.scoring import score
from agentbench.mcp.client import Sandbox
from agentbench.observability import CASES, JUDGE_ERRORS, LATENCY, RUNS, SAFETY, TOOL_ERRORS, tracer
from agentbench.schemas import AgentConfig, CaseResult, DatasetFile, RunRequest, checksum, now, uid
from agentbench.services.runs import results_for, source_snapshot
from agentbench.tracking import log_run


async def event(run_id: str, kind: str, **data):
    async with transaction() as db:
        db.add(RunEvent(run_id=run_id, kind=kind, data=data))


async def cancelled(run_id: str) -> bool:
    async with transaction() as db:
        row = await db.get(EvaluationRun, run_id)
        return row.cancel_requested


async def persist_result(run_id: str, result: CaseResult):
    async with transaction() as db:
        # Lock the parent before inserting FK children; consistent ordering avoids
        # FK key-share / parent FOR UPDATE upgrade deadlocks across concurrent cases.
        row = await db.get(EvaluationRun, run_id, with_for_update=True)
        # Unique(run_id,case_id) is the final protection against duplicate delivery.
        insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
        statement = (
            insert(CaseResultRow)
            .values(
                id=uid(),
                created_at=now(),
                run_id=run_id,
                case_id=result.case_id,
                attempt_id=result.attempt_id,
                passed=result.passed,
                body=result.model_dump(mode="json"),
            )
            .on_conflict_do_nothing(index_elements=["run_id", "case_id"])
        )
        await db.execute(statement)
        count = await db.scalar(
            select(func.count()).select_from(CaseResultRow).where(CaseResultRow.run_id == run_id)
        )
        row.completed = count
        db.add(
            RunEvent(
                run_id=run_id,
                kind="CaseCompleted" if result.passed else "CaseFailed",
                data={"case_id": result.case_id, "completed": count, "total": row.total},
            )
        )


async def evaluate_run(run_id: str):
    async with transaction() as db:
        row = await db.get(EvaluationRun, run_id)
        if row is None:
            raise ValueError("Run not found")
        context = extract(row.snapshot.get("trace_context", {}))
    with tracer.start_as_current_span(
        "evaluation.run", context=context, attributes={"agentbench.run_id": run_id}
    ):
        structlog.get_logger().info("evaluation_started", service="worker", run_id=run_id)
        try:
            result = await _evaluate_run(run_id)
        except ValueError as exc:
            async with transaction() as db:
                failed = await db.get(EvaluationRun, run_id, with_for_update=True)
                if failed and failed.status not in {"COMPLETED", "CANCELLED"}:
                    failed.status, failed.error, failed.finished_at = "FAILED", str(exc)[:1000], now()
            raise
        structlog.get_logger().info(
            "evaluation_finished",
            service="worker",
            run_id=run_id,
            gate=result.get("gate", {}).get("status", "not-completed"),
        )
        return result


async def _evaluate_run(run_id: str):
    started = perf_counter()
    async with transaction() as db:
        run = await db.get(EvaluationRun, run_id, with_for_update=True)
        if run is None:
            raise ValueError("Run not found")
        if run.status in {"COMPLETED", "COMPLETED_WITH_ERRORS", "CANCELLED", "FAILED"}:
            return run.summary
        if run.cancel_requested:
            run.status, run.finished_at = "CANCELLED", now()
            return {}
        snapshot = copy.deepcopy(run.snapshot)
        expected_source = snapshot.get("source_snapshot")
        if expected_source:
            actual_source = source_snapshot()
            if expected_source["tree_checksum"] != actual_source["tree_checksum"] or expected_source.get(
                "uv_lock_sha256"
            ) != actual_source.get("uv_lock_sha256"):
                raise ValueError(
                    "Worker source/dependency lock differs from the immutable run snapshot; deploy the matching revision or create a new evaluation"
                )
        if (
            checksum(snapshot["agent"]) != snapshot["agent_checksum"]
            or checksum(snapshot["dataset"]) != snapshot["dataset_checksum"]
        ):
            raise ValueError("Immutable snapshot checksum mismatch")
        run.status, run.started_at = "RUNNING", now()
        existing = {r.case_id for r in await results_for(db, run_id)}
    request = RunRequest.model_validate(snapshot["request"])
    config, dataset = (
        AgentConfig.model_validate(snapshot["agent"]),
        DatasetFile.model_validate(snapshot["dataset"]),
    )
    budget_lock = asyncio.Lock()
    reserved_cost = 0.0
    async with transaction() as db:
        previous = await results_for(db, run_id)
        reserved_cost = sum(
            r.execution.usage.cost_usd or (c.budget.cost_usd if request.mode == "live" else 0)
            for r in previous
            for c in dataset.cases
            if r.case_id.split("::repeat-")[0] == c.id
        )
    semaphore = asyncio.Semaphore(settings().case_concurrency)
    await event(run_id, "RunStarted", resumed_cases=len(existing))

    async def one(case, sandbox):
        nonlocal reserved_cost
        async with semaphore:
            if case.id in existing or await cancelled(run_id):
                return
            await event(run_id, "CaseStarted", case_id=case.id)
            reserve = (
                case.budget.cost_usd
                if request.mode == "live" or ("judge" in request.evaluators and settings().judge_enabled)
                else 0.0
            )
            async with budget_lock:
                if reserved_cost + reserve > request.max_cost_usd:
                    result = score(
                        case,
                        error_execution(
                            case, request.mode, ValueError("Run cost reservation exhausted"), run_id
                        ),
                    )
                    await persist_result(run_id, result)
                    return
                reserved_cost += reserve
            with tracer.start_as_current_span(
                "agentbench.case", attributes={"agentbench.case_id": case.id, "agentbench.run_id": run_id}
            ):
                try:
                    async with asyncio.timeout(case.budget.timeout_seconds + 2):
                        execution = await execute(config, case, sandbox, request.mode, run_id)
                except Exception as exc:
                    execution = error_execution(case, request.mode, exc, run_id)
                await event(run_id, "AgentExecutionCompleted", case_id=case.id)
                await event(run_id, "ScoringStarted", case_id=case.id)
                with tracer.start_as_current_span("evaluation.score"):
                    result = score(case, execution)
                try:
                    if "ragas" in request.evaluators:
                        result.metrics.extend(await ragas_metrics(case, execution))
                    if "deepeval" in request.evaluators:
                        result.metrics.extend(await deepeval_metrics(case, execution))
                    if "judge" in request.evaluators:
                        result.metrics.append(
                            await judge_metric(
                                case,
                                execution,
                                LiveJudge(snapshot.get("judge_spec")) if settings().judge_enabled else None,
                            )
                        )
                        # Judge usage is available only after inference. Re-evaluate the budget
                        # using total agent + judge usage rather than the pre-judge snapshot.
                        updated_budget = next(m for m in score(case, execution).metrics if m.name == "budget")
                        result.metrics = [updated_budget if m.name == "budget" else m for m in result.metrics]
                except Exception as exc:
                    from agentbench.schemas import Metric

                    result.metrics.append(
                        Metric(name="extension_error", status="ERROR", reason=str(exc)[:500])
                    )
                result.passed = all(m.status in {"PASS", "NOT_APPLICABLE"} for m in result.metrics)
                await persist_result(run_id, result)
                structlog.get_logger().info(
                    "case_completed",
                    service="worker",
                    run_id=run_id,
                    case_id=case.id,
                    agent_id=config.name,
                    trace_id=execution.trace[0].trace_id if execution.trace else None,
                    passed=result.passed,
                )
                CASES.labels("pass" if result.passed else "fail").inc()
                LATENCY.observe(execution.latency_ms / 1000)
                TOOL_ERRORS.inc(sum(c.status == "error" for c in execution.tool_calls))
                if any(m.name == "safety" and m.status == "FAIL" for m in result.metrics):
                    SAFETY.inc()
                JUDGE_ERRORS.inc(sum(m.status == "ERROR" for m in result.metrics))

    try:
        async with asyncio.timeout(settings().run_timeout_seconds):
            async with Sandbox() as sandbox:
                tasks = []
                # Bounded work batches: never allocate one task per unbounded upload.
                for repetition in range(request.repetitions):
                    for source in dataset.cases:
                        case = source.model_copy(deep=True)
                        if request.repetitions > 1:
                            case.id += f"::repeat-{repetition + 1}"
                        tasks.append(case)
                for offset in range(0, len(tasks), settings().case_concurrency):
                    await asyncio.gather(
                        *(one(c, sandbox) for c in tasks[offset : offset + settings().case_concurrency])
                    )
                    if await cancelled(run_id):
                        break
        async with transaction() as db:
            results = await results_for(db, run_id)
            comparison = None
            if request.baseline_id:
                baseline = await db.get(EvaluationRun, request.baseline_id)
                if baseline.snapshot["dataset_checksum"] != snapshot["dataset_checksum"]:
                    raise ValueError("Cannot compare different dataset checksums")
                comparison = compare(
                    await results_for(db, request.baseline_id),
                    results,
                    request.gate_policy.minimum_sample_size,
                )
            run = await db.get(EvaluationRun, run_id)
            was_cancelled, total = run.cancel_requested, run.total
        summary = aggregate(results)
        summary["comparison"] = comparison
        summary["gate"] = apply_gate(
            summary, request.gate_policy, total, {c.category for c in dataset.cases}, comparison
        )
        summary["elapsed_seconds"] = perf_counter() - started
        summary["cases_per_second"] = len(results) / max(summary["elapsed_seconds"], 0.001)
        summary["mode"] = request.mode
        # No database transaction stays open during MLflow network IO.
        summary["tracking"] = (
            await asyncio.to_thread(log_run, run_id, snapshot, summary, results)
            if results
            else {"status": "DISABLED"}
        )
        async with transaction() as db:
            run = await db.get(EvaluationRun, run_id, with_for_update=True)
            run.status = (
                "CANCELLED"
                if was_cancelled
                else "COMPLETED_WITH_ERRORS"
                if any(
                    r.execution.status == "error"
                    and not next(
                        (c.expected.error for c in dataset.cases if r.case_id.split("::repeat-")[0] == c.id),
                        None,
                    )
                    for r in results
                )
                or summary["evaluator_errors"]
                else "COMPLETED"
            )
            run.summary, run.finished_at, run.completed = summary, now(), len(results)
            db.add(
                RunEvent(
                    run_id=run_id,
                    kind="RunCancelled" if was_cancelled else "RunCompleted",
                    data={"status": run.status, "gate": summary["gate"]["status"]},
                )
            )
            RUNS.labels(run.status).inc()
        return summary
    except BaseException as exc:
        async with transaction() as db:
            run = await db.get(EvaluationRun, run_id)
            run.status, run.error, run.finished_at = (
                "FAILED",
                f"{type(exc).__name__}: {str(exc)[:1000]}",
                now(),
            )
        raise
