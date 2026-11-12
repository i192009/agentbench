from pathlib import Path

import pytest
from agentbench.agents.langgraph_adapter import execute_graph
from agentbench.evaluation.extensions import deepeval_metrics, ragas_metrics
from agentbench.evaluation.scoring import score
from agentbench.schemas import AgentConfig, DatasetFile
from jsonschema import ValidationError


def load(name):
    return DatasetFile.model_validate_json(Path(f"datasets/{name}/v1.json").read_text()).cases


@pytest.mark.integration
async def test_actual_mcp_initialize_discover_validate_call(sandbox):
    assert len(sandbox.schemas) == 21
    assert "inputSchema" not in sandbox.schemas["get_company_profile"]
    assert "company" in sandbox.schemas["get_company_profile"]["properties"]
    response = await sandbox.raw("get_company_profile", {"company": "ACME", "scenario": {}})
    assert response["candidates"] == ["ACME"]
    with pytest.raises(ValidationError):
        await sandbox.raw("get_company_profile", {"company": 123, "scenario": {}})


@pytest.mark.integration
@pytest.mark.parametrize(
    "name", ["financial-research", "financial-operations", "rag", "adversarial", "multi-step"]
)
async def test_all_curated_workflows(name, sandbox):
    for case in load(name):
        execution = await execute_graph(
            AgentConfig(name="Baseline", version="1", workflow="supervisor"), case, sandbox
        )
        result = score(case, execution)
        assert result.passed, (
            case.id,
            [m.model_dump() for m in result.metrics if m.status != "PASS"],
            execution.errors,
        )


@pytest.mark.integration
async def test_approval_interrupt_checkpoint_resume_and_idempotency(sandbox):
    case = load("financial-operations")[16]
    execution = await execute_graph(
        AgentConfig(name="Operations", version="1", workflow="operations"), case, sandbox
    )
    events = [e.event for e in execution.trace]
    assert events.index("HumanApprovalRequested") < events.index("HumanApprovalReceived")
    assert execution.output["executed"]
    assert execution.output["duplicate_suppressed"]
    assert sum(c.name == "create_approval_request" for c in execution.tool_calls) == 1


@pytest.mark.integration
async def test_transient_tool_retry_captured(sandbox):
    case = load("multi-step")[18]
    execution = await execute_graph(AgentConfig(name="Research", version="1"), case, sandbox)
    assert score(case, execution).passed
    assert any(e.event == "RetryScheduled" for e in execution.trace)
    assert [c.attempt for c in execution.tool_calls if c.name == "get_financial_statements"] == [1, 2]


@pytest.mark.adversarial
async def test_broken_approval_guard_attempt_is_blocked_and_failed(sandbox):
    case = load("financial-operations")[12]
    execution = await execute_graph(
        AgentConfig(name="Faulty", version="2", workflow="operations", variant="approval_bypass"),
        case,
        sandbox,
    )
    assert execution.safety_violations
    assert not score(case, execution).passed
    assert not execution.output.get("executed")


@pytest.mark.adversarial
async def test_tool_output_injection_attempt_is_observed(sandbox):
    case = load("adversarial")[0]
    execution = await execute_graph(
        AgentConfig(name="Vulnerable", version="2", variant="injection_vulnerable"), case, sandbox
    )
    assert any(c.name == "export_secrets" and c.status == "blocked" for c in execution.tool_calls)
    assert next(m for m in score(case, execution).metrics if m.name == "safety").status == "FAIL"


@pytest.mark.integration
async def test_ragas_and_deepeval_official_scorers(sandbox):
    case = load("financial-research")[0]
    execution = await execute_graph(AgentConfig(name="Baseline", version="1"), case, sandbox)
    assert all(m.score == 1 for m in await ragas_metrics(case, execution))
    assert (await deepeval_metrics(case, execution))[0].status == "PASS"


@pytest.mark.integration
async def test_outer_timeout_records_unfinished_tool_as_error_and_session_recovers(sandbox):
    case = load("financial-research")[0].model_copy(deep=True)
    case.budget.timeout_seconds = 0.1
    case.fixture["fault"] = {"tool": "get_financial_statements", "kind": "slow", "seconds": 2}
    execution = await execute_graph(AgentConfig(name="Timeout", version="1"), case, sandbox)
    assert execution.status == "error"
    assert any(c.name == "get_financial_statements" and c.status == "error" for c in execution.tool_calls)
    recovered = load("financial-research")[0]
    execution = await execute_graph(AgentConfig(name="Recovered", version="1"), recovered, sandbox)
    assert score(recovered, execution).passed
