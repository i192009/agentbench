# AgentBench evaluation

Run: `077019a2-7ecc-492e-a131-810de60003e0`
Mode: **offline**
Dataset SHA256: `fe885e967e9e68d0d50dabda104a5caca4f260f9ad79935ef790fee0810fa85c`

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

- `finance-001`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-002`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-003`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-004`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-005`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-006`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-007`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-008`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-009`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-010`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-011`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-012`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment

Offline fixture results do not evaluate live model reasoning. Judge assessments are not factual guarantees.
