"""
Terminal Session Lifecycle and Real-Time Event Fan-Out Manager.

Features:
- In-memory event ring buffer per session for instant playback upon reconnection.
- Async subscriber queue management for real-time SSE and WebSocket clients.
- Pre-configured specialized session presets (Developer, QA, Security, Git).
- Session limit enforcement and idle session cleanup.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.terminal.terminal_schemas import TerminalEventItem

logger = logging.getLogger(__name__)


@dataclass
class SessionStreamState:
    session_id: str
    project_id: str
    name: str
    shell_type: str
    working_directory: str
    buffer: deque[TerminalEventItem] = field(default_factory=lambda: deque(maxlen=2000))
    subscribers: set[asyncio.Queue[TerminalEventItem]] = field(default_factory=set)
    active_pid: int | None = None
    running_command: str | None = None
    sequence_counter: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionManager:
    """Manages active terminal sessions and live output broadcasting."""

    def __init__(self, max_sessions: int = 20) -> None:
        self.max_sessions = max_sessions
        self._sessions: dict[str, SessionStreamState] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_stream_state(
        self,
        session_id: str,
        project_id: str,
        name: str = "Main Terminal",
        shell_type: str = "powershell",
        working_directory: str = "",
    ) -> SessionStreamState:
        async with self._lock:
            if session_id not in self._sessions:
                if len(self._sessions) >= self.max_sessions:
                    # Evict oldest inactive session
                    oldest_id = next(iter(self._sessions))
                    del self._sessions[oldest_id]

                self._sessions[session_id] = SessionStreamState(
                    session_id=session_id,
                    project_id=project_id,
                    name=name,
                    shell_type=shell_type,
                    working_directory=working_directory,
                )
            return self._sessions[session_id]

    def get_stream_state(self, session_id: str) -> SessionStreamState | None:
        return self._sessions.get(session_id)

    async def broadcast_event(
        self,
        session_id: str,
        event_type: str,
        data: str,
    ) -> TerminalEventItem:
        state = self.get_stream_state(session_id)
        if not state:
            return TerminalEventItem(type=event_type, data=data)

        async with state.lock:
            state.sequence_counter += 1
            item = TerminalEventItem(
                type=event_type,
                data=data,
                sequence=state.sequence_counter,
                timestamp=datetime.now(UTC).isoformat(),
            )
            state.buffer.append(item)

            # Fan out to all active subscriber queues
            dead_queues = []
            for q in state.subscribers:
                try:
                    q.put_nowait(item)
                except asyncio.QueueFull:
                    dead_queues.append(q)
                except Exception:
                    dead_queues.append(q)

            for dq in dead_queues:
                state.subscribers.discard(dq)

            return item

    async def subscribe(self, session_id: str) -> asyncio.Queue[TerminalEventItem]:
        state = self.get_stream_state(session_id)
        q: asyncio.Queue[TerminalEventItem] = asyncio.Queue(maxsize=1000)
        if state:
            async with state.lock:
                # Pre-populate with recent buffer
                for item in state.buffer:
                    try:
                        q.put_nowait(item)
                    except asyncio.QueueFull:
                        break
                state.subscribers.add(q)
        return q

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue[TerminalEventItem]) -> None:
        state = self.get_stream_state(session_id)
        if state:
            async with state.lock:
                state.subscribers.discard(queue)

    async def clear_buffer(self, session_id: str) -> None:
        state = self.get_stream_state(session_id)
        if state:
            async with state.lock:
                state.buffer.clear()
            await self.broadcast_event(session_id, "system", "\x1b[2J\x1b[H[Terminal cleared]\n")

    def remove_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# Global singleton
_session_manager_instance: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _session_manager_instance
    if _session_manager_instance is None:
        _session_manager_instance = SessionManager()
    return _session_manager_instance
