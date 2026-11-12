# RAG evaluation

Deterministic ranking metrics compare retrieved source IDs against independently supplied
relevant IDs. Precision/recall credit each relevant source once; reciprocal rank uses the
first relevant rank. The synthetic filing tool uses lexical inverse-document-frequency
weighting to rank sources. This is a reproducible sandbox retrieval implementation, not
a claim about embedding-model retrieval quality.
The capped Precision@5 denominator is the available top-k count, `min(5, retrieved_count)`;
the actual k is recorded in metric evidence. Match this convention before comparing against
fixed-denominator external retrieval benchmarks.

Citation validity checks retrieved membership, source version, required IDs and exact
quoted spans. Structured evidence support separately compares claim-bound values with
the cited source's facts and actual output. A source can exist and still contradict its
attached claim; those cases pass identity validation and fail support.

Arbitrary prose requires semantic entailment assessment. A citation without a structured
fact binding is INCONCLUSIVE until an appropriate semantic judge is configured. Deterministic
fact support does not imply general natural-language faithfulness or real-world truth.

Ragas 0.4.3's official `SingleTurnSample`, `IDBasedContextPrecision`,
`IDBasedContextRecall` and `single_turn_ascore` were executed. That version marks this
interface deprecated but does not expose equivalent ID scorers in `metrics.collections`;
the dependency is pinned and the four emitted deprecation warnings are documented.

Modern model-based faithfulness/relevancy metrics are not silently substituted for these
offline scores. The optional structured judge is separate. Live Ragas semantic metrics and
independent human calibration are unverified.

Primary API reference: [Ragas context precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/).
