import logging
import os
from typing import Awaitable, cast

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from prometheus_client import Counter, Gauge, Histogram

RUNS = Counter("agentbench_runs_total", "Completed evaluation runs", ["status"])
CASES = Counter("agentbench_cases_total", "Scored cases", ["outcome"])
LATENCY = Histogram(
    "agentbench_case_seconds",
    "Measured execution latency",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5, 15, 30, 60, 180],
)
SAFETY = Counter("agentbench_safety_failures_total", "Cases with attempted unsafe behavior")
TOOL_ERRORS = Counter("agentbench_tool_errors_total", "Failed tool calls")
TOKENS = Counter("agentbench_model_tokens_total", "Provider-reported tokens", ["direction"])
JUDGE_ERRORS = Counter("agentbench_judge_errors_total", "Failed judge evaluations")
PERSISTED_RUNS = Gauge("agentbench_persisted_runs", "Authoritative persisted runs", ["status"])
PERSISTED_CASES = Gauge("agentbench_persisted_cases", "Authoritative persisted case results", ["outcome"])
PERSISTED_SAFETY = Gauge(
    "agentbench_persisted_safety_failures", "Safety-failing cases in completed run summaries"
)
QUEUE = Gauge("agentbench_queue_depth", "Redis evaluation queue length")
tracer = trace.get_tracer("agentbench")


def configure():
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.processors.JSONRenderer()]
    )
    provider = TracerProvider()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces"))
        )
    trace.set_tracer_provider(provider)


async def collect_persisted_metrics():
    from redis.asyncio import Redis
    from sqlalchemy import func, select

    from agentbench.config import settings
    from agentbench.database import CaseResultRow, EvaluationRun, transaction

    async with transaction() as db:
        rows = (
            await db.execute(select(EvaluationRun.status, func.count()).group_by(EvaluationRun.status))
        ).all()
        counts = dict(rows)
        for status in [
            "CREATED",
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "COMPLETED_WITH_ERRORS",
            "FAILED",
            "CANCELLED",
        ]:
            PERSISTED_RUNS.labels(status).set(counts.get(status, 0))
        results = (
            await db.execute(select(CaseResultRow.passed, func.count()).group_by(CaseResultRow.passed))
        ).all()
        outcomes = dict(results)
        PERSISTED_CASES.labels("pass").set(outcomes.get(True, 0))
        PERSISTED_CASES.labels("fail").set(outcomes.get(False, 0))
        failures = await db.scalar(select(func.sum(EvaluationRun.summary["safety_violations"].as_integer())))
        PERSISTED_SAFETY.set(failures or 0)
    redis = Redis.from_url(settings().redis_url)
    try:
        QUEUE.set(await cast(Awaitable[int], redis.llen("celery")))
    except Exception:
        QUEUE.set(float("nan"))
    finally:
        await redis.aclose()
