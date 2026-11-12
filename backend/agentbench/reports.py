import csv
import io
import json

from agentbench.schemas import CaseResult


def report_dict(run_id: str, snapshot: dict, summary: dict, results: list[CaseResult]) -> dict:
    return {
        "schema_version": "1",
        "run_id": run_id,
        "snapshot": snapshot,
        "summary": summary,
        "results": [r.model_dump(mode="json") for r in results],
    }


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# AgentBench evaluation",
        "",
        f"Run: `{report['run_id']}`",
        f"Mode: **{summary.get('mode', 'unknown')}**",
        f"Dataset SHA256: `{report['snapshot']['dataset_checksum']}`",
        "",
        f"Gate: **{summary.get('gate', {}).get('status', 'ERROR')}**",
        f"Cases: {summary.get('count', 0)}; passed: {summary.get('passed', 0)}; safety failures: {summary.get('safety_violations', 0)}.",
        "",
        "| Metric | Measured score |",
        "| --- | ---: |",
    ]
    for name, value in summary.get("metrics", {}).items():
        lines.append(f"| {name} | {value:.4f} |")
    lines += ["", "## Failed cases", ""]
    for result in report.get("results", []):
        if not result["passed"]:
            reasons = [
                f"{m['name']}: {m['reason']}"
                for m in result["metrics"]
                if m["status"] not in {"PASS", "NOT_APPLICABLE"}
            ]
            lines.append(f"- `{result['case_id']}`: " + "; ".join(reasons))
    comparison = summary.get("comparison")
    if comparison:
        lines += [
            "",
            "## Paired regression",
            "",
            f"Status: {comparison['status']}; effect size: {comparison.get('effect_size')}; 95% bootstrap interval: {comparison.get('delta_ci95')}.",
            f"New failures: {', '.join(comparison.get('new_failures', [])) or 'none'}.",
        ]
    lines += [
        "",
        "Offline fixture results do not evaluate live model reasoning. Judge assessments are not factual guarantees.",
        "",
    ]
    return "\n".join(lines)


def export_report(report: dict, format: str):
    if format == "json":
        return json.dumps(report, indent=2, ensure_ascii=False)
    if format == "md":
        return markdown(report)
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["case_id", "passed", "metric", "status", "score", "reason"])
        for result in report["results"]:
            for metric in result["metrics"]:
                writer.writerow(
                    [
                        result["case_id"],
                        result["passed"],
                        metric["name"],
                        metric["status"],
                        metric["score"],
                        metric["reason"],
                    ]
                )
        return output.getvalue()
    raise ValueError("Unsupported report format")
