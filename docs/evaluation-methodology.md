# Evaluation methodology

An evaluation unit is a validated test case plus its complete normalized execution.
Gold data is independent of the adapter output. Cases specify required/allowed/forbidden
tools, expected arguments, partial order constraints, structured outcomes, facts, sources,
citation identities, graph nodes, forbidden transitions, terminal states and budgets.

Each metric records a score when meaningful, a status, evidence, explanation, evaluator
version and measured evaluation duration. An ERROR or INCONCLUSIVE metric cannot make a
case pass. Missing lifecycle/tool trajectory evidence returns an explicit integrity ERROR.

Deterministic checks include:

- Tool selection: required calls must have succeeded; forbidden and unauthorized attempts count.
- Arguments: official MCP JSON schemas plus independent case-specific values and tolerances.
- Order: required precedence only, allowing independent analysis branches to commute.
- Task/numerics: expected structured outcomes, Decimal comparisons and explicit tolerances.
- Workflow: intermediate nodes, forbidden transitions, final state and step budgets.
- Safety: forbidden calls, blocked attempts, approval timing and protected synthetic values.
- Retrieval: hit rate, Precision@5, Recall@5 and reciprocal rank, with unique relevance credit.
- Citation validity: retrieved source ID/version, required citations and exact quoted spans.
- Evidence support: claim-bound structured fact comparisons, separate from identity checks.

Abstention is correct when the case explicitly requires it for missing, contradictory,
ambiguous, incompatible or undefined evidence. Expected tool errors are tested as outcomes;
unanticipated failures remain failures. Budget exhaustion is recognized as an expected
contained outcome only when the case explicitly specifies that error behavior.

Ragas/DeepEval are optional extension scorers. Ragas uses real ID-based precision/recall.
DeepEval uses real name-only tool correctness without inference; an injected model object
raises if that configuration tries to call a model. Neither implies semantic truth.

The structured judge Protocol supports a separate explicitly enabled live provider adapter.
Responses validate against `JudgeResponse`. Timeouts and malformed outputs produce ERROR;
missing configuration does not become PASS. Critical authorization invariants remain
deterministic regardless of judge opinion. Provider usage and explicit prices determine
estimates; unavailable usage stays unknown. Reservations bound spending before requests.

Calibration utilities accept independently labeled records, report threshold sensitivity,
repeated-score dispersion and a disagreement review queue. No independent human calibration
or live judge accuracy is claimed. Repeated self-agreement is not a ground-truth test.
