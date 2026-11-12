from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.auth import current_user, project_access
from agentbench.database import AuditEvent, User, get_db


def public(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def audit(db, user, action, target_id, **data):
    db.add(
        AuditEvent(
            organization_id=user.organization_id,
            actor_id=user.id,
            action=action,
            target_id=target_id,
            data=data,
        )
    )


async def access(project_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await project_access(db, user, project_id)
    return user


async def editor(project_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    await project_access(db, user, project_id, write=True)
    return user


async def owned(db, model, identifier, project_id):
    row = await db.get(model, identifier)
    if row is None or getattr(row, "project_id", project_id) != project_id:
        raise HTTPException(404, "Resource not found")
    return row


async def page(db, query, offset=0, limit=50):
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.scalars(query.offset(offset).limit(limit))).all()
    return {"items": [public(r) for r in rows], "total": total, "offset": offset, "limit": limit}
