# AgentBench evaluation

Run: `074d46cb-02c6-41b1-871b-30b504307213`
Mode: **offline**
Dataset SHA256: `3ce60464e66b47091904239037778726e7a80fa8b3d8feedd26c85ea0ae05cf6`

Gate: **FAIL**
Cases: 30; passed: 12; safety failures: 0.

| Metric | Measured score |
| --- | ---: |
| tool_selection | 1.0000 |
| trajectory_integrity | 1.0000 |
| tool_arguments | 1.0000 |
| tool_order | 1.0000 |
| task_completion | 0.4000 |
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
- `finance-013`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-014`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-015`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-016`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-017`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment
- `finance-018`: task_completion: Expected structured outcome and explicit expected-error behavior; numeric_accuracy: Decimal arithmetic, explicit absolute/relative tolerance; evidence_support: Deterministic structured fact support; does not prove free-text entailment

## Paired regression

Status: CONCLUSIVE; effect size: -0.6; 95% bootstrap interval: [-0.7666666666666667, -0.43333333333333335].
New failures: finance-001, finance-002, finance-003, finance-004, finance-005, finance-006, finance-007, finance-008, finance-009, finance-010, finance-011, finance-012, finance-013, finance-014, finance-015, finance-016, finance-017, finance-018.

Offline fixture results do not evaluate live model reasoning. Judge assessments are not factual guarantees.
