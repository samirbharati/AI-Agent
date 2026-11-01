"""
Correlation and distributed tracing context for AgentForge multi-agent operations.

Allows linking events across workflow stages, agent invocations, tool runs,
and test executions using contextvars.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Generator
from contextlib import contextmanager

_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_trace_id", default=None
)
_current_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_span_id", default=None
)


def generate_trace_id() -> str:
    """Generate a 16-character hexadecimal trace ID."""
    return uuid.uuid4().hex[:16]


def generate_span_id() -> str:
    """Generate an 8-character hexadecimal span ID."""
    return uuid.uuid4().hex[:8]


def get_current_trace_id() -> str | None:
    """Retrieve the current trace ID if one has been set in this context."""
    return _current_trace_id.get()


def set_current_trace_id(trace_id: str | None) -> None:
    """Set the active trace ID for the current async task / context."""
    _current_trace_id.set(trace_id)


def get_current_span_id() -> str | None:
    """Retrieve the active span ID."""
    return _current_span_id.get()


@contextmanager
def trace_context(
    trace_id: str | None = None, span_id: str | None = None
) -> Generator[str, None, None]:
    """
    Context manager that sets the active trace ID and optional span ID,
    restoring previous values on exit.
    """
    tid = trace_id or generate_trace_id()
    sid = span_id or generate_span_id()

    token_trace = _current_trace_id.set(tid)
    token_span = _current_span_id.set(sid)
    try:
        yield tid
    finally:
        _current_trace_id.reset(token_trace)
        _current_span_id.reset(token_span)
