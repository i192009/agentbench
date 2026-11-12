"""Short-lived async transactions; Alembic owns all table creation."""

from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from agentbench.config import settings
from agentbench.schemas import now, uid


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Organization(Entity):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(120))


class User(Entity):
    __tablename__ = "users"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="admin")


class RefreshSession(Entity):
    __tablename__ = "refresh_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Project(Entity):
    __tablename__ = "projects"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")


class ProjectMembership(Entity):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20), default="editor")


class Agent(Entity):
    __tablename__ = "agents"
    __table_args__ = (UniqueConstraint("project_id", "name"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")


class AgentVersion(Entity):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version"),)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    version: Mapped[str] = mapped_column(String(80))
    config: Mapped[dict] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64))


class Dataset(Entity):
    __tablename__ = "datasets"
    __table_args__ = (UniqueConstraint("project_id", "name"),)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(80), default="general")
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class DatasetVersion(Entity):
    __tablename__ = "dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_id", "version"),)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    frozen: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum: Mapped[str] = mapped_column(String(64))
    manifest: Mapped[dict] = mapped_column(JSON)


class TestCaseRow(Entity):
    __tablename__ = "test_cases"
    __table_args__ = (UniqueConstraint("version_id", "case_id"),)
    version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    case_id: Mapped[str] = mapped_column(String(100))
    body: Mapped[dict] = mapped_column(JSON)


class EvaluationRun(Entity):
    __tablename__ = "evaluation_runs"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    agent_version_id: Mapped[str] = mapped_column(ForeignKey("agent_versions.id"))
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    status: Mapped[str] = mapped_column(String(40), default="CREATED", index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    total: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseResultRow(Entity):
    __tablename__ = "evaluation_case_results"
    __table_args__ = (UniqueConstraint("run_id", "case_id"),)
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    case_id: Mapped[str] = mapped_column(String(120))
    attempt_id: Mapped[str] = mapped_column(String(36))
    passed: Mapped[bool] = mapped_column(Boolean)
    body: Mapped[dict] = mapped_column(JSON)


class RunEvent(Entity):
    __tablename__ = "run_events"
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Baseline(Entity):
    __tablename__ = "baseline_assignments"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class GatePolicyRow(Entity):
    __tablename__ = "quality_gate_policies"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    policy: Mapped[dict] = mapped_column(JSON)


class AuditEvent(Entity):
    __tablename__ = "audit_events"
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120))
    target_id: Mapped[str] = mapped_column(String(36))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


def make_engine(url: str | None = None):
    target = url or settings().database_url
    kwargs = {} if target.startswith("sqlite") else {"pool_size": 8, "max_overflow": 4, "pool_pre_ping": True}
    return create_async_engine(target, **kwargs)


engine = make_engine()
Session = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def transaction():
    async with Session() as db, db.begin():
        yield db


async def get_db():
    async with Session() as db:
        yield db
