"""
Terminal Execution Service.

Coordinates terminal sessions, safe process execution, real-time event
broadcasting, database persistence, and integration with the central Logs & Monitoring system.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging.correlation import generate_trace_id, get_current_trace_id
from app.logging.event_service import EventService
from app.models.db_models import (
    TerminalCommand,
    TerminalSession,
)
from app.terminal.command_policy import CommandPolicyEngine
from app.terminal.process_manager import ProcessManager, get_process_manager
from app.terminal.session_manager import SessionManager, get_session_manager
from app.terminal.terminal_schemas import (
    TerminalCommandResponse,
    TerminalExecuteRequest,
    TerminalProcessInfo,
    TerminalSessionCreate,
    TerminalSessionResponse,
    TerminalSessionUpdate,
)
from app.terminal.terminal_security import TerminalSecurity

logger = logging.getLogger(__name__)

# Standard preset tabs for project command execution
DEFAULT_SESSION_PRESETS = [
    {"name": "Main Terminal", "shell_type": "powershell", "created_by": "user"},
    {
        "name": "Developer Agent",
        "shell_type": "powershell",
        "created_by": "agent:software-developer",
    },
    {"name": "QA Execution", "shell_type": "powershell", "created_by": "agent:qa-engineer"},
    {
        "name": "Security Scanner",
        "shell_type": "powershell",
        "created_by": "agent:security-engineer",
    },
    {"name": "Git Operations", "shell_type": "powershell", "created_by": "agent:orchestrator"},
]


class TerminalService:
    """Core domain service for Terminal and Command Execution."""

    def __init__(
        self,
        db: AsyncSession,
        process_mgr: ProcessManager | None = None,
        session_mgr: SessionManager | None = None,
    ) -> None:
        self.db = db
        self.process_mgr = process_mgr or get_process_manager()
        self.session_mgr = session_mgr or get_session_manager()

    async def ensure_default_sessions(self, project_id: str) -> list[TerminalSession]:
        """Ensure standard set of tabs exists for the project."""
        stmt = select(TerminalSession).where(
            TerminalSession.project_id == project_id,
            TerminalSession.status == "active",
        )
        res = await self.db.execute(stmt)
        existing = list(res.scalars().all())
        if existing:
            return existing

        created_sessions = []
        for preset in DEFAULT_SESSION_PRESETS:
            session = TerminalSession(
                project_id=project_id,
                name=preset["name"],
                shell_type=preset["shell_type"],
                working_directory="",
                created_by=preset["created_by"],
                status="active",
            )
            self.db.add(session)
            created_sessions.append(session)

        await self.db.commit()
        for s in created_sessions:
            await self.db.refresh(s)
            await self.session_mgr.get_or_create_stream_state(
                session_id=s.id,
                project_id=project_id,
                name=s.name,
                shell_type=s.shell_type,
            )
        return created_sessions

    async def list_sessions(self, project_id: str | None = None) -> list[TerminalSessionResponse]:
        """List active terminal sessions, creating defaults if empty for a project."""
        if project_id:
            await self.ensure_default_sessions(project_id)
            stmt = (
                select(TerminalSession)
                .where(
                    TerminalSession.project_id == project_id,
                    TerminalSession.status == "active",
                )
                .order_by(TerminalSession.created_at)
            )
        else:
            stmt = (
                select(TerminalSession)
                .where(TerminalSession.status == "active")
                .order_by(TerminalSession.created_at)
            )

        res = await self.db.execute(stmt)
        sessions = res.scalars().all()

        responses = []
        for s in sessions:
            stream_state = self.session_mgr.get_stream_state(s.id)
            responses.append(
                TerminalSessionResponse(
                    id=s.id,
                    project_id=s.project_id,
                    name=s.name,
                    shell_type=s.shell_type,
                    working_directory=s.working_directory,
                    created_by=s.created_by,
                    status=s.status,
                    created_at=s.created_at.isoformat() if s.created_at else "",
                    closed_at=s.closed_at.isoformat() if s.closed_at else None,
                    running_command=stream_state.running_command if stream_state else None,
                    active_pid=stream_state.active_pid if stream_state else None,
                )
            )
        return responses

    async def create_session(self, payload: TerminalSessionCreate) -> TerminalSessionResponse:
        """Create a new custom terminal session."""
        session = TerminalSession(
            project_id=payload.project_id,
            name=payload.name,
            shell_type=payload.shell_type,
            working_directory=payload.working_directory or "",
            created_by="user",
            status="active",
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        await self.session_mgr.get_or_create_stream_state(
            session_id=session.id,
            project_id=session.project_id,
            name=session.name,
            shell_type=session.shell_type,
            working_directory=session.working_directory,
        )

        return TerminalSessionResponse(
            id=session.id,
            project_id=session.project_id,
            name=session.name,
            shell_type=session.shell_type,
            working_directory=session.working_directory,
            created_by=session.created_by,
            status=session.status,
            created_at=session.created_at.isoformat(),
        )

    async def get_session(self, session_id: str) -> TerminalSessionResponse | None:
        session = await self.db.get(TerminalSession, session_id)
        if not session:
            return None
        stream_state = self.session_mgr.get_stream_state(session.id)
        return TerminalSessionResponse(
            id=session.id,
            project_id=session.project_id,
            name=session.name,
            shell_type=session.shell_type,
            working_directory=session.working_directory,
            created_by=session.created_by,
            status=session.status,
            created_at=session.created_at.isoformat() if session.created_at else "",
            closed_at=session.closed_at.isoformat() if session.closed_at else None,
            running_command=stream_state.running_command if stream_state else None,
            active_pid=stream_state.active_pid if stream_state else None,
        )

    async def update_session(
        self, session_id: str, payload: TerminalSessionUpdate
    ) -> TerminalSessionResponse | None:
        session = await self.db.get(TerminalSession, session_id)
        if not session:
            return None
        if payload.name:
            session.name = payload.name
        if payload.status:
            session.status = payload.status
            if payload.status == "closed":
                session.closed_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(session)
        return await self.get_session(session_id)

    async def close_session(self, session_id: str) -> bool:
        session = await self.db.get(TerminalSession, session_id)
        if not session:
            return False

        # Terminate any running process in this session
        procs = self.process_mgr.list_processes(session_id=session_id, active_only=True)
        for p in procs:
            await self.process_mgr.stop_process(p.pid)

        session.status = "closed"
        session.closed_at = datetime.now(UTC)
        await self.db.commit()
        self.session_mgr.remove_session(session_id)
        return True

    async def execute_in_session(
        self,
        session_id: str,
        req: TerminalExecuteRequest,
    ) -> TerminalCommandResponse:
        """
        Validate, launch, stream, and record a command execution.
        """
        session = await self.db.get(TerminalSession, session_id)
        if not session:
            raise ValueError(f"Terminal session {session_id} not found.")

        # 1. Policy Evaluation
        eval_result = CommandPolicyEngine.evaluate(req.command)
        if not eval_result.is_allowed:
            err_msg = f"[SECURITY BLOCKED] {eval_result.reason}\n"
            await self.session_mgr.broadcast_event(session_id, "error", err_msg)
            # Log security event
            await EventService.emit_event(
                self.db,
                project_id=session.project_id,
                event_type="terminal_command_blocked",
                message=f"Blocked dangerous command: {req.command}",
                severity="error",
                source=req.agent_id or "user",
                category="security_scan",
                trace_id=req.trace_id or get_current_trace_id() or generate_trace_id(),
                payload={"command": req.command, "reason": eval_result.reason},
            )
            raise PermissionError(eval_result.reason)

        # 2. Workspace boundary resolution
        try:
            cwd_path = TerminalSecurity.resolve_and_verify_cwd(
                session.project_id, req.working_directory
            )
        except ValueError as ve:
            await self.session_mgr.broadcast_event(session_id, "error", f"[PATH ERROR] {ve}\n")
            raise

        cwd_str = str(cwd_path)
        trace_id = req.trace_id or get_current_trace_id() or generate_trace_id()

        # 3. Create command entity in DB
        cmd_entity = TerminalCommand(
            session_id=session.id,
            project_id=session.project_id,
            agent_id=req.agent_id,
            task_id=req.task_id,
            run_id=req.run_id,
            trace_id=trace_id,
            command=req.command,
            working_directory=cwd_str,
            status="running",
            started_at=datetime.now(UTC),
        )
        self.db.add(cmd_entity)
        await self.db.commit()
        await self.db.refresh(cmd_entity)

        # 4. Stream setup
        stream_state = await self.session_mgr.get_or_create_stream_state(
            session_id=session.id,
            project_id=session.project_id,
            name=session.name,
            shell_type=session.shell_type,
            working_directory=cwd_str,
        )
        stream_state.running_command = req.command

        # Broadcast prompt header
        if req.agent_id:
            banner = f"\n\x1b[35m[{datetime.now(UTC).strftime('%H:%M:%S')}] [AGENT: {req.agent_id.upper()}]\x1b[0m\n> {req.command}\n"
        else:
            banner = f"\n\x1b[32mPS {cwd_str}>\x1b[0m {req.command}\n"
        await self.session_mgr.broadcast_event(session.id, "system", banner)

        # Log start in Central Logs
        await EventService.emit_event(
            self.db,
            project_id=session.project_id,
            event_type="terminal_command_started",
            message=f"Command started: {req.command[:80]}",
            severity="info",
            source=req.agent_id or "user",
            category="tool_execution",
            task_id=req.task_id,
            trace_id=trace_id,
            status="running",
            payload={
                "command": req.command,
                "cwd": cwd_str,
                "session_id": session.id,
                "command_id": cmd_entity.id,
            },
        )

        async def _output_callback(stream: str, text: str, seq: int) -> None:
            await self.session_mgr.broadcast_event(session.id, stream, text)

        # 5. Launch process via ProcessManager
        run_proc = await self.process_mgr.execute_command(
            command_str=req.command,
            cwd=cwd_str,
            session_id=session.id,
            project_id=session.project_id,
            shell_type=session.shell_type,
            agent_id=req.agent_id,
            timeout_seconds=req.timeout_seconds,
            output_callback=_output_callback,
        )

        # 6. Update command entity with completion results
        cmd_entity.process_id = run_proc.pid if run_proc.pid > 0 else None
        cmd_entity.exit_code = run_proc.exit_code
        cmd_entity.status = run_proc.status
        cmd_entity.duration_ms = run_proc.duration_ms
        cmd_entity.completed_at = datetime.now(UTC)

        stdout_full = "".join(run_proc.stdout_buffer)
        stderr_full = "".join(run_proc.stderr_buffer)
        cmd_entity.stdout_preview = stdout_full[:5000] if stdout_full else ""
        cmd_entity.stderr_preview = stderr_full[:5000] if stderr_full else ""

        stream_state.running_command = None
        stream_state.active_pid = None

        await self.db.commit()
        await self.db.refresh(cmd_entity)

        # 7. Broadcast completion status
        status_color = "\x1b[32m" if run_proc.exit_code == 0 else "\x1b[31m"
        dur_s = (run_proc.duration_ms or 0) / 1000.0
        summary_line = (
            f"{status_color}[Process exited with code {run_proc.exit_code} "
            f"({run_proc.status.upper()}) in {dur_s:.2f}s]\x1b[0m\n"
        )
        await self.session_mgr.broadcast_event(session.id, "status", summary_line)

        # 8. Log completion to Central Logs
        severity = "success" if run_proc.exit_code == 0 else "error"
        await EventService.emit_event(
            self.db,
            project_id=session.project_id,
            event_type="terminal_command_completed",
            message=f"Command {run_proc.status}: {req.command[:60]} (exit {run_proc.exit_code})",
            severity=severity,
            source=req.agent_id or "user",
            category="tool_execution",
            task_id=req.task_id,
            trace_id=trace_id,
            duration_ms=run_proc.duration_ms,
            status=run_proc.status,
            payload={
                "command": req.command,
                "exit_code": run_proc.exit_code,
                "duration_ms": run_proc.duration_ms,
                "command_id": cmd_entity.id,
                "session_id": session.id,
            },
        )

        return TerminalCommandResponse(
            id=cmd_entity.id,
            session_id=cmd_entity.session_id,
            project_id=cmd_entity.project_id,
            agent_id=cmd_entity.agent_id,
            task_id=cmd_entity.task_id,
            run_id=cmd_entity.run_id,
            trace_id=cmd_entity.trace_id,
            command=cmd_entity.command,
            working_directory=cmd_entity.working_directory,
            process_id=cmd_entity.process_id,
            started_at=cmd_entity.started_at.isoformat() if cmd_entity.started_at else "",
            completed_at=cmd_entity.completed_at.isoformat() if cmd_entity.completed_at else None,
            duration_ms=cmd_entity.duration_ms,
            exit_code=cmd_entity.exit_code,
            status=cmd_entity.status,
            stdout_preview=cmd_entity.stdout_preview,
            stderr_preview=cmd_entity.stderr_preview,
        )

    async def interrupt_session(self, session_id: str) -> bool:
        """Interrupt any running command in the session."""
        procs = self.process_mgr.list_processes(session_id=session_id, active_only=True)
        if not procs:
            return False
        for p in procs:
            await self.process_mgr.stop_process(p.pid)
        await self.session_mgr.broadcast_event(
            session_id, "system", "\n\x1b[33m[SIGINT received - process interrupted]\x1b[0m\n"
        )
        return True

    async def get_command_history(
        self,
        session_id: str | None = None,
        project_id: str | None = None,
        agent_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TerminalCommandResponse]:
        """Fetch command history with multi-filtering."""
        stmt = select(TerminalCommand)
        if session_id:
            stmt = stmt.where(TerminalCommand.session_id == session_id)
        if project_id and project_id != "all":
            stmt = stmt.where(TerminalCommand.project_id == project_id)
        if agent_id and agent_id != "all":
            stmt = stmt.where(TerminalCommand.agent_id == agent_id)
        if status and status != "all":
            stmt = stmt.where(TerminalCommand.status == status)
        if search:
            stmt = stmt.where(TerminalCommand.command.ilike(f"%{search}%"))

        stmt = stmt.order_by(desc(TerminalCommand.started_at)).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        commands = res.scalars().all()

        return [
            TerminalCommandResponse(
                id=c.id,
                session_id=c.session_id,
                project_id=c.project_id,
                agent_id=c.agent_id,
                task_id=c.task_id,
                run_id=c.run_id,
                trace_id=c.trace_id,
                command=c.command,
                working_directory=c.working_directory,
                process_id=c.process_id,
                started_at=c.started_at.isoformat() if c.started_at else "",
                completed_at=c.completed_at.isoformat() if c.completed_at else None,
                duration_ms=c.duration_ms,
                exit_code=c.exit_code,
                status=c.status,
                stdout_preview=c.stdout_preview,
                stderr_preview=c.stderr_preview,
            )
            for c in commands
        ]

    async def get_command_details(self, command_id: str) -> TerminalCommandResponse | None:
        cmd = await self.db.get(TerminalCommand, command_id)
        if not cmd:
            return None
        return TerminalCommandResponse(
            id=cmd.id,
            session_id=cmd.session_id,
            project_id=cmd.project_id,
            agent_id=cmd.agent_id,
            task_id=cmd.task_id,
            run_id=cmd.run_id,
            trace_id=cmd.trace_id,
            command=cmd.command,
            working_directory=cmd.working_directory,
            process_id=cmd.process_id,
            started_at=cmd.started_at.isoformat() if cmd.started_at else "",
            completed_at=cmd.completed_at.isoformat() if cmd.completed_at else None,
            duration_ms=cmd.duration_ms,
            exit_code=cmd.exit_code,
            status=cmd.status,
            stdout_preview=cmd.stdout_preview,
            stderr_preview=cmd.stderr_preview,
        )

    def list_active_processes(self, project_id: str | None = None) -> list[TerminalProcessInfo]:
        """List active processes across all sessions."""
        procs = self.process_mgr.list_processes(project_id=project_id, active_only=True)
        results = []
        now = datetime.now(UTC)
        for p in procs:
            dur = (now - p.started_at).total_seconds()
            results.append(
                TerminalProcessInfo(
                    process_id=p.pid,
                    session_id=p.session_id,
                    project_id=p.project_id,
                    command=p.command_str,
                    started_by=p.agent_id or "user",
                    agent_name=p.agent_id,
                    started_at=p.started_at.isoformat(),
                    duration_seconds=round(dur, 2),
                    status=p.status,
                )
            )
        return results

    async def export_session_output(
        self, session_id: str, format_type: str = "txt"
    ) -> tuple[str, str]:
        """Export session buffer as text, markdown, or JSON."""
        state = self.session_mgr.get_stream_state(session_id)
        if not state or not state.buffer:
            # Fall back to commands in database
            cmds = await self.get_command_history(session_id=session_id, limit=100)
            if format_type == "json":
                import json

                return json.dumps([c.model_dump() for c in cmds], indent=2), "application/json"
            lines = [f"=== Session {session_id} History ==="]
            for c in cmds:
                lines.append(f"[{c.started_at}] ({c.status.upper()}) > {c.command}")
                if c.stdout_preview:
                    lines.append(c.stdout_preview)
            return "\n".join(lines), "text/plain"

        if format_type == "json":
            import json

            items = [item.model_dump() for item in state.buffer]
            return json.dumps(items, indent=2), "application/json"

        if format_type == "markdown":
            md = [f"# Terminal Session Export: {state.name}\n\n```terminal"]
            for item in state.buffer:
                md.append(item.data.rstrip("\n"))
            md.append("```\n")
            return "\n".join(md), "text/markdown"

        # Plain text
        plain = "".join(item.data for item in state.buffer)
        return plain, "text/plain"
