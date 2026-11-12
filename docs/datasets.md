# Dataset management

Five frozen regression suites contain 30 cases each:

| Suite | Main assertions |
| --- | --- |
| Financial research | Growth/margins/ratios, missing periods, units/currency, ambiguity, stale/conflicting evidence |
| Financial operations | Duplicate detection, risk thresholds, reconciliation, account scope, approval, rejection/expiry, idempotency |
| RAG | Exact facts, versions, irrelevant sources, contradictory sources, missing evidence, long-context ranking |
| Adversarial | Thirty distinct lower-trust injection and authorization attacks |
| Multi-step | Dependent calls, parallel analysis, errors/retries, approval interrupts/resume, budget containment, conversation context |

The checked-in JSON is the benchmark. `datasets/manifest.json` records canonical SHA256
checksums and case counts. The reviewed scenario generator is development tooling;
do not regenerate and replace a frozen benchmark after observing a failure. Create a
new dataset version and review its provenance instead.

There is a separate one-case development set, a clearly identified 12-case CI subset,
and two additional 12-case native-contract suites under `examples/repository-contracts/`.
The CI subset intentionally samples the regression scenarios; it is not an independent
holdout. The development case has a distinct value and identifier. No automatic training
or prompt-optimization feedback loop consumes the frozen data.

Create/import a dataset in the dashboard or POST `/api/projects/{project_id}/datasets`.
The dataset body follows `DatasetFile`; cases follow `TestCase`. JSON imports the full
manifest. JSONL imports one case per line. CSV represents nested fields as JSON strings.
Exports preserve those fields; non-tabular data must use the nested contract.

Draft cases can be edited with PUT `dataset-versions/{id}/cases/{case_id}`. Freeze validates
the checksum. Evaluation also freezes a draft automatically. Database triggers protect
frozen cases and versions. Clone creates a new numbered draft; export/compare retains
the original history. Import/export and clone checksums sort cases by ID for canonical order.

Limits: 8 MB import, 2,000 cases per dataset contract, 1,000 case executions per run
including repetitions. Case inputs are at most 16,000 characters and conversations 50 turns.
