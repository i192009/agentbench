from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.auth import (
    DUMMY_PASSWORD_HASH,
    access_token,
    current_user,
    issue_session,
    passwords,
    rate_limit,
    token_hash,
)
from agentbench.config import settings
from agentbench.database import Organization, RefreshSession, User, get_db
from agentbench.schemas import Contract, uid

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Credentials(Contract):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)


def set_refresh(response, token):
    response.set_cookie(
        "ab_refresh",
        token,
        httponly=True,
        secure=settings().secure_cookies,
        samesite="strict",
        path="/api/auth",
        max_age=settings().refresh_days * 86400,
    )


@router.post("/register", status_code=201)
async def register(
    body: Credentials, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> dict:
    await rate_limit(request, "register", 5, 300)
    org = Organization(id=uid(), name=body.email.split("@")[0] + " organization")
    db.add(org)
    await db.flush()
    user = User(
        id=uid(),
        organization_id=org.id,
        email=body.email.lower(),
        password_hash=passwords.hash(body.password),
        role="admin",
    )
    db.add(user)
    await db.flush()
    refresh = await issue_session(db, user)
    await db.commit()
    set_refresh(response, refresh)
    return {"access_token": access_token(user), "token_type": "bearer"}


@router.post("/login")
async def login(
    body: Credentials, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> dict:
    await rate_limit(request, "login", 15, 300)
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    # Constant work for unknown accounts prevents a cheap email enumeration oracle.
    try:
        valid = passwords.verify(body.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    except Exception:
        valid = False
    if not user or not valid:
        raise HTTPException(401, "Invalid email or password")
    token = await issue_session(db, user)
    await db.commit()
    set_refresh(response, token)
    return {"access_token": access_token(user), "token_type": "bearer"}


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    await rate_limit(request, "refresh", 60, 300)
    raw = request.cookies.get("ab_refresh", "")
    session = await db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash(raw)).with_for_update()
    )
    if session is None:
        raise HTTPException(401, "Refresh session is invalid")
    expired = session.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
    if session.revoked or expired:
        await db.execute(
            update(RefreshSession).where(RefreshSession.family_id == session.family_id).values(revoked=True)
        )
        await db.commit()
        raise HTTPException(401, "Refresh replay or expired session; sign in again")
    changed = await db.scalar(
        update(RefreshSession)
        .where(RefreshSession.id == session.id, RefreshSession.revoked.is_(False))
        .values(revoked=True)
        .returning(RefreshSession.id)
    )
    if changed is None:
        await db.rollback()
        raise HTTPException(401, "Refresh session already rotated")
    user = await db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "User no longer exists")
    token = await issue_session(db, user, session.family_id)
    await db.commit()
    set_refresh(response, token)
    return {"access_token": access_token(user), "token_type": "bearer"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw = request.cookies.get("ab_refresh", "")
    await db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user.id, RefreshSession.token_hash == token_hash(raw))
        .values(revoked=True)
    )
    await db.commit()
    response.delete_cookie("ab_refresh", path="/api/auth")
    return {"status": "logged_out"}


@router.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role, "organization_id": user.organization_id}
