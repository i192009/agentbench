import os
from time import perf_counter
from urllib.parse import urlparse

import httpx

from agentbench.agents.langgraph_adapter import execute_graph
from agentbench.config import settings
from agentbench.mcp.client import Sandbox
from agentbench.schemas import AgentConfig, Execution, ExecutionMode, TestCase
from agentbench.tracing import Recorder, redact


def validate_external_url(url: str):
    parsed = urlparse(url)
    origins = settings().external_agent_origins.split(",")
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Invalid external agent URL")
    if f"{parsed.scheme}://{parsed.netloc}" not in origins:
        raise ValueError("External origin is not administrator-authorized")


async def execute(config: AgentConfig, case: TestCase, sandbox: Sandbox, mode: ExecutionMode, run_id: str):
    if config.adapter == "recorded":
        if mode != "recorded":
            raise ValueError("Recorded adapter requires recorded mode")
        payload = config.runtime.get("traces", {}).get(case.id)
        if payload is None:
            raise ValueError("Missing recorded trace for " + case.id)
        result = Execution.model_validate(redact(payload))
        if result.case_id != case.id:
            raise ValueError("Recorded trace case mismatch")
        result.mode = "recorded"
        return result
    if config.adapter in {"finsight", "ledgerguard"}:
        from agentbench.integrations.repositories import execute_repository

        return await execute_repository(config, case, sandbox, mode, run_id)
    if config.adapter == "http":
        if mode != "external":
            raise ValueError("HTTP adapter requires external mode")
        url = config.runtime.get("url", "")
        validate_external_url(url)
        token_env = config.runtime.get("token_env", "AB_EXTERNAL_TOKEN")
        if token_env != "AB_EXTERNAL_TOKEN":
            raise ValueError("HTTP adapters may only use the administrator-configured AB_EXTERNAL_TOKEN")
        key = os.getenv(token_env)
        if not key:
            raise ValueError("External agent token environment is not configured")
        start = perf_counter()
        async with httpx.AsyncClient(
            timeout=case.budget.timeout_seconds, follow_redirects=False, trust_env=False
        ) as client:
            response = await client.post(
                url,
                headers={"Authorization": "Bearer " + key},
                json={
                    "case_id": case.id,
                    "input": case.input,
                    "conversation": case.conversation,
                    "budget": case.budget.model_dump(),
                    "fixture": case.fixture,
                },
            )
            response.raise_for_status()
            if len(response.content) > 1000000:
                raise ValueError("External response exceeds 1 MB")
            result = Execution.model_validate(redact(response.json()))
        if result.case_id != case.id:
            raise ValueError("External case ID mismatch")
        result.mode, result.latency_ms = "external", (perf_counter() - start) * 1000
        return result
    if mode not in {"offline", "live"}:
        raise ValueError("LangGraph adapter requires offline or live mode")
    return await execute_graph(config, case, sandbox, mode, run_id)


def error_execution(case: TestCase, mode: ExecutionMode, exc: Exception, run_id: str):
    recorder = Recorder(case.id, run_id)
    recorder.add("ErrorOccurred", error=str(exc)[:1000])
    return Execution(
        case_id=case.id,
        mode=mode,
        status="error",
        final_state="error",
        trace=recorder.events,
        errors=[str(exc)[:1000]],
    )
