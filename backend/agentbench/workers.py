"""At-least-once delivery, bounded leases, idempotent results and durable queue recovery."""

import asyncio
import secrets
from typing import Awaitable, cast

from celery import Celery
from celery.signals import worker_process_init
from redis.asyncio import Redis
from sqlalchemy import func, or_, select

from agentbench.config import settings
from agentbench.database import EvaluationRun, transaction
from agentbench.evaluation.orchestration import evaluate_run
from agentbench.observability import configure


@worker_process_init.connect
def initialize_worker_telemetry(**kwargs):
    configure()


celery = Celery("agentbench", broker=settings().redis_url, backend=settings().redis_url)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=settings().run_timeout_seconds + 60,
    broker_transport_options={"visibility_timeout": settings().run_timeout_seconds + 120},
    result_expires=86400,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={"recover-durable-evaluations": {"task": "agentbench.dispatch", "schedule": 15.0}},
)
_loop = None


def run_async(coro):
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


class Busy(Exception):
    pass


async def leased_run(run_id: str):
    redis = Redis.from_url(settings().redis_url)
    token = secrets.token_hex(24)
    ttl = settings().run_timeout_seconds + 90
    run_key, slot_key = "ab:run:" + run_id, None
    acquired = False
    release = (
        "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
    )
    try:
        async with transaction() as db:
            run = await db.get(EvaluationRun, run_id)
            if not run or run.status in {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELLED"}:
                return
            project_id = run.project_id
        acquired = bool(await redis.set(run_key, token, nx=True, ex=ttl))
        if not acquired:
            return  # The durable dispatcher reclaims abandoned work after lease expiry.
        for slot in range(settings().project_concurrency):
            key = f"ab:project:{project_id}:slot:{slot}"
            if await redis.set(key, token, nx=True, ex=ttl):
                slot_key = key
                break
        if slot_key is None:
            raise Busy("Project concurrency limit")
        await evaluate_run(run_id)
    finally:
        if acquired:
            await cast(Awaitable[object], redis.eval(release, 1, run_key, token))
        if slot_key:
            await cast(Awaitable[object], redis.eval(release, 1, slot_key, token))
        await redis.aclose()


@celery.task(bind=True, name="agentbench.evaluate", max_retries=None)
def evaluate(self, run_id: str):
    try:
        run_async(leased_run(run_id))
    except Busy as exc:
        # QUEUED state is the outbox. A later dispatch retries project backpressure;
        # do not multiply broker retries for each periodic scan of the same run.
        return {"status": "deferred", "reason": str(exc)}


async def queued_runs():
    async with transaction() as db:
        candidates = list(
            (
                await db.scalars(
                    select(EvaluationRun.id)
                    .where(or_(EvaluationRun.status == "QUEUED", EvaluationRun.status == "RUNNING"))
                    .where(
                        func.coalesce(EvaluationRun.snapshot["execution_backend"].as_string(), "celery")
                        == "celery"
                    )
                    .limit(100)
                )
            ).all()
        )
    redis = Redis.from_url(settings().redis_url)
    try:
        ready = []
        for run_id in candidates:
            if await redis.exists("ab:run:" + run_id):
                continue
            if await redis.set("ab:dispatch:" + run_id, "queued", nx=True, ex=30):
                ready.append(run_id)
        return ready
    finally:
        await redis.aclose()


@celery.task(name="agentbench.dispatch")
def dispatch():
    for run_id in run_async(queued_runs()):
        evaluate.delay(run_id)
