"""Run the offline CI subset, compare a pinned real report, and return the quality gate exit code."""

import argparse
import asyncio
import json
from pathlib import Path

from agentbench.cli import get_report, resolve_run
from agentbench.evaluation.orchestration import evaluate_run
from agentbench.evaluation.quality_gates import apply_gate
from agentbench.evaluation.regression import compare
from agentbench.reports import export_report
from agentbench.schemas import CaseResult, GatePolicy


async def main(args):
    pinned = json.loads(args.baseline.read_text(encoding="utf-8"))
    run_id = await resolve_run(
        "Financial Research", "ci-smoke", args.version, "offline", None, ["deterministic"]
    )
    summary = await evaluate_run(run_id)
    report = await get_report(run_id)
    if report["snapshot"]["dataset_checksum"] != pinned["snapshot"]["dataset_checksum"]:
        raise ValueError(
            "Pinned baseline dataset checksum does not match; explicitly review and promote a new baseline"
        )
    comparison = compare(
        [CaseResult.model_validate(r) for r in pinned["results"]],
        [CaseResult.model_validate(r) for r in report["results"]],
    )
    gate = apply_gate(summary, GatePolicy(), len(report["results"]), {"financial-research"}, comparison)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "run.json").write_text(export_report(report, "json"), encoding="utf-8")
    (args.output / "run.md").write_text(export_report(report, "md"), encoding="utf-8")
    decision = {
        "decision_scope": "external CI paired comparison of exported authoritative results",
        "gate": gate,
        "comparison": comparison,
        "run_id": run_id,
        "pinned_baseline_run_id": pinned["run_id"],
    }
    (args.output / "quality-gate.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    (args.output / "quality-gate.md").write_text(
        f"# AgentBench CI quality gate\n\n**{gate['status']}** (exit {gate['exit_code']})\n\nPaired cases: {comparison.get('paired_count')}\n\nEffect size: {comparison.get('effect_size')}\n\n95% interval: {comparison.get('delta_ci95')}\n\n"
        + "\n".join("- " + f for f in gate["failures"] + gate["inconclusive"])
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps({"run_id": run_id, "gate": gate, "new_failures": comparison.get("new_failures")}, indent=2)
    )
    return gate["exit_code"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=Path("evaluation/baselines/ci-baseline.json"))
    parser.add_argument("--version", default="v1")
    parser.add_argument("--output", type=Path, default=Path("artifacts/ci"))
    raise SystemExit(asyncio.run(main(parser.parse_args())))
