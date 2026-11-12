from agentbench.evaluation.calibration import calibration_report
from agentbench.evaluation.quality_gates import apply_gate
from agentbench.evaluation.regression import aggregate, compare
from agentbench.schemas import GatePolicy
from test_evaluators import make_results


def test_independent_calibration_reports_disagreement():
    report = calibration_report(
        [
            {"case_id": "a", "reference_passed": True, "judge_score": 0.9},
            {"case_id": "b", "reference_passed": False, "judge_score": 0.9},
            {"case_id": "b", "reference_passed": False, "judge_score": 0.4},
        ]
    )
    assert report["human_review_queue"] == ["b"]
    assert report["repeated_judge_stddev"]["b"] > 0
    assert calibration_report([])["status"] == "INCONCLUSIVE"


def test_metric_regression_and_required_metric_thresholds():
    baseline, candidate = make_results(), make_results(faulty=30)
    paired = compare(baseline, candidate)
    assert paired["metric_ci95"]["numeric_accuracy"] == [-1, -1]
    policy = GatePolicy(maximum_metric_drops={"numeric_accuracy": 0.05})
    assert any(
        "numeric_accuracy" in reason
        for reason in apply_gate(aggregate(candidate), policy, 30, {"unit"}, paired)["failures"]
    )
    policy = GatePolicy(minimum_metric_scores={"semantic_judge_not_run": 0.8})
    assert apply_gate(aggregate(baseline), policy, 30, {"unit"})["status"] == "FAIL"


def test_repetitions_do_not_artificially_increase_independent_sample_size():
    results = make_results(3) * 5
    for index, result in enumerate(results):
        # Create copies because the source repetitions intentionally share objects.
        results[index] = result.model_copy(deep=True)
        results[index].case_id = f"case-{index % 3}::repeat-{index // 3 + 1}"
    summary = aggregate(results)
    assert summary["independent_cases"] == 3
    assert apply_gate(summary, GatePolicy(), 15, {"unit"})["status"] == "INCONCLUSIVE"


def test_evaluator_error_has_distinct_nonzero_gate_status():
    summary = aggregate(make_results())
    summary["evaluator_errors"] = 1
    gate = apply_gate(summary, GatePolicy(), 30, {"unit"})
    assert gate["status"] == "ERROR" and gate["exit_code"] == 3
