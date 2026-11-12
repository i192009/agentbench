# Real MCP testing

`agentbench.mcp.server` creates four official `FastMCP` services. The runner uses actual
`ClientSession` initialization, `list_tools`, discovered JSON schemas and `call_tool`.
There is no REST-to-MCP naming shortcut.

| Service | Tools |
| --- | --- |
| financial | get_company_profile, get_financial_statements, get_revenue_history, calculate_financial_ratio, search_financial_filings |
| transactions | list_transactions, get_transaction, find_duplicate_transactions, get_account_balances, search_transaction_history |
| risk | assess_transaction_risk, detect_transaction_anomalies, compare_ledger_entries, find_reconciliation_discrepancies, generate_reconciliation_report |
| approvals | create_approval_request, get_approval_status, list_pending_approvals, cancel_approval_request, resolve_approval, execute_correction |

`resolve_approval` is driver-only; `execute_correction` has no real financial backend.
The original requirement's 19 tools are present, with these two additional simulation tools.

Compose runs Streamable HTTP on `/mcp`, with bearer authentication and local health endpoints.
No MCP port is published to the host. Stdio runs use the same servers and protocol.
The installed SDK is pinned to 1.30.0, the compatible 1.x API line inspected during implementation.

Faults are fixture data: `fault: {tool, kind, seconds}`. Supported kinds include temporary
failure, slow/timeout delay, permanent error, malformed statement output and empty statement
output. Temporary failures retry within an explicit limit; errors and retries are traced.
Wrong argument types are rejected by discovered JSON schema validation before dispatch.

The test driver supplies raw synthetic facts and evidence, never test expectations, to
tools. Every case gets a new scope. Tool-call limits, per-call timeouts, permission checks,
64 KiB result limits and normalized errors bound execution. MCP server inputs cannot request
shell execution or arbitrary network access. Stdio environment allowlisting and minimal HTTP
service environments exclude live model/database credentials.

Run `python scripts/smoke_core.py` with the desired MCP transport configured. The integration
tests initialize and call the actual protocol and verify invalid arguments. The full API/Celery
demonstration exercised Streamable HTTP; the deterministic test suite exercised stdio.

Primary SDK reference: [official Python SDK](https://github.com/modelcontextprotocol/python-sdk).
