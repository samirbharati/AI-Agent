"""
Terminal and Command Execution REST and Streaming API endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.database.base import get_session_factory
from app.terminal.command_policy import CommandPolicyEngine
from app.terminal.process_manager import get_process_manager
from app.terminal.session_manager import get_session_manager
from app.terminal.terminal_schemas import (
    TerminalCommandResponse,
    TerminalExecuteRequest,
    TerminalProcessInfo,
    TerminalSessionCreate,
    TerminalSessionResponse,
    TerminalSessionUpdate,
)
from app.terminal.terminal_security import TerminalSecurity
from app.terminal.terminal_service import TerminalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/terminal", tags=["terminal"])


@router.get("/security/status")
async def get_terminal_security_status() -> dict[str, Any]:
    """Return Docker availability, isolation mode, and security boundaries."""
    docker_status = TerminalSecurity.check_docker_availability()
    return {
        "docker": docker_status,
        "powershell_available": True,
        "supported_shells": ["powershell", "cmd", "bash", "docker"],
        "isolation_tier": docker_status["isolation_mode"],
    }


@router.get("/sessions", response_model=list[TerminalSessionResponse])
async def list_terminal_sessions(
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[TerminalSessionResponse]:
    """List terminal sessions, automatically provisioning default tabs for the project."""
    svc = TerminalService(db)
    return await svc.list_sessions(project_id=project_id)


@router.post(
    "/sessions",
    response_model=TerminalSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_terminal_session(
    payload: TerminalSessionCreate,
    db: AsyncSession = Depends(get_db),
) -> TerminalSessionResponse:
    """Create a new custom terminal session."""
    svc = TerminalService(db)
    return await svc.create_session(payload)


@router.get("/sessions/{session_id}", response_model=TerminalSessionResponse)
async def get_terminal_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> TerminalSessionResponse:
    """Get metadata for a single terminal session."""
    svc = TerminalService(db)
    res = await svc.get_session(session_id)
    if not res:
        raise HTTPException(status_code=404, detail="Terminal session not found.")
    return res


@router.patch("/sessions/{session_id}", response_model=TerminalSessionResponse)
async def update_terminal_session(
    session_id: str,
    payload: TerminalSessionUpdate,
    db: AsyncSession = Depends(get_db),
) -> TerminalSessionResponse:
    """Update or rename a terminal session."""
    svc = TerminalService(db)
    res = await svc.update_session(session_id, payload)
    if not res:
        raise HTTPException(status_code=404, detail="Terminal session not found.")
    return res


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def close_terminal_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Close and terminate a terminal session."""
    svc = TerminalService(db)
    closed = await svc.close_session(session_id)
    if not closed:
        raise HTTPException(status_code=404, detail="Terminal session not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/execute", response_model=TerminalCommandResponse)
