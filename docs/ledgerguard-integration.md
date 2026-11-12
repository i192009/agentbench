# LedgerGuard AI adapter

Source inspected, without modification: https://github.com/i192009/ledgerguard-ai at
`bfc8892e25e645fc1a3771782474e2572a1d0201`. The local working tree was clean.
Inspected files include `src/ledgerguard/orchestrator.py`, `api.py`, `models.py`,
`schemas.py`, `mcp_server.py`, and governance-related code.

The native supervisor fans out transaction, risk and reconciliation nodes, joins at
governance, interrupts at human review, and proceeds through an authorized executor and
reporter. Native `AgentRun` records contain request/status/state/error. `AgentEvent`
records carry event/data; `ToolExecution` records carry server/tool/duration/status/details.

The adapter normalizes native approval-required/received/action-executed events. It checks
execution timing against approval, final state, report creation and supplied native tool
telemetry. Unknown native arguments are not invented. Contract fixtures include approved,
rejected and expired outcomes. A faulty fixture variant removes authorization evidence;
the apparently successful final report still fails the safety gate.

External mode uses the inspected authenticated GET `/api/v1/agents/runs/{run_id}` and
GET `/api/v1/mcp/tool-executions?run_id=...` contracts. Configure allowlisted `runtime.base_url`,
`runtime.resource_ids`, `AB_EXTERNAL_AGENT_ORIGINS` and `AB_LEDGERGUARD_TOKEN`.
Temporal approval evidence must be supplied as `runtime.captured_events` from a real export;
the adapter does not invent a native approval operation.

The 12 offline fixtures are synthetic native contracts, not original application executions.
Live original-deployment connectivity is unverified. Separately, the built-in operations
agent executes actual LangGraph parallel branches, checkpoints, interrupts and resume over
real synthetic MCP services; approval guards and duplicate suppression were executed end to end.
