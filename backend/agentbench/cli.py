import asyncio
import json
from pathlib import Path

import typer
from sqlalchemy import select

from agentbench.database import (
    Agent,
    AgentVersion,
    Dataset,
    DatasetVersion,
    EvaluationRun,
    Project,
    transaction,
)
from agentbench.evaluation.orchestration import evaluate_run
from agentbench.evaluation.regression import compare
from agentbench.reports import export_report, report_dict
from agentbench.schemas import GatePolicy, RunRequest
from agentbench.services.runs import create_run, results_for

app = typer.Typer(
    no_args_is_help=True, help="AgentBench administrator CLI. Offline runs never imply live model reasoning."
)
evaluation = typer.Typer(no_args_is_help=True)
app.add_typer(evaluation, name="eval")


@app.command("register-live")
def register_live(agent: str = "Financial Research", version: str = "live-configured"):
    """Freeze the explicitly configured provider model/pricing as a new agent version."""
    from agentbench.config import settings
    from agentbench.schemas import AgentConfig, ProviderSpec, checksum

    cfg = settings()
    spec = ProviderSpec.model_validate(
        {
            "provider": "openai",
            "model": cfg.provider_model,
            "input_per_million": cfg.provider_input_per_million,
            "output_per_million": cfg.provider_output_per_million,
            "pricing_version": "configured-provider-v1",
        }
    )

    async def operation():
        async with transaction() as db:
            project = await db.scalar(select(Project).where(Project.name == "Agent Reliability Lab"))
            if not project:
                raise ValueError("Seed the demo project first")
            row = await db.scalar(select(Agent).where(Agent.project_id == project.id, Agent.name == agent))
            if not row:
                raise ValueError("Unknown agent")
            base = await db.scalar(
                select(AgentVersion).where(AgentVersion.agent_id == row.id).order_by(AgentVersion.created_at)
            )
            if base is None:
                raise ValueError("Register a base agent configuration first")
            config = AgentConfig.model_validate(
                {**base.config, "version": version, "model": spec.model_dump()}
            )
            digest = checksum(config.model_dump())
            existing = await db.scalar(
                select(AgentVersion).where(AgentVersion.agent_id == row.id, AgentVersion.version == version)
            )
            if existing:
                if existing.checksum != digest:
                    raise ValueError("This live version is immutable; choose a new --version")
                return existing.id
            selected = AgentVersion(
                agent_id=row.id, version=version, config=config.model_dump(), checksum=digest
            )
            db.add(selected)
            await db.flush()
            return selected.id

    typer.echo(
        json.dumps(
            {
                "agent_version_id": asyncio.run(operation()),
                "version": version,
                "provider_config": spec.model_dump(),
            },
            indent=2,
        )
    )


@app.command()
def seed():
    """Seed immutable demo datasets and agent versions after migrations."""
    from agentbench.seed import seed as do_seed

    typer.echo(json.dumps(asyncio.run(do_seed()), indent=2))


@app.command()
def datasets():
    """List persisted dataset versions."""

    async def operation():
        async with transaction() as db:
            rows = (
                await db.execute(
                    select(
                        Dataset.name, DatasetVersion.id, DatasetVersion.version, DatasetVersion.frozen
                    ).join(DatasetVersion)
                )
            ).all()
            return [dict(row._mapping) for row in rows]

    typer.echo(json.dumps(asyncio.run(operation()), indent=2))


