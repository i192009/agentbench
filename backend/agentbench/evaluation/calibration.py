"""Report judge agreement against independently supplied labels, never self-agreement as truth."""

from collections import defaultdict

import numpy as np


def calibration_report(records: list[dict], thresholds: list[float] | None = None) -> dict:
    if not records:
        return {"status": "INCONCLUSIVE", "reason": "No independently labeled records"}
    labeled = [
        r for r in records if isinstance(r.get("reference_passed"), bool) and r.get("judge_score") is not None
    ]
    errors = len(records) - len(labeled)
    if not labeled:
        return {"status": "INCONCLUSIVE", "reason": "No usable independent labels", "errors": errors}
    sensitivity = []
    for threshold in thresholds or [0.6, 0.7, 0.8, 0.9]:
        if not 0 <= threshold <= 1:
            raise ValueError("Thresholds must be in [0,1]")
        correct = sum((r["judge_score"] >= threshold) == r["reference_passed"] for r in labeled)
        sensitivity.append(
            {
                "threshold": threshold,
                "agreement_with_reference": correct / len(labeled),
                "count": len(labeled),
            }
        )
    grouped: dict[str, list[float]] = defaultdict(list)
    for record in labeled:
        grouped[record["case_id"]].append(record["judge_score"])
    disagreements = [r["case_id"] for r in labeled if (r["judge_score"] >= 0.8) != r["reference_passed"]]
    return {
        "status": "MEASURED",
        "reference_source": "caller-supplied independent labels; provenance must be reviewed",
        "usable_records": len(labeled),
        "errors": errors,
        "threshold_sensitivity": sensitivity,
        "human_review_queue": sorted(set(disagreements)),
        "repeated_judge_stddev": {k: float(np.std(v)) for k, v in grouped.items() if len(v) > 1},
        "warning": "Repeated-judge consistency does not establish factual accuracy",
    }
