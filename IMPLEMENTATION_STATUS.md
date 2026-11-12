# Implementation and verification status

Updated 2026-11-12. AgentBench is a runnable local reference platform; no production-certification claim is made.

## Implemented

- FastAPI, async SQLAlchemy/PostgreSQL, two Alembic revisions, immutable agent/dataset/run snapshots.
- Organizations, project roles/memberships, Argon2, JWT, rotating HttpOnly refresh sessions, replay detection, audit records and rate limits.
- Agent/prompt/model/tool versions, explicit live-provider registration, frozen provider pricing, source-file and lockfile checksums.
- Dataset import/export in JSON/JSONL/CSV, draft editing, cloning, freezing, comparison, validation and pagination.
- Five 30-case suites, a separate 12-case CI subset, one development case and 24 additional native-contract fixtures.
- Real LangGraph research/operations workflows, parallel analysis, conditions, SQLite checkpoints, approval interrupts and resume.
- Four official-SDK MCP services, 21 tools, actual stdio/Streamable HTTP sessions, schema validation, fault injection and simulated idempotent corrections.
- Independent trace/tool/argument/order/task/numeric/workflow/citation/fact-support/retrieval/safety/budget evaluators.
- Official Ragas ID scorers and DeepEval name-only tool correctness in tested offline configurations; optional structured live planning/judging with explicit budgets and errors.
- Celery/Redis, bounded concurrency/project leases, cancellation, durable progress/SSE, unique results and durable dispatch recovery.
- Paired bootstrap comparisons, clustered repetitions, Wilson intervals, effect sizes and configurable PASS/FAIL/INCONCLUSIVE/ERROR gates.
- Real SQL-backed MLflow experiments, supported GenAI scores, traces/artifacts; OpenTelemetry propagation/export and Prometheus persisted gauges.
- Ten-view React/TypeScript dashboard, TanStack Query, actual-data Recharts, trace investigation, Vitest and Playwright.
- Administrator CLI, executable demonstrations, CI gates, benchmarks, recovery probe, Make targets, Compose and GitHub Actions definitions.

## Verified

- Backend: **73 tests passed**; four documented Ragas compatibility deprecation warnings. Includes all 150 curated scenarios, real MCP, approval resume, tenant isolation, immutable histories, imports/exports, concurrent persistence, timeout recovery, worker/source mismatch rejection and inline-run dispatch isolation.
- Ruff and formatting passed. Mypy passed for 38 application modules.
- Frontend: **6 Vitest tests passed**; strict TypeScript and Vite build passed.
- Playwright passed login, dataset browsing, real evaluation launch/progress, results, traces, comparison, gate views and mobile checks. The final release-image rerun passed, including approval interrupt/resume, and its screenshots are retained.
- Two complete 13-run API/Celery/Streamable-HTTP demonstrations asserted every expected gate decision and RECORDED MLflow tracking.
- Research: 30/30 baseline, 12/30 calculation regression. Operations: 30/30 baseline, 19/30 broken guard with 11 safety failures. Adversarial: 30/30 defense, 0/30 vulnerable candidate with 30 safety failures.
- RAG and multi-step: 30/30 each. FinSight contract: 12/12 baseline, 0/12 faulty. LedgerGuard contract: 12/12 baseline, 8/12 faulty with four safety failures. CI subset: 12/12.
- CI subprocess proof returned 0 for the passing agent and 1 for the controlled regression.
- Actual Celery child termination after four completed results recovered all 24 cases without duplicate results or replacement of completed attempt IDs. Only the probe's lease was shortened; raw evidence is in `artifacts/reliability.json`.
- Benchmark admitted 10/50/100/500 cases at concurrency four; all 660 passed. Raw measurements and precise scope are in `artifacts/benchmark.json`.
- Original FinSight/LedgerGuard source trees were inspected at recorded commits, confirmed clean and left unchanged.
- Fresh self-contained backend/frontend images built; the default Compose stack started without source mounts and passed application health checks.

## Delivery evidence

- Final protocol, service-health, trace-propagation and MLflow correspondence proof: `artifacts/stack-verification.json` and `artifacts/mlflow-native-trace-proof.json`.
- Final browser screenshots, including approval interrupt/resume: `docs/screenshots/`.
- Consolidated actual check results: `artifacts/verification-summary.json`.
- Sources, both dependency lockfiles, documentation and measured evidence are included in the local Git delivery commit. No remote publication was requested.

## Unverified or limited

- Paid live model/judge calls and independent human judge calibration were not exercised. Missing configured judges return ERROR.
- Original-project live deployments were not exercised. Verified repository integration is synthetic native-contract/recorded fixtures. External mode reads inspected authenticated snapshot endpoints and does not claim to execute those original applications.
- Semantic Ragas/DeepEval configurations beyond the documented offline scorers remain unverified.
- Hosted GitHub Actions execution was not run; equivalent local checks and exit-code behavior were executed.
- Normal crash failover waits for the run-timeout lease, default 1,890 seconds. Accelerated probe timings do not represent normal failover latency.
- Recovery keeps completed cases and reruns interrupted cases. It does not promise exactly-once remote side effects or arbitrary native workflow state recovery.
- Approval resume is scripted fixture evaluation; there is no general external-workflow approval inbox.
- Native Windows ARM64 runtime verification was blocked by Application Control on a dependency DLL. Linux containers are verified; Node/Git were used from containers because host PATH lacked them.
- Trace archival is bounded database-backed JSON. Large streaming/object storage, multi-host fencing and extended distributed-load testing remain future work.
- No independent global prompt catalog, invitation/SSO system, managed secrets, TLS ingress or compliance certification is implemented. Prompts/models are versioned within immutable agent configurations.
- Ragas 0.4.3's supported ID compatibility interface emits deprecation warnings; equivalent ID scorers are absent from its suggested collections replacement.

No planned feature is represented by a success stub. See README and the individual guides for exact contracts and setup commands.
