import copy
import os
from decimal import Decimal
from time import perf_counter

import httpx

from agentbench.agents.adapters import validate_external_url
from agentbench.schemas import (
    AgentConfig,
    Citation,
    Document,
    Execution,
    ExecutionMode,
    TestCase,
    ToolCall,
    Usage,
)
from agentbench.tracing import Recorder, redact

SOURCES = {
    "finsight": {
        "repository": "https://github.com/i192009/finsight-ai",
        "inspected_commit": "fb75952a28be92d5f3134e17e9283c7cb6bb37ef",
        "contracts": [
            "backend/app/schemas/contracts.py",
            "backend/app/schemas/responses.py",
            "backend/app/agents/graph.py",
            "backend/app/api/v1/routes.py",
        ],
    },
    "ledgerguard": {
        "repository": "https://github.com/i192009/ledgerguard-ai",
        "inspected_commit": "bfc8892e25e645fc1a3771782474e2572a1d0201",
        "contracts": [
            "src/ledgerguard/schemas.py",
            "src/ledgerguard/models.py",
            "src/ledgerguard/orchestrator.py",
            "src/ledgerguard/api.py",
        ],
    },
}


def normalize_finsight(case_id: str, payload: dict, recorder: Recorder) -> Execution:
    body = payload["report"]["body"]
    aliases = {"revenue_growth": "growth_percent", "net_profit_margin": "profit_margin_percent"}
    output = {}
    for calculation in body.get("calculations", []):
        if calculation.get("value") is not None:
            output[aliases.get(calculation["metric"], calculation["metric"])] = float(
                Decimal(str(calculation["value"]))
            )
    documents = [
        Document(
            id=s["id"], version=str(s.get("version", "1")), content=s["content"], facts=s.get("facts", {})
        )
        for s in body.get("sources", [])
    ]
    citations = []
    for section in body.get("sections", []):
        for claim in section.get("claims", []):
            for source_id in claim["citations"]:
                quote = next(
                    (q["quote"] for q in claim.get("evidence_quotes", []) if q["source_id"] == source_id),
                    None,
                )
                key = payload.get("claim_bindings", {}).get(claim["text"])
                citations.append(
                    Citation(
                        source_id=source_id,
                        claim=claim["text"],
                        quote=quote,
                        fact_key=key,
                        fact_value=output.get(key),
                    )
                )
    # Native reports lack execution telemetry. Only explicitly supplied captured calls count.
    calls = [ToolCall.model_validate(c) for c in payload.get("tool_calls", [])]
    for call in calls:
        recorder.add("ToolCalled", tool=call.name, arguments=call.arguments)
        recorder.add("ToolReturned", tool=call.name, result=call.result, duration_ms=call.duration_ms)
    for node in payload.get("nodes", []):
        recorder.add("StateTransition", node, to_state=node)
    return Execution(
        case_id=case_id,
        output=output,
        tool_calls=calls,
        documents=documents,
        citations=citations,
        trace=recorder.events,
        final_state="completed" if body["status"] in {"COMPLETED", "complete", "completed"} else "incomplete",
        usage=Usage.model_validate(payload.get("usage", {})),
    )


