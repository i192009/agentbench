# Regression analysis

Comparisons require identical frozen dataset checksums and identical case-ID sets.
Runs with missing pairs produce ERROR. Cases are paired before computing success deltas,
new failures, recovered cases, persistent failures, metric changes and tool-trajectory changes.

The implementation uses 2,000 bootstrap resamples and seed 42. Repetitions sharing a case
identifier are clustered before uncertainty estimation, so repeated outputs are not falsely
counted as independent scenarios. It reports effect size, a 95% interval, sample counts and
explicit INCONCLUSIVE status below the configured minimum independent sample size.

Per-metric paired intervals support configured regression thresholds. An observed drop
that exceeds its allowance but has an interval overlapping that allowance is INCONCLUSIVE.
A statistically supported drop whose interval is wholly below the allowed negative effect
fails the regression gate. Independent absolute quality thresholds can also fail.

Wilson intervals summarize bounded Bernoulli case success. Empirical latency p95 is shown
for at least 20 cases and p99 for at least 100. A smaller latency gate uses the conservative
sample maximum, with the basis recorded in the decision; it does not fabricate a p95 estimate.

These intervals describe the evaluated cases under the recorded setup. They do not guarantee
future model behavior or remove dataset selection bias. Frozen cases must not be silently
reused as optimization feedback.

CLI: `python -m agentbench eval compare --baseline baseline.json --candidate candidate.json
--fail-on-regression`. API: GET `/api/projects/{id}/comparisons?baseline_id=...&candidate_id=...`.
The CI path checks a pinned, measured report and persists separate comparison/gate artifacts.