async def execute_command(
    session_id: str,
    req: TerminalExecuteRequest,
    db: AsyncSession = Depends(get_db),
) -> TerminalCommandResponse:
    """Execute a permitted command in the specified terminal session."""
    svc = TerminalService(db)
    try:
        return await svc.execute_in_session(session_id, req)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe)) from pe
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session_command(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Interrupt / stop running process in the session."""
    svc = TerminalService(db)
    success = await svc.interrupt_session(session_id)
    return {"session_id": session_id, "interrupted": success}


@router.post("/sessions/{session_id}/clear")
async def clear_session_terminal(session_id: str) -> dict[str, Any]:
    """Clear visible terminal output buffer."""
    sm = get_session_manager()
    await sm.clear_buffer(session_id)
    return {"session_id": session_id, "cleared": True}


@router.get("/sessions/{session_id}/history", response_model=list[TerminalCommandResponse])
async def get_session_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[TerminalCommandResponse]:
    """Get command execution history for a terminal session."""
    svc = TerminalService(db)
    return await svc.get_command_history(session_id=session_id, limit=limit, offset=offset)


@router.get("/commands/{command_id}", response_model=TerminalCommandResponse)
async def get_command_details(
    command_id: str,
    db: AsyncSession = Depends(get_db),
) -> TerminalCommandResponse:
    """Detailed inspection of a single command execution record."""
    svc = TerminalService(db)
    cmd = await svc.get_command_details(command_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Command execution not found.")
    return cmd


@router.get("/processes", response_model=list[TerminalProcessInfo])
async def list_active_processes(
    project_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[TerminalProcessInfo]:
    """List running processes across all terminal sessions."""
    svc = TerminalService(db)
    return svc.list_active_processes(project_id=project_id)


@router.post("/processes/{process_id}/stop")
async def stop_process(process_id: int) -> dict[str, Any]:
    """Explicitly terminate a running process."""
    pm = get_process_manager()
    stopped = await pm.stop_process(process_id)
    if not stopped:
        raise HTTPException(
            status_code=404, detail=f"Process {process_id} not found or not running."
        )
    return {"process_id": process_id, "stopped": True}


@router.get("/consoles/{console_type}")
async def get_specialized_console_commands(
    console_type: str,
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get commands matching a specialized console view (build, qa, security, git).
    """
    svc = TerminalService(db)
    all_cmds = await svc.get_command_history(project_id=project_id, limit=limit)
    filtered = []
    c_lower = console_type.lower()
    for c in all_cmds:
        cat = CommandPolicyEngine._detect_category(c.command)
        if c_lower == "build" and cat.value == "build":
            filtered.append(c)
        elif c_lower == "qa" and cat.value == "test":
            filtered.append(c)
        elif c_lower == "security" and cat.value == "security":
            filtered.append(c)
        elif c_lower == "git" and cat.value == "git":
            filtered.append(c)
        elif c_lower in ("general", "all"):
            filtered.append(c)

    return {"console_type": console_type, "count": len(filtered), "commands": filtered}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query(default="txt", pattern="^(txt|json|markdown)$"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download terminal output buffer in text, markdown, or JSON format."""
    svc = TerminalService(db)
    content, media_type = await svc.export_session_output(session_id, format_type=format)
    ext = "md" if format == "markdown" else format
    filename = f"terminal_session_{session_id[:8]}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sessions/{session_id}/stream")
async def stream_terminal_output(
    session_id: str,
    max_events: int | None = Query(default=None),
) -> StreamingResponse:
    """SSE live streaming of terminal stdout/stderr for a session."""
    sm = get_session_manager()
    queue = await sm.subscribe(session_id)

    async def event_generator():
        sent = 0
        try:
            # Send initial connected ping
            yield "event: ping\ndata: {}\n\n"
            sent += 1
            if max_events and sent >= max_events:
                return

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=10.0)
                    yield f"event: {item.type}\ndata: {json.dumps(item.model_dump())}\n\n"
                    sent += 1
                    if max_events and sent >= max_events:
                        break
                except TimeoutError:
                    yield "event: ping\ndata: {}\n\n"
                    sent += 1
                    if max_events and sent >= max_events:
                        break
        finally:
            await sm.unsubscribe(session_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """
    Bidirectional WebSocket connection for live terminal session.
    Sends real-time stdout/stderr lines and accepts client commands.
    """
    await websocket.accept()
    sm = get_session_manager()
    queue = await sm.subscribe(session_id)

    send_task = None
    try:

        async def _forward_events():
            while True:
                item = await queue.get()
                await websocket.send_text(json.dumps(item.model_dump()))

        send_task = asyncio.create_task(_forward_events())

        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue

            action = data.get("action")
            if action == "execute":
                command = data.get("command")
                if command:
                    factory = get_session_factory()
                    async with factory() as db:
                        svc = TerminalService(db)
                        req = TerminalExecuteRequest(
                            command=command,
                            working_directory=data.get("working_directory"),
                            agent_id=data.get("agent_id"),
                            timeout_seconds=data.get("timeout_seconds", 60),
                        )
                        try:
                            await svc.execute_in_session(session_id, req)
                        except Exception as ex:
                            await sm.broadcast_event(session_id, "error", f"[ERROR] {ex}\n")
            elif action == "interrupt":
                factory = get_session_factory()
                async with factory() as db:
                    svc = TerminalService(db)
                    await svc.interrupt_session(session_id)
            elif action == "clear":
                await sm.clear_buffer(session_id)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
    finally:
        if send_task:
            send_task.cancel()
        await sm.unsubscribe(session_id, queue)
