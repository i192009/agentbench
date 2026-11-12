from agentbench.schemas import GatePolicy


def apply_gate(
    summary: dict, policy: GatePolicy, total: int, categories: set[str], comparison: dict | None = None
) -> dict:
    failures, unknown = [], []
    if summary.get("count", 0) != total or total == 0:
        failures.append("Required evaluation cases are missing")
    if summary.get("safety_violations", 0) > policy.maximum_safety_violations:
        failures.append("Critical safety invariant violated")
    if summary.get("evaluator_errors", 0):
        failures.append("Required evaluator returned ERROR")
    if summary.get("inconclusive_scores", 0):
        unknown.append("One or more evaluator scores are inconclusive")
    if not set(policy.required_categories).issubset(categories):
        failures.append("Required evaluation categories are missing")
    for required in policy.required_metrics:
        if summary.get("metric_counts", {}).get(required, 0) != total:
            failures.append("Missing required metric: " + required)
    if summary.get("independent_cases", summary.get("count", 0)) < policy.minimum_sample_size:
        unknown.append("Minimum independent sample size not met")
    for name, actual, threshold in [
        ("task success", summary.get("success_rate"), policy.minimum_success),
        (
            "tool correctness",
            summary.get("metrics", {}).get("tool_selection"),
            policy.minimum_tool_correctness,
        ),
        (
            "citation validity",
            summary.get("metrics", {}).get("citation_validity"),
            policy.minimum_citation_validity,
        ),
    ]:
        if actual is None:
            failures.append("Missing " + name)
        elif actual < threshold:
            failures.append(f"{name}: {actual:.4f} < {threshold:.4f}")
    p95 = summary.get("p95_latency_ms")
    latency_basis = (
        "empirical p95" if p95 is not None else "conservative sample maximum (fewer than 20 cases)"
    )
    if p95 is None:
        p95 = summary.get("maximum_latency_ms")
    if p95 is not None and p95 > policy.maximum_p95_latency_ms:
        failures.append("p95 latency exceeds limit")
    elif p95 is None:
        unknown.append("Latency budget cannot evaluate missing latency measurements")
    for name, threshold in policy.minimum_metric_scores.items():
        value = summary.get("metrics", {}).get(name)
        if value is None:
            failures.append("Missing configured threshold metric: " + name)
        elif value < threshold:
            failures.append(f"{name}: {value:.4f} < {threshold:.4f}")
    if policy.maximum_average_cost_usd is not None:
        cost = summary.get("average_cost_usd")
        if cost is None:
            unknown.append("Cost gate cannot evaluate unknown usage/pricing")
        elif cost > policy.maximum_average_cost_usd:
            failures.append("Estimated cost exceeds limit")
    if comparison:
        if comparison["status"] in {"ERROR", "INCONCLUSIVE"}:
            unknown.append("Paired regression comparison is " + comparison["status"])
        elif comparison["effect_size"] < -policy.maximum_success_drop:
            if comparison["delta_ci95"][1] < -policy.maximum_success_drop:
                failures.append("Statistically supported task success regression exceeds allowance")
            else:
                unknown.append("Observed drop exceeds allowance but uncertainty overlaps threshold")
        for name, allowance in policy.maximum_metric_drops.items():
            delta = comparison.get("metric_deltas", {}).get(name)
            interval = comparison.get("metric_ci95", {}).get(name)
            if delta is None or interval is None:
                failures.append("Missing configured regression metric: " + name)
            elif delta < -allowance:
                if comparison["status"] == "CONCLUSIVE" and interval[1] < -allowance:
                    failures.append("Statistically supported metric regression: " + name)
                else:
                    unknown.append("Metric regression is inconclusive: " + name)
    status = "FAIL" if failures else "INCONCLUSIVE" if unknown else "PASS"
    if (
        summary.get("evaluator_errors", 0)
        and summary.get("safety_violations", 0) <= policy.maximum_safety_violations
    ):
        status = "ERROR"
    return {
        "status": status,
        "failures": failures,
        "inconclusive": unknown,
        "policy": policy.model_dump(),
        "latency_check_basis": latency_basis,
        "exit_code": {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 2, "ERROR": 3}[status],
    }
