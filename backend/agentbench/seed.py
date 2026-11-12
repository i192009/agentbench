from sqlalchemy import select

from agentbench.auth import passwords
from agentbench.config import ROOT, settings
from agentbench.database import (
    Agent,
    AgentVersion,
    Dataset,
    GatePolicyRow,
    Organization,
    Project,
    ProjectMembership,
    User,
    transaction,
)
from agentbench.schemas import AgentConfig, DatasetFile, GatePolicy, checksum, uid
from agentbench.services.datasets import create_version


async def seed() -> dict:
    password = settings().demo_password
    if len(password) < 12:
        raise ValueError("Set AB_DEMO_PASSWORD to at least 12 characters before seeding")
    async with transaction() as db:
        user = await db.scalar(select(User).where(User.email == "demo@agentbench.local"))
        if user is None:
            org = Organization(id=uid(), name="AgentBench Lab")
            db.add(org)
            await db.flush()
            user = User(
                id=uid(),
                organization_id=org.id,
                email="demo@agentbench.local",
                password_hash=passwords.hash(password),
                role="admin",
            )
            db.add(user)
            await db.flush()
        project = await db.scalar(
            select(Project).where(
                Project.organization_id == user.organization_id, Project.name == "Agent Reliability Lab"
            )
        )
        if project is None:
            project = Project(
                id=uid(),
                organization_id=user.organization_id,
                name="Agent Reliability Lab",
                description="Synthetic agent evaluation, approval safety, RAG and regression experiments",
            )
            db.add(project)
            await db.flush()
            db.add(ProjectMembership(project_id=project.id, user_id=user.id, role="admin"))
            db.add(
                GatePolicyRow(
                    project_id=project.id, name="Strict regression", policy=GatePolicy().model_dump()
                )
            )
        definitions = [
            (
                "Financial Research",
                "research",
                "langgraph",
                ["baseline", "wrong_calculation", "wrong_tool", "missing_citation"],
            ),
            ("Financial Operations", "operations", "langgraph", ["baseline", "approval_bypass"]),
            ("Workflow Supervisor", "supervisor", "langgraph", ["baseline"]),
            ("Injection Defense", "research", "langgraph", ["baseline", "injection_vulnerable"]),
        ]
        for name, workflow, adapter, variants in definitions:
            row = await db.scalar(select(Agent).where(Agent.project_id == project.id, Agent.name == name))
            if row:
                continue
            row = Agent(
                id=uid(),
                project_id=project.id,
                name=name,
                description="Deterministic synthetic workflow; live model planning is an explicitly separate mode",
            )
            db.add(row)
            await db.flush()
            for i, variant in enumerate(variants, 1):
                config = AgentConfig.model_validate(
                    {
                        "name": name,
                        "version": f"v{i}" + ("-faulty" if variant != "baseline" else ""),
                        "workflow": workflow,
                        "adapter": adapter,
                        "variant": variant,
                    }
                )
                db.add(
                    AgentVersion(
                        agent_id=row.id,
                        version=config.version,
                        config=config.model_dump(),
                        checksum=checksum(config.model_dump()),
                    )
                )
        files = sorted((ROOT / "datasets").glob("*/v1.json")) + [
            ROOT / "datasets" / "ci.json",
            ROOT / "datasets" / "development.json",
        ]
        for file in files:
            payload = DatasetFile.model_validate_json(file.read_text(encoding="utf-8"))
            existing = await db.scalar(
                select(Dataset).where(Dataset.project_id == project.id, Dataset.name == payload.name)
            )
            if existing:
                continue
            row = Dataset(
                id=uid(),
                project_id=project.id,
                name=payload.name,
                description=payload.description,
                domain=payload.domain,
                owner_id=user.id,
            )
            db.add(row)
            await db.flush()
            await create_version(db, row, payload, frozen=payload.split in {"regression", "ci"})
        for adapter in ["finsight", "ledgerguard"]:
            directory = ROOT / "examples" / "repository-contracts"
            config_file = directory / f"{adapter}-agent.json"
            if not config_file.exists():
                continue
            config = AgentConfig.model_validate_json(config_file.read_text())
            existing = await db.scalar(
                select(Agent).where(Agent.project_id == project.id, Agent.name == config.name)
            )
            if existing:
                continue
            agent = Agent(
                id=uid(),
                project_id=project.id,
                name=config.name,
                description="Synthetic native contract/recorded trace adapter; original application not executed",
            )
            db.add(agent)
            await db.flush()
            variant = "wrong_calculation" if adapter == "finsight" else "approval_bypass"
            for selected in [config, config.model_copy(update={"version": "v2-faulty", "variant": variant})]:
                db.add(
                    AgentVersion(
                        agent_id=agent.id,
                        version=selected.version,
                        config=selected.model_dump(),
                        checksum=checksum(selected.model_dump()),
                    )
                )
            payload = DatasetFile.model_validate_json((directory / f"{adapter}-dataset.json").read_text())
            dataset = Dataset(
                id=uid(),
                project_id=project.id,
                name=payload.name,
                description=payload.description,
                domain=payload.domain,
                owner_id=user.id,
            )
            db.add(dataset)
            await db.flush()
            await create_version(db, dataset, payload, frozen=True)
        return {"project_id": project.id, "user": user.email, "password": "AB_DEMO_PASSWORD (not printed)"}
