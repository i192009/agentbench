import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.config import settings
from agentbench.database import Project, ProjectMembership, RefreshSession, User, get_db
from agentbench.schemas import now, uid

passwords = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = passwords.hash("timing-placeholder-not-a-user-password")
bearer = HTTPBearer(auto_error=False)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def access_token(user: User) -> str:
    return jwt.encode(
        {
            "sub": user.id,
            "iat": now(),
            "exp": now() + timedelta(minutes=settings().access_minutes),
            "iss": "agentbench",
            "aud": "agentbench-api",
            "jti": uid(),
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


async def issue_session(db: AsyncSession, user: User, family_id: str | None = None):
    token = secrets.token_urlsafe(48)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_hash(token),
            family_id=family_id or uid(),
            expires_at=now() + timedelta(days=settings().refresh_days),
        )
    )
    return token


async def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: AsyncSession = Depends(get_db)
) -> User:
    if credentials is None:
        raise HTTPException(401, "Authentication required")
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings().jwt_secret,
            algorithms=["HS256"],
            issuer="agentbench",
            audience="agentbench-api",
        )
        user = await db.get(User, claims["sub"])
        if user is None:
            raise ValueError("Unknown user")
        return user
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid or expired access token") from None


async def project_access(db: AsyncSession, user: User, project_id: str, write: bool = False) -> Project:
    project = await db.get(Project, project_id)
    if project is None or project.organization_id != user.organization_id:
        raise HTTPException(404, "Project not found")
    membership = await db.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id, ProjectMembership.user_id == user.id
        )
    )
    if user.role != "admin" and membership is None:
        raise HTTPException(404, "Project not found")
    if write and user.role != "admin" and (membership is None or membership.role not in {"editor", "admin"}):
        raise HTTPException(403, "Project editor role required")
    return project


async def rate_limit(request: Request, bucket: str, limit: int = 30, seconds: int = 60):
    host = request.client.host if request.client else "unknown"
    key = f"ab:rate:{bucket}:{host}:{int(datetime.now(UTC).timestamp()) // seconds}"
    redis = Redis.from_url(settings().redis_url)
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, seconds + 1)
        if count > limit:
            raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": str(seconds)})
    finally:
        await redis.aclose()