def normalize_ledgerguard(case_id: str, payload: dict, recorder: Recorder) -> Execution:
    run = payload["run"]
    state = run["state"]
    calls = []
    # Native event records and tool execution records may be interleaved by capture order.
    for event in payload.get("events", []):
        kind = event["event"]
        data = event.get("data", {})
        if kind == "APPROVAL_REQUIRED":
            recorder.add("HumanApprovalRequested", "human_review", **data)
        elif kind == "APPROVAL_RECEIVED":
            statuses = data.get("statuses", [])
            recorder.add(
                "HumanApprovalReceived",
                "human_review",
                decision="approved" if statuses and all(s == "APPROVED" for s in statuses) else "rejected",
                native_event=data,
            )
        elif kind == "ACTION_EXECUTED":
            recorder.add("ToolCalled", "authorized_executor", tool="execute_correction", native_event=data)
        elif kind == "AGENT_STARTED":
            recorder.add("StateTransition", data.get("agent", "unknown"), to_state=data.get("agent"))
        else:
            recorder.add("NativeEvent", native_type=kind, **data)
    for item in payload.get("tool_executions", []):
        details = item.get("details", {})
        recorder.add(
            "ToolCalled", tool=item["tool"], arguments=details.get("arguments", {}), native_telemetry=True
        )
        recorder.add("ToolReturned", tool=item["tool"], result=details.get("result"), native_telemetry=True)
        calls.append(
            ToolCall(
                name=item["tool"],
                arguments=details.get("arguments", {}),
                result=details.get("result"),
                duration_ms=item["duration_ms"],
                status="ok" if item["status"] in {"SUCCESS", "ok", "COMPLETED"} else "error",
            )
        )
    output = {
        "executed": bool(state.get("executions")),
        "report_created": bool(state.get("report_id")),
        "approval_ids": state.get("approval_ids", []),
    }
    return Execution(
        case_id=case_id,
        output=output,
        tool_calls=calls,
        trace=recorder.events,
        final_state={
            "COMPLETED": "completed",
            "WAITING_APPROVAL": "awaiting_approval",
            "FAILED": "error",
        }.get(run["status"], run["status"].lower()),
        status="error" if run["status"] == "FAILED" else "completed",
        errors=[run["error"]] if run.get("error") else [],
    )


async def execute_repository(config: AgentConfig, case: TestCase, sandbox, mode: ExecutionMode, run_id: str):
    start = perf_counter()
    recorder = Recorder(case.id, run_id)
    recorder.add("AgentStarted", adapter=config.adapter, mode=mode)
    if mode in {"offline", "recorded"}:
        payload = config.runtime.get("records", {}).get(case.id)
        if payload is None:
            raise ValueError("Missing native contract fixture/recording for " + case.id)
        payload = copy.deepcopy(payload)
        provenance = {
            **SOURCES[config.adapter],
            "kind": "synthetic-native-contract-fixture",
            "original_application_executed": False,
        }
    elif mode == "external":
        base = config.runtime["base_url"].rstrip("/")
        validate_external_url(base)
        token_env = {"finsight": "AB_FINSIGHT_TOKEN", "ledgerguard": "AB_LEDGERGUARD_TOKEN"}[config.adapter]
        token = os.getenv(token_env)
        if not token:
            raise ValueError("Native integration token environment is missing")
        async with httpx.AsyncClient(
            timeout=case.budget.timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            headers={"Authorization": "Bearer " + token},
        ) as client:
            identifier = config.runtime["resource_ids"][case.id]
            from uuid import UUID

            identifier = str(UUID(identifier))
            if config.adapter == "finsight":
                response = await client.get(base + "/api/v1/research/reports/" + identifier)
                response.raise_for_status()
                payload = {
                    "report": response.json(),
                    "tool_calls": config.runtime.get("captured_tool_calls", {}).get(case.id, []),
                }
            else:
                response = await client.get(base + "/api/v1/agents/runs/" + identifier)
                response.raise_for_status()
                tools = await client.get(base + "/api/v1/mcp/tool-executions", params={"run_id": identifier})
                tools.raise_for_status()
                payload = {
                    "run": response.json(),
                    "tool_executions": tools.json().get("items", []),
                    "events": config.runtime.get("captured_events", {}).get(case.id, []),
                }
        provenance = {
            **SOURCES[config.adapter],
            "kind": "native-authenticated-read-only-snapshot",
            "original_application_executed": False,
        }
    else:
        raise ValueError(
            "Native adapters support offline/recorded contracts or explicitly configured external snapshots"
        )
    if config.variant == "wrong_calculation" and config.adapter == "finsight":
        payload["report"]["body"]["calculations"][0]["value"] = "999"
    if config.variant == "approval_bypass" and config.adapter == "ledgerguard":
        payload["events"] = [e for e in payload.get("events", []) if e["event"] != "APPROVAL_RECEIVED"]
    normalize = normalize_finsight if config.adapter == "finsight" else normalize_ledgerguard
    result = normalize(case.id, redact(payload), recorder)
    result.mode = mode
    result.latency_ms = (perf_counter() - start) * 1000
    result.provenance = provenance
    recorder.add("AgentFinished", status=result.status, duration_ms=result.latency_ms)
    result.trace = recorder.events
    return result
