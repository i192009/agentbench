from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.api.common import access, audit, editor, owned, page, public
from agentbench.auth import current_user
from agentbench.database import Agent, AgentVersion, GatePolicyRow, Project, ProjectMembership, User, get_db
from agentbench.schemas import AgentConfig, Contract, GatePolicy, Page, checksum

router = APIRouter(tags=["Registry"])


class ProjectInput(Contract):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)


class MembershipInput(Contract):
    user_id: str
    role: str = Field(pattern="^(viewer|editor|admin)$")


@router.get("/projects", response_model=Page)
async def projects(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.organization_id == user.organization_id)
    if user.role != "admin":
        query = query.where(
            Project.id.in_(select(ProjectMembership.project_id).where(ProjectMembership.user_id == user.id))
        )
    return await page(db, query.order_by(Project.created_at), offset, limit)


@router.post("/projects", status_code=201)
async def create_project(
    body: ProjectInput, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Organization administrator required")
    row = Project(organization_id=user.organization_id, **body.model_dump())
    db.add(row)
    await db.flush()
    db.add(ProjectMembership(project_id=row.id, user_id=user.id, role="admin"))
    audit(db, user, "project.created", row.id)
    await db.commit()
    return public(row)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)
) -> dict:
    return public(await db.get(Project, project_id))


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str, body: ProjectInput, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    row = await db.get(Project, project_id)
    if row is None:
        raise HTTPException(404, "Project not found")
    row.name, row.description = body.name, body.description
    audit(db, user, "project.updated", row.id)
    await db.commit()
    return public(row)


@router.post("/projects/{project_id}/members", status_code=201)
async def add_member(
    project_id: str, body: MembershipInput, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    if user.role != "admin":
        raise HTTPException(403, "Organization administrator required")
    target = await db.get(User, body.user_id)
    if not target or target.organization_id != user.organization_id:
        raise HTTPException(404, "Organization user not found")
    row = ProjectMembership(project_id=project_id, **body.model_dump())
    db.add(row)
    await db.commit()
    return public(row)


@router.get("/projects/{project_id}/agents", response_model=Page)
async def agents(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    return await page(
        db, select(Agent).where(Agent.project_id == project_id).order_by(Agent.created_at), offset, limit
    )


@router.post("/projects/{project_id}/agents", status_code=201)
async def register_agent(
    project_id: str, body: AgentConfig, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    row = Agent(project_id=project_id, name=body.name)
    db.add(row)
    await db.flush()
    version = AgentVersion(
        agent_id=row.id, version=body.version, config=body.model_dump(), checksum=checksum(body.model_dump())
    )
    db.add(version)
    await db.flush()
    audit(db, user, "agent.registered", row.id)
    await db.commit()
    return {"agent": public(row), "version": public(version)}


@router.post("/projects/{project_id}/agents/{agent_id}/versions", status_code=201)
async def agent_version(
    project_id: str,
    agent_id: str,
    body: AgentConfig,
    user: User = Depends(editor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await owned(db, Agent, agent_id, project_id)
    row = AgentVersion(
        agent_id=agent_id,
        version=body.version,
        config=body.model_dump(),
        checksum=checksum(body.model_dump()),
    )
    db.add(row)
    await db.flush()
    audit(db, user, "agent.version.created", row.id)
    await db.commit()
    return public(row)


@router.get("/projects/{project_id}/agents/{agent_id}/versions", response_model=Page)
async def versions(
    project_id: str, agent_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)
):
    await owned(db, Agent, agent_id, project_id)
    return await page(
        db, select(AgentVersion).where(AgentVersion.agent_id == agent_id).order_by(AgentVersion.created_at)
    )


@router.get("/projects/{project_id}/gates", response_model=Page)
async def gates(project_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)):
    return await page(db, select(GatePolicyRow).where(GatePolicyRow.project_id == project_id))


class NamedGate(Contract):
    name: str = Field(min_length=1, max_length=120)
    policy: GatePolicy


@router.post("/projects/{project_id}/gates", status_code=201)
async def create_gate(
    project_id: str, body: NamedGate, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    row = GatePolicyRow(project_id=project_id, name=body.name, policy=body.policy.model_dump())
    db.add(row)
    await db.flush()
    audit(db, user, "gate.created", row.id)
    await db.commit()
    return public(row)


@router.put("/projects/{project_id}/gates/{gate_id}")
async def update_gate(
    project_id: str,
    gate_id: str,
    body: NamedGate,
    user: User = Depends(editor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await owned(db, GatePolicyRow, gate_id, project_id)
    row.name, row.policy = body.name, body.policy.model_dump()
    audit(db, user, "gate.updated", row.id)
    await db.commit()
    return public(row)
