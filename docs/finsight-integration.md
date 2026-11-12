# FinSight AI adapter

Source inspected, without modification: https://github.com/i192009/finsight-ai at
`fb75952a28be92d5f3134e17e9283c7cb6bb37ef`. The local working tree was clean.
Inspected files include `backend/app/agents/graph.py`, `schemas/contracts.py`,
`schemas/responses.py`, `api/v1/routes.py`, and financial calculation helpers.

The native workflow state includes request/plan, companies, facts, passages, calculations,
interpretation, sources, sections, report and errors. Native calculations use metrics such
as `revenue_growth` and `net_profit_margin`; normalization maps them to AgentBench metric
keys while preserving native provenance. Native sources and claim evidence quotes become
versioned documents and citations. Explicit sidecar claim bindings support structured
fact checks; the adapter does not infer semantic entailment from a source ID.

Offline mode loads explicitly supplied native-contract records. The 12 checked-in records
are authored synthetic fixtures matching inspected contracts, not captured original-app
executions. Tool telemetry is supplied explicitly; a report alone does not invent tool calls.
The faulty variant changes a numeric calculation and is detected independently of the source ID.

External mode reads the actual authenticated GET `/api/v1/research/reports/{report_id}`
contract from `runtime.base_url`. It requires `AB_EXTERNAL_AGENT_ORIGINS`, `AB_FINSIGHT_TOKEN`
and `runtime.resource_ids` mapping case IDs to report UUIDs. Optional `captured_tool_calls`
must come from an actual telemetry export. No arbitrary Python or undocumented endpoint runs.

The original application is not modified, started, or automatically authorized by this adapter.
Live deployment connectivity and its model/SEC workflows are unverified. The recorded fixture
mode and controlled regression are verified by tests and the API/Celery demonstration.
