import pytest
from agentbench.evaluation.extensions import JudgeResponse, judge_metric
from agentbench.evaluation.quality_gates import apply_gate
from agentbench.evaluation.regression import aggregate, compare
from agentbench.evaluation.scoring import equivalent, score
from agentbench.schemas import Citation, Document, Execution, GatePolicy, ToolCall, TraceEvent
from agentbench.schemas import TestCase as Case


def simple():
    case = Case(
        id="unit",
        category="unit",
        input="Find the verified amount.",
        expected={"facts": {"amount": 100}, "required_tools": ["retrieve"], "citation_ids": ["d1"]},
    )
    execution = Execution(
        case_id=case.id,
        output={"amount": 100},
        documents=[Document(id="d1", content="Amount is 100 minor units.", facts={"amount": 100})],
        citations=[
            Citation(
                source_id="d1",
                claim="amount=100",
                fact_key="amount",
                fact_value=100,
                quote="Amount is 100 minor units.",
            )
        ],
        tool_calls=[ToolCall(name="retrieve", arguments={})],
    )
    execution.trace = [
        TraceEvent(trace_id="unit", case_id=case.id, event="AgentStarted"),
        TraceEvent(trace_id="unit", case_id=case.id, event="ToolCalled", data={"tool": "retrieve"}),
        TraceEvent(trace_id="unit", case_id=case.id, event="AgentFinished"),
    ]
    return case, execution


@pytest.mark.parametrize(
    "actual,expected,answer",
    [
        (1, 1, True),
        (1.00001, 1.0, True),
        (True, 1, False),
        ("NaN", 1, False),
        ("Infinity", 1, False),
        ("USD", "EUR", False),
        (100, 100.0, True),
        (None, 1, False),
    ],
)
def test_numeric_and_typed_comparison(actual, expected, answer):
    assert equivalent(actual, expected) is answer


def test_relative_tolerance():
    assert equivalent(1001, 1000, absolute=0, relative=0.002)
    assert not equivalent(1003, 1000, absolute=0, relative=0.002)


def test_valid_execution_passes():
    assert score(*simple()).passed


def test_valid_id_is_not_evidence_support():
    case, execution = simple()
    execution.documents[0].facts["amount"] = 50
    result = score(case, execution)
    assert next(m for m in result.metrics if m.name == "citation_validity").status == "PASS"
    assert next(m for m in result.metrics if m.name == "evidence_support").status == "FAIL"


@pytest.mark.parametrize("mutate", ["unknown_id", "wrong_version", "invented_quote", "missing_citation"])
def test_citation_failures(mutate):
    case, execution = simple()
    if mutate == "unknown_id":
        execution.citations[0].source_id = "fabricated"
    elif mutate == "wrong_version":
        execution.citations[0].source_version = "2"
    elif mutate == "invented_quote":
        execution.citations[0].quote = "A passage not present"
    else:
        execution.citations = []
    assert not score(case, execution).passed


def test_unsupported_free_text_is_inconclusive():
    case, execution = simple()
    execution.citations[0].fact_key = None
    result = score(case, execution)
    assert next(m for m in result.metrics if m.name == "semantic_entailment").status == "INCONCLUSIVE"


def test_blocked_unsafe_attempt_fails_safe_final_answer():
    case, execution = simple()
    execution.tool_calls.append(ToolCall(name="execute_payment", arguments={}, status="blocked"))
    result = score(case, execution)
    assert not result.passed
    assert next(m for m in result.metrics if m.name == "safety").status == "FAIL"


def test_trace_detects_approval_bypass_without_self_report():
    case, execution = simple()
    execution.trace = [
        TraceEvent(trace_id="a", case_id=case.id, event="ToolCalled", data={"tool": "execute_correction"})
    ]
    assert next(m for m in score(case, execution).metrics if m.name == "safety").status == "FAIL"


def test_order_constraints_allow_independent_calls():
    case, execution = simple()
    case.expected.order = [("retrieve", "calculate")]
    execution.tool_calls += [
        ToolCall(name="independent", arguments={}),
        ToolCall(name="calculate", arguments={}),
    ]
    execution.trace[-1:-1] = [
        TraceEvent(trace_id="unit", case_id=case.id, event="ToolCalled", data={"tool": name})
        for name in ["independent", "calculate"]
    ]
    assert score(case, execution).passed
    execution.tool_calls.reverse()
    assert next(m for m in score(case, execution).metrics if m.name == "tool_order").status == "FAIL"


def test_arguments_checked_on_every_retry():
    case, execution = simple()
    case.expected.arguments = {"retrieve": {"company": "ACME"}}
    execution.tool_calls[0].arguments = {"company": "OTHER"}
    execution.tool_calls.append(ToolCall(name="retrieve", arguments={"company": "ACME"}, attempt=2))
    assert next(m for m in score(case, execution).metrics if m.name == "tool_arguments").status == "FAIL"


def make_results(count=30, faulty=0):
    results = []
    for i in range(count):
        case, execution = simple()
        case.id, execution.case_id = f"case-{i}", f"case-{i}"
        if i < faulty:
            execution.output["amount"] = 999
        results.append(score(case, execution))
    return results


@pytest.mark.regression
def test_paired_bootstrap_reports_regression():
    result = compare(make_results(), make_results(faulty=20))
    assert result["statistical_regression"]
    assert result["delta_ci95"][1] < 0
    assert len(result["new_failures"]) == 20


@pytest.mark.regression
def test_small_sample_and_unpaired_runs_inconclusive_or_error():
    assert compare(make_results(3), make_results(3, 1))["status"] == "INCONCLUSIVE"
    assert compare(make_results(3), make_results(4))["status"] == "ERROR"


def test_passing_gate_and_missing_metric_failure():
    results = make_results()
    summary = aggregate(results)
    assert apply_gate(summary, GatePolicy(), 30, {"unit"})["status"] == "PASS"
    summary["metric_counts"].pop("safety")
    assert apply_gate(summary, GatePolicy(), 30, {"unit"})["status"] == "FAIL"


def test_unknown_cost_never_passes_cost_gate():
    result = apply_gate(aggregate(make_results()), GatePolicy(maximum_average_cost_usd=0.1), 30, {"unit"})
    assert result["status"] == "INCONCLUSIVE"


def test_missing_cases_and_required_suite_fail_gate():
    summary = aggregate(make_results())
    assert (
        apply_gate(summary, GatePolicy(required_categories=["adversarial"]), 31, {"unit"})["status"] == "FAIL"
    )


async def test_judge_missing_and_timeout_are_errors():
    case, execution = simple()
    assert (await judge_metric(case, execution, None)).status == "ERROR"

    class TimeoutJudge:
        async def evaluate(self, case, execution):
            raise TimeoutError("synthetic judge timeout")

    assert (await judge_metric(case, execution, TimeoutJudge())).status == "ERROR"


async def test_judge_structured_response_threshold():
    class Calibrated:
        async def evaluate(self, case, execution):
            return JudgeResponse(score=0.7, reason="Unsupported claim", unsupported_claims=["claim"])

    result = await judge_metric(*simple(), Calibrated())
    assert result.status == "FAIL"
    assert result.evidence["response"]["unsupported_claims"] == ["claim"]
