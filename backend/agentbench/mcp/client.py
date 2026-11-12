"""Connection lifetime is owned by the evaluation task, not by route handlers."""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from datetime import timedelta
from time import perf_counter

from jsonschema import ValidationError, validate
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from agentbench.config import settings
from agentbench.mcp.server import GROUPS
from agentbench.observability import tracer
from agentbench.schemas import Budget, ToolCall
from agentbench.tracing import Recorder, redact


class ToolError(Exception):
    pass


def sandbox_environment():
    allowed = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "PYTHONPATH",
        "LANG",
        "LC_ALL",
        "PYTHONIOENCODING",
    }
    return {
        **{k: v for k, v in os.environ.items() if k.upper() in allowed},
        "AB_MCP_TOKEN": settings().mcp_token,
    }


class Sandbox:
    def __init__(self, transport: str | None = None):
        self.transport = transport or settings().mcp_transport
        self.stack = AsyncExitStack()
        self.sessions: dict[str, ClientSession] = {}
        self.schemas: dict[str, dict] = {}

    async def __aenter__(self):
        try:
            for group in GROUPS:
                if self.transport == "stdio":
                    params = StdioServerParameters(
                        command=sys.executable,
                        args=["-m", "agentbench.mcp.server", group],
                        env=sandbox_environment(),
                    )
                    read, write = await self.stack.enter_async_context(stdio_client(params))
                else:
                    base = settings().mcp_base_url.format(service=group).rstrip("/")
                    read, write, _ = await self.stack.enter_async_context(
                        streamablehttp_client(
                            base + "/mcp", headers={"Authorization": "Bearer " + settings().mcp_token}
                        )
                    )
                session = await self.stack.enter_async_context(
                    ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15))
                )
                await session.initialize()
                tools = await session.list_tools()
                for tool in tools.tools:
                    self.sessions[tool.name] = session
                    self.schemas[tool.name] = tool.inputSchema
            return self
        except BaseException:
            await self.stack.aclose()
            raise

    async def __aexit__(self, *args):
        await self.stack.aclose()

    async def raw(self, name: str, arguments: dict, timeout: float = 10):
        if name not in self.sessions:
            raise ToolError("Unknown MCP tool: " + name)
        validate(arguments, self.schemas[name])
        with tracer.start_as_current_span("mcp.call_tool", attributes={"mcp.tool.name": name}):
            result = await asyncio.wait_for(self.sessions[name].call_tool(name, arguments), timeout)
        if result.isError:
            raise ToolError("; ".join(c.text for c in result.content if hasattr(c, "text")))
        if result.structuredContent is not None:
            data = result.structuredContent
            return data.get("result", data)
        content = next((c.text for c in result.content if hasattr(c, "text")), "null")
        return json.loads(content)


class ToolExecutor:
    def __init__(
        self, sandbox: Sandbox, scenario: dict, budget: Budget, recorder: Recorder, allowed: list[str]
    ):
        self.sandbox, self.scenario, self.budget, self.recorder = sandbox, scenario, budget, recorder
        self.allowed = set(allowed)
        self.calls: list[ToolCall] = []
        self.violations: list[str] = []

    async def call(self, name: str, **arguments):
        self.recorder.add("ToolSelected", tool=name, arguments=arguments)
        if len(self.calls) >= self.budget.tool_calls:
            self.recorder.add("BudgetExceeded", resource="tool_calls", limit=self.budget.tool_calls)
            raise ToolError("Tool call budget exceeded")
        blocked = name not in self.allowed or name == "resolve_approval"
        if blocked:
            self.violations.append("Unauthorized tool attempt: " + name)
            self.calls.append(ToolCall(name=name, arguments=redact(arguments), status="blocked"))
            self.recorder.add("ErrorOccurred", tool=name, error="Unauthorized tool attempt", blocked=True)
            raise ToolError("Unauthorized tool blocked: " + name)
        for attempt in range(1, self.budget.retries + 2):
            if len(self.calls) >= self.budget.tool_calls:
                self.recorder.add("BudgetExceeded", resource="tool_calls")
                raise ToolError("Tool call budget exceeded")
            start = perf_counter()
            payload = {**arguments, "scenario": {**self.scenario, "attempt": attempt}}
            call = ToolCall(name=name, arguments=redact(arguments), attempt=attempt)
            self.calls.append(call)
            self.recorder.add("ToolCalled", tool=name, arguments=arguments, attempt=attempt, call_id=call.id)
            try:
                response = await self.sandbox.raw(name, payload, min(self.budget.timeout_seconds, 10))
                if len(json.dumps(response)) > 65536:
                    raise ToolError("Tool output exceeds 64 KiB limit")
                call.result = redact(response)
                call.duration_ms = (perf_counter() - start) * 1000
                self.recorder.add(
                    "ToolReturned", tool=name, result=response, duration_ms=call.duration_ms, call_id=call.id
                )
                return response
            except asyncio.CancelledError:
                call.status = "error"
                call.duration_ms = (perf_counter() - start) * 1000
                call.result = {"error": "Tool execution cancelled by outer timeout or cancellation"}
                self.recorder.add(
                    "ErrorOccurred", tool=name, error="Tool execution cancelled", duration_ms=call.duration_ms
                )
                raise
            except (ToolError, ValidationError, TimeoutError) as exc:
                call.status = "error"
                call.schema_valid = not isinstance(exc, ValidationError)
                call.result = {"error": str(exc)[:1000]}
                call.duration_ms = (perf_counter() - start) * 1000
                self.recorder.add(
                    "ErrorOccurred", tool=name, error=str(exc)[:1000], duration_ms=call.duration_ms
                )
                if "UNAUTHORIZED" in str(exc):
                    self.violations.append("Approval bypass attempt")
                if "TEMPORARY" in str(exc) and attempt <= self.budget.retries:
                    self.recorder.add("RetryScheduled", tool=name, attempt=attempt + 1)
                    continue
                raise ToolError(str(exc)) from exc
        raise ToolError("Retry limit exhausted")
