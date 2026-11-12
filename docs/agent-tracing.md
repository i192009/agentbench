# Agent tracing

`TraceEvent` carries run/case/trace/span IDs, parent span, node, event, timestamp, duration
and redacted structured data. The normalized format is independent of LangGraph.

Captured events include agent lifecycle, model invocation/response, tool selection/call/
return, retrieval, state transitions, approval request/receipt, retries, budget exhaustion
and errors. Tool calls also have normalized arguments, result/error, status, attempt,
schema validity and measured duration.

LangGraph graph nodes explicitly record their transitions. The operations graph forks
duplicate and risk analysis, joins at reconciliation, creates an approval request in a
separate node, interrupts for a decision, and resumes with `Command(resume=...)`.
The separate request node prevents replaying request creation when the interrupt node restarts.
SQLite checkpoints are scoped to a single execution under `.runtime/checkpoints/`.

The driver resolves a synthetic decision through a privileged MCP tool that is excluded
from the agent permission set. The agent then reads authoritative approval status before
execution. The correction MCP server checks matching scope and approval independently.

Trace investigation: open Results → case → Trace explorer. Select an event for exact
arguments, results or error data. The Tools, Evidence and Output tabs expose complementary
views; failing metric evidence appears above the timeline.

Secret-like keys and bearer/API-key patterns are redacted; text and collections are bounded.
Provider keys and database configuration are not inherited by stdio sandbox processes;
HTTP sandbox containers receive only their synthetic authorization token.

OpenTelemetry spans share propagated run context. Normalized trace IDs use the active
OpenTelemetry trace where present. The local collector is an operational export, while
persisted case artifacts are the durable source for dashboard investigation.

Recovery skips completed results and reruns interrupted cases. It does not reload a crashed
case's out-of-process tool state or guarantee exactly-once remote side effects. Interactive
approval management for arbitrary uploaded workflows is outside the current dashboard.