async def resolve_run(
    agent: str, dataset: str, version: str, mode: str, baseline_id: str | None, evaluators: list[str]
):
    async with transaction() as db:
        project = await db.scalar(select(Project).where(Project.name == "Agent Reliability Lab"))
        if not project:
            raise ValueError("Seed demo data first, or use the authenticated API for another project")
        agent_row = await db.scalar(select(Agent).where(Agent.project_id == project.id, Agent.name == agent))
        if not agent_row:
            raise ValueError("Unknown agent: " + agent)
        av = await db.scalar(
            select(AgentVersion).where(AgentVersion.agent_id == agent_row.id, AgentVersion.version == version)
        )
        dv = await db.scalar(
            select(DatasetVersion)
            .join(Dataset)
            .where(Dataset.project_id == project.id, Dataset.name == dataset)
            .order_by(DatasetVersion.version.desc())
        )
        if not av or not dv:
            raise ValueError("Agent or dataset version not found")
        request = RunRequest.model_validate(
            {
                "agent_version_id": av.id,
                "dataset_version_id": dv.id,
                "mode": mode,
                "baseline_id": baseline_id,
                "evaluators": evaluators,
            }
        )
        run = await create_run(db, project.id, request, execution_backend="inline")
        return run.id


async def get_report(run_id: str):
    async with transaction() as db:
        run = await db.get(EvaluationRun, run_id)
        if not run:
            raise ValueError("Run not found")
        return report_dict(run.id, run.snapshot, run.summary, await results_for(db, run.id))


@evaluation.command("run")
def run(
    agent: str = "Financial Research",
    dataset: str = "financial-research",
    version: str = "v1",
    mode: str = "offline",
    baseline: str | None = None,
    output: Path = Path("artifacts/latest.json"),
    evaluator: list[str] = typer.Option(["deterministic"]),
):
    """Run locally against real MCP sessions and persist all results. Exit with gate code."""

    async def operation():
        run_id = await resolve_run(agent, dataset, version, mode, baseline, evaluator)
        summary = await evaluate_run(run_id)
        report = await get_report(run_id)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(export_report(report, "json"), encoding="utf-8")
        output.with_suffix(".md").write_text(export_report(report, "md"), encoding="utf-8")
        return run_id, summary

    run_id, summary = asyncio.run(operation())
    typer.echo(json.dumps({"run_id": run_id, "summary": summary}, indent=2))
    raise typer.Exit(summary["gate"]["exit_code"])


@evaluation.command("inspect")
def inspect_run(run_id: str):
    """Inspect a persisted run and measured summary."""
    report = asyncio.run(get_report(run_id))
    typer.echo(json.dumps({"run_id": run_id, "summary": report["summary"]}, indent=2))


@evaluation.command("export")
def export(run_id: str, output: Path, format: str = "json"):
    report = asyncio.run(get_report(run_id))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(export_report(report, format), encoding="utf-8")
    typer.echo(str(output))


@evaluation.command("compare")
def compare_files(
    baseline: Path,
    candidate: Path,
    output: Path = Path("artifacts/comparison.json"),
    fail_on_regression: bool = False,
):
    """Compare exported reports from identical immutable datasets."""
    from agentbench.schemas import CaseResult

    a, b = json.loads(baseline.read_text()), json.loads(candidate.read_text())
    if a["snapshot"]["dataset_checksum"] != b["snapshot"]["dataset_checksum"]:
        raise typer.BadParameter("Dataset checksums do not match")
    result = compare(
        [CaseResult.model_validate(r) for r in a["results"]],
        [CaseResult.model_validate(r) for r in b["results"]],
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    typer.echo(json.dumps(result, indent=2))
    if fail_on_regression:
        raise typer.Exit(
            1 if result.get("statistical_regression") else 2 if result["status"] != "CONCLUSIVE" else 0
        )


@evaluation.command("gate")
def gate(report: Path, policy: Path | None = None):
    """Reapply an explicit policy to an exported report; unknown data never passes."""
    from agentbench.evaluation.quality_gates import apply_gate

    payload = json.loads(report.read_text())
    selected = GatePolicy.model_validate_json(policy.read_text()) if policy else GatePolicy()
    result = apply_gate(
        payload["summary"],
        selected,
        len(payload["snapshot"]["dataset"]["cases"]) * payload["snapshot"]["request"]["repetitions"],
        {c["category"] for c in payload["snapshot"]["dataset"]["cases"]},
        payload["summary"].get("comparison"),
    )
    typer.echo(json.dumps(result, indent=2))
    raise typer.Exit(result["exit_code"])


if __name__ == "__main__":
    app()
