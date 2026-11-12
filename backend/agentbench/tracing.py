import re
from time import perf_counter
from typing import Any

from opentelemetry import trace

from agentbench.schemas import TraceEvent, uid

SENSITIVE = re.compile(
    r"password|secret|authorization|api[_-]?key|driver_token|refresh_token|access_token", re.I
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SENSITIVE.search(k) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value[:200]]
    if isinstance(value, str):
        value = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]+)", "[REDACTED]", value)
        return value[:16000]
    return value


class Recorder:
    def __init__(self, case_id: str, run_id: str = ""):
        self.case_id, self.run_id, self.trace_id = case_id, run_id, uid()
        self.root_span = uid().replace("-", "")[:16]
        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            self.trace_id = format(context.trace_id, "032x")
            self.root_span = format(context.span_id, "016x")
        self.events: list[TraceEvent] = []
        self.started = perf_counter()

    def add(self, event: str, node: str = "", duration_ms: float = 0, **data):
        item = TraceEvent(
            trace_id=self.trace_id,
            case_id=self.case_id,
            run_id=self.run_id,
            event=event,
            node=node,
            duration_ms=duration_ms,
            parent_span_id=self.root_span,
            data=redact(data),
        )
        self.events.append(item)
        return item
