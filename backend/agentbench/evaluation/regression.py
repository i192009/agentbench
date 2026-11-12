from collections import defaultdict

import numpy as np

from agentbench.schemas import CaseResult


def aggregate(results: list[CaseResult]) -> dict:
    metrics: dict[str, list[float]] = defaultdict(list)
    safety = errors = inconclusive = 0
    costs, latencies = [], []
    for result in results:
        for item in result.metrics:
            if item.score is not None:
                metrics[item.name].append(item.score)
            errors += item.status == "ERROR"
            inconclusive += item.status == "INCONCLUSIVE"
            if item.name == "safety" and item.status == "FAIL":
                safety += 1
        if result.execution.usage.cost_usd is not None:
            costs.append(result.execution.usage.cost_usd + (result.execution.usage.judge_cost_usd or 0))
        latencies.append(result.execution.latency_ms)
    n = len(results)
    passed = sum(r.passed for r in results)
    # Wilson interval, valid for a bounded Bernoulli case-success aggregate.
    z = 1.96
    if n:
        p = passed / n
        denominator = 1 + z * z / n
        center = (p + z * z / (2 * n)) / denominator
        radius = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
        interval = [max(0, float(center - radius)), min(1, float(center + radius))]
    else:
        interval = None
    return {
        "count": n,
        "independent_cases": len({r.case_id.split("::repeat-")[0] for r in results}),
        "passed": passed,
        "failed": n - passed,
        "success_rate": passed / n if n else None,
        "success_rate_ci95": interval,
        "metrics": {k: float(np.mean(v)) for k, v in metrics.items()},
        "metric_counts": {k: len(v) for k, v in metrics.items()},
        "safety_violations": safety,
        "evaluator_errors": errors,
        "inconclusive_scores": inconclusive,
        "average_latency_ms": float(np.mean(latencies)) if latencies else None,
        "maximum_latency_ms": max(latencies) if latencies else None,
        "p50_latency_ms": float(np.percentile(latencies, 50)) if latencies else None,
        "p95_latency_ms": float(np.percentile(latencies, 95)) if len(latencies) >= 20 else None,
        "p99_latency_ms": float(np.percentile(latencies, 99)) if len(latencies) >= 100 else None,
        "average_cost_usd": float(np.mean(costs)) if len(costs) == n and n else None,
        "total_known_cost_usd": sum(costs),
        "cost_coverage": len(costs) / n if n else 0,
        "input_tokens": sum(r.execution.usage.input_tokens or 0 for r in results),
        "output_tokens": sum(r.execution.usage.output_tokens or 0 for r in results),
        "judge_input_tokens": sum(r.execution.usage.judge_input_tokens or 0 for r in results),
        "judge_output_tokens": sum(r.execution.usage.judge_output_tokens or 0 for r in results),
        "total_known_judge_cost_usd": sum(r.execution.usage.judge_cost_usd or 0 for r in results),
        "tool_calls": sum(len(r.execution.tool_calls) for r in results),
        "retries": sum(c.attempt > 1 for r in results for c in r.execution.tool_calls),
    }


def compare(
    baseline: list[CaseResult], candidate: list[CaseResult], minimum_samples: int = 10, resamples: int = 2000
) -> dict:
    a, b = {r.case_id: r for r in baseline}, {r.case_id: r for r in candidate}
    keys = sorted(a.keys() & b.keys())
    if not keys or set(a) != set(b):
        return {
            "status": "ERROR",
            "reason": "Paired comparisons require identical case IDs",
            "missing_candidate": sorted(a.keys() - b.keys()),
            "missing_baseline": sorted(b.keys() - a.keys()),
        }
    deltas = np.array([float(b[k].passed) - float(a[k].passed) for k in keys])
    # Repetitions share a case ID prefix and are clustered for uncertainty.
    clusters: dict[str, list[float]] = defaultdict(list)
    for key, delta in zip(keys, deltas, strict=True):
        clusters[key.split("::repeat-")[0]].append(float(delta))
    cluster_means = np.array([np.mean(v) for v in clusters.values()])
    rng = np.random.default_rng(42)
    bootstrap = np.mean(rng.choice(cluster_means, size=(resamples, len(cluster_means)), replace=True), axis=1)
    low, high = np.percentile(bootstrap, [2.5, 97.5])
    enough = len(clusters) >= minimum_samples
    trajectory_changes = []
    for key in keys:
        old = [c.name for c in a[key].execution.tool_calls]
        new = [c.name for c in b[key].execution.tool_calls]
        if old != new:
            trajectory_changes.append({"case_id": key, "baseline": old, "candidate": new})
    summary_a, summary_b = aggregate(baseline), aggregate(candidate)
    metric_intervals = {}
    for name in summary_a["metrics"].keys() & summary_b["metrics"].keys():
        score_deltas = []
        for key in keys:
            old_score = next((m.score for m in a[key].metrics if m.name == name), None)
            new_score = next((m.score for m in b[key].metrics if m.name == name), None)
            if old_score is not None and new_score is not None:
                score_deltas.append((key.split("::repeat-")[0], new_score - old_score))
        by_case: dict[str, list[float]] = defaultdict(list)
        for key, delta in score_deltas:
            by_case[key].append(delta)
        if by_case:
            independent = [float(np.mean(v)) for v in by_case.values()]
            draws = np.mean(rng.choice(independent, size=(resamples, len(independent)), replace=True), axis=1)
            metric_intervals[name] = [float(v) for v in np.percentile(draws, [2.5, 97.5])]
    return {
        "status": "CONCLUSIVE" if enough else "INCONCLUSIVE",
        "paired_count": len(keys),
        "independent_cases": len(clusters),
        "effect_size": float(np.mean(deltas)),
        "delta_ci95": [float(low), float(high)],
        "statistical_regression": bool(enough and high < 0),
        "resamples": resamples,
        "seed": 42,
        "new_failures": [k for k in keys if a[k].passed and not b[k].passed],
        "recovered": [k for k in keys if not a[k].passed and b[k].passed],
        "persistent_failures": [k for k in keys if not a[k].passed and not b[k].passed],
        "trajectory_changes": trajectory_changes,
        "metric_deltas": {
            k: summary_b["metrics"][k] - v
            for k, v in summary_a["metrics"].items()
            if k in summary_b["metrics"]
        },
        "metric_ci95": metric_intervals,
        "latency_delta_ms": summary_b["average_latency_ms"] - summary_a["average_latency_ms"],
        "baseline": summary_a,
        "candidate": summary_b,
    }
