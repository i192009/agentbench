import hashlib
from importlib.metadata import version as package_version
from typing import Any

from opentelemetry.propagate import inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.config import ROOT, settings
from agentbench.database import Agent, AgentVersion, Dataset, DatasetVersion, EvaluationRun, RunEvent
from agentbench.schemas import AgentConfig, ProviderSpec, RunRequest, checksum
from agentbench.services.datasets import export_version


def source_snapshot() -> dict[str, Any]:
    sources = {
        str(file.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted((ROOT / "backend" / "agentbench").rglob("*.py"))
    }
    return {
        "files": sources,
        "tree_checksum": checksum(sources),
        "uv_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()
        if (ROOT / "uv.lock").exists()
        else None,
    }


async def create_run(
    db: AsyncSession, project_id: str, request: RunRequest, execution_backend: str = "celery"
) -> EvaluationRun:
    agent = await db.get(AgentVersion, request.agent_version_id)
    dataset = await db.get(DatasetVersion, request.dataset_version_id)
    if agent is None or dataset is None:
        raise ValueError("Agent or dataset version does not exist")
    agent_owner, dataset_owner = (
        await db.get(Agent, agent.agent_id),
        await db.get(Dataset, dataset.dataset_id),
    )
    if (
        not agent_owner
        or not dataset_owner
        or agent_owner.project_id != project_id
        or dataset_owner.project_id != project_id
    ):
        raise ValueError("Agent and dataset must belong to this project")
    AgentConfig.model_validate(agent.config)
    if request.mode == "live":
        ProviderSpec.model_validate(agent.config["model"])
    payload = await export_version(db, dataset)
    if len(payload.cases) * request.repetitions > 1000:
        raise ValueError("A run supports at most 1000 case executions including repetitions")
    body = payload.model_dump(mode="json")
    if checksum(body) != dataset.checksum:
        raise ValueError("Dataset checksum mismatch; cannot create reproducible run")
    if not dataset.frozen:
        dataset.frozen = True
    if request.baseline_id:
        baseline = await db.get(EvaluationRun, request.baseline_id)
        if baseline is None or baseline.project_id != project_id or baseline.dataset_version_id != dataset.id:
            raise ValueError("Baseline must use the identical project and dataset version")
        if baseline.status != "COMPLETED":
            raise ValueError("Baseline must be completed")
    snapshot: dict[str, Any] = {
        "agent": agent.config,
        "agent_checksum": agent.checksum,
        "dataset": body,
        "dataset_checksum": dataset.checksum,
        "request": request.model_dump(),
        "execution_backend": execution_backend,
        "dependencies": {
            name: package_version(name) for name in ["mcp", "langgraph", "ragas", "deepeval", "mlflow"]
        },
    }
    carrier: dict[str, str] = {}
    inject(carrier)
    snapshot["trace_context"] = carrier
    cfg = settings()
    snapshot["judge_spec"] = (
        ProviderSpec.model_validate(
            {
                "provider": "openai",
                "model": cfg.judge_model,
                "input_per_million": cfg.judge_input_per_million,
                "output_per_million": cfg.judge_output_per_million,
                "pricing_version": "configured-judge-v1",
            }
        ).model_dump()
        if "judge" in request.evaluators and cfg.judge_enabled
        else None
    )
    snapshot["source_snapshot"] = source_snapshot()
    run = EvaluationRun(
        project_id=project_id,
        agent_version_id=agent.id,
        dataset_version_id=dataset.id,
        total=len(payload.cases) * request.repetitions,
        snapshot=snapshot,
    )
    db.add(run)
    await db.flush()
    db.add(RunEvent(run_id=run.id, kind="RunCreated", data={"total": run.total}))
    return run


async def results_for(db: AsyncSession, run_id: str):
    from agentbench.database import CaseResultRow
    from agentbench.schemas import CaseResult

    rows = (
        await db.scalars(
            select(CaseResultRow).where(CaseResultRow.run_id == run_id).order_by(CaseResultRow.case_id)
        )
    ).all()
    return [CaseResult.model_validate(row.body) for row in rows]
