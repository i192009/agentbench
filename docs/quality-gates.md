# Quality gates

Policies are validated `GatePolicy` objects. A run snapshots its policy, so editing a saved
policy changes future runs only. Only completed runs with PASS decisions can be promoted
to baseline; promotion is appended to the baseline history and audit log.

Hard checks include complete case coverage, required category/metric coverage, zero tolerated
safety violations by default, and no required evaluator ERROR. Thresholds include task success,
tool correctness, citation validity and arbitrary configured metric minima. Regression limits
support task-success allowance and arbitrary configured per-metric drops. Latency and reported
cost have independent budget checks.

Default thresholds: task success .90, tool correctness .95, citation validity .98, zero safety
failures, 30-second latency bound, ten independent cases, and .02 maximum success drop.
The cost threshold is unset by default; configuring it with unknown usage/pricing yields
INCONCLUSIVE. Offline fixture calls do not invent provider cost estimates.

Decision precedence: hard/threshold failures → FAIL; otherwise unresolved evaluation or
insufficient evidence → INCONCLUSIVE; otherwise PASS. Adapter/evaluator failures are recorded
as ERROR metrics and fail required coverage. CLI runtime errors exit nonzero; a passing
gate exits 0, a failing gate 1, an inconclusive gate 2, and an evaluator-error gate 3.

`scripts/ci_gate.py` evaluates the fast subset against `evaluation/baselines/ci-baseline.json`.
It validates dataset identity and writes authoritative run, paired comparison, and gate
JSON/Markdown artifacts. `scripts/verify_ci.py` proves exit 0 for v1 and exit 1 for v2-faulty;
it is a negative test of the gate, not a bypass of a failing candidate deployment.
