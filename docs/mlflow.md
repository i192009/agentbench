# MLflow integration

MLflow 3.18.0 runs with a PostgreSQL-backed store in the separate `mlflow` database and
artifact storage under the persistent `.runtime/mlartifacts` volume. Separate databases
avoid application/MLflow Alembic revision collisions. AgentBench remains authoritative.

Each tracked evaluation records agent/prompt/model identifiers, dataset version/checksum,
configuration checksum, mode, measured aggregate metrics, the snapshot, the report, and
per-case normalized execution artifacts. Supported `start_span` APIs create case traces.
`mlflow.genai.evaluate` with a custom supported `@scorer` reuses authoritative case pass
values; it does not invoke the traditional tabular-model evaluation API or reinterpret
the same metric using a second definition.

The returned tracking run ID and GenAI evaluation run ID are persisted in the AgentBench
summary. Tracking failures return ERROR metadata with a bounded reason. Disabled tracking
is labeled DISABLED. Neither state is fabricated as a successful experiment.
Compose explicitly enables MLflow dual export so supported traces reach both the MLflow
experiment and the local collector. OTLP uses HTTP/protobuf consistently for traces and metrics.

Open http://localhost:5050, select `AgentBench/<dataset>`, and locate the run by its
AgentBench UUID or `agentbench_run_id` parameter. Inspect metrics, evaluation results,
traces and JSON artifacts. `artifacts/verified-demo/demonstration.json` records the actual IDs.

The acceptance demonstration required RECORDED tracking for every run. Offline tracking
does not imply that a live model was evaluated. If the tracker becomes unavailable,
application results remain available and the tracking error is visible.

Primary reference: [MLflow GenAI evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/).
