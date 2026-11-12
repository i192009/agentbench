# AgentBench evaluation

Run: `af185e6b-d246-4ff8-9b91-0c522a24602d`
Mode: **offline**
Dataset SHA256: `350b9b3a5771826029950df1cd700fa3675d8a6282995fe7db03b98135120002`

Gate: **FAIL**
Cases: 12; passed: 0; safety failures: 0.

| Metric | Measured score |
| --- | ---: |
| tool_selection | 1.0000 |
| trajectory_integrity | 1.0000 |
| tool_arguments | 1.0000 |
| tool_order | 1.0000 |
| task_completion | 0.0000 |
| numeric_accuracy | 0.0000 |
| workflow | 1.0000 |
| safety | 1.0000 |
| retrieval_hit_rate | 1.0000 |
| precision_at_5 | 1.0000 |
| recall_at_5 | 1.0000 |
| mrr | 1.0000 |
| citation_validity | 1.0000 |
| evidence_support | 0.0000 |
| budget | 1.0000 |

## Failed cases

- `finsight-001`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-002`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-003`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-004`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-005`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-006`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-007`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-008`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-009`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-010`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-011`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finsight-012`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment

## Paired regression

Status: CONCLUSIVE; effect size: -1.0; 95% bootstrap interval: [-1.0, -1.0].
New failures: finsight-001, finsight-002, finsight-003, finsight-004, finsight-005, finsight-006, finsight-007, finsight-008, finsight-009, finsight-010, finsight-011, finsight-012.

Offline fixture results do not evaluate live model reasoning. Judge assessments are not factual guarantees.
