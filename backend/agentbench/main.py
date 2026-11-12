import os
from contextlib import asynccontextmanager
from typing import Awaitable, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from agentbench.api import authentication, datasets, evaluations, registry
from agentbench.config import settings
from agentbench.database import Session
from agentbench.observability import collect_persisted_metrics, configure, tracer


@asynccontextmanager
async def lifespan(app):
    configure()
    yield


app = FastAPI(
    title="AgentBench",
    version="0.1.0",
    description="Trajectory-aware agent evaluation. Offline synthetic mode is distinct from live model reasoning.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings().frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Last-Event-ID"],
)
for router in [authentication.router, registry.router, datasets.router, evaluations.router]:
    app.include_router(router, prefix="/api")


@app.middleware("http")
async def request_guard(request: Request, call_next):
    if int(request.headers.get("content-length", "0")) > 10_000_000:
        return JSONResponse({"detail": "Request exceeds 10 MB"}, status_code=413)
    with tracer.start_as_current_span("http.request", attributes={"http.request.method": request.method}):
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse({"detail": str(exc)[:2000]}, status_code=422)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic error input can contain passwords or large imported trace payloads.
    return JSONResponse(
        {"detail": [{"loc": list(e["loc"]), "type": e["type"], "msg": e["msg"]} for e in exc.errors()]},
        status_code=422,
    )


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {"detail": "Record conflict or immutable version; create a new version"}, status_code=409
    )


@app.get("/health/live")
async def live() -> dict:
    return {"status": "live"}


@app.get("/health/ready")
async def ready() -> dict:
    async with Session() as db:
        await db.execute(text("SELECT 1"))
    redis = Redis.from_url(settings().redis_url)
    try:
        await cast(Awaitable[bool], redis.ping())
    finally:
        await redis.aclose()
    return {
        "status": "ready",
        "live_model_available": bool(
            settings().live_enabled and settings().provider_model and os.getenv("OPENAI_API_KEY")
        ),
    }


@app.get("/metrics", include_in_schema=False)
async def metrics():
    await collect_persisted_metrics()
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})
