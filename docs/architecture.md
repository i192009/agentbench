# Architecture

The API manages projects, agent versions, dataset versions, gates and run requests.
An evaluation snapshots validated configuration and cases before dispatch. PostgreSQL
is authoritative. `RunEvent` rows provide durable progress; Redis is coordination and
delivery infrastructure, not the sole record of an evaluation.
Trusted operator CLI runs are explicitly marked as inline executions. The durable Celery
dispatcher excludes them, preventing a periodic scan from duplicating a local evaluation.

Celery acknowledges late and rejects tasks lost with a worker process. A Redis lease
prevents concurrent processing of the same run; project slots bound concurrent runs.
Each run executes at most `AB_CASE_CONCURRENCY` cases concurrently, in bounded batches.
The default worker has two processes, two project slots, and four concurrent cases per run.

The orchestration service loads an immutable snapshot, verifies its checksums, skips
already-persisted cases, invokes the selected adapter, runs independent scorers, and
writes case results. A unique `(run_id, case_id)` constraint handles duplicate deliveries.
Parent rows are locked before child inserts to avoid PostgreSQL FK lock-upgrade deadlocks.
External model, MCP and tracking calls happen outside application database transactions.

Adapters return a framework-independent `Execution`. Evaluators operate on that contract,
not LangGraph internals. MCP sessions use the official Python SDK. Each case gets a new
fixture scope; server-side approvals and idempotency keys cannot leak across cases.
No sandbox tool implements shell execution, arbitrary HTTP fetches, or real money movement.

MLflow has its own SQL database and stores measured experiment views, GenAI scores,
traces and artifacts. Tracking failures are persisted as ERROR metadata and do not erase
authoritative results. OpenTelemetry propagates API trace context through the immutable
run snapshot to worker, case, tool and scorer spans. The collector exports a local debug
stream; durable investigation traces remain in case results and MLflow artifacts.

The application stores bounded JSON artifacts in PostgreSQL. Tool outputs are capped
at 64 KiB before normalization; summaries and trace text are truncated and redacted.
There is no object-storage archive in this implementation. Dataset imports are capped at
8 MB and run admission at 1,000 executions including repetitions.

The React app has ten task-focused views. TanStack Query handles API state and refresh;
authenticated SSE updates the result view and periodic queries recover persisted state.
Recharts renders actual completed-run data. Unknown costs and unavailable measurements
are displayed explicitly rather than replaced with invented zeros.
