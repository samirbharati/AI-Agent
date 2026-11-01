"""
Central Event and Observability Service for AgentForge.

Provides unified logging, filtering, aggregation, and export for:
- Agent lifecycle and state transitions
- LLM inference telemetry
- Tool and subprocess executions
- Automated test runs and QA verification
- Security scans and policy violations
- Bug tracking and incident resolution
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.database.base import get_session_factory
from app.logging.correlation import get_current_trace_id
from app.logging.redaction import redact_metadata, redact_string
from app.models.db_models import (
    AgentRun,
    Bug,
    ModelUsageStat,
    Project,
    SecurityFinding,
    WorkflowEvent,
)
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EventService:
    """
    Core logging and observability service for AgentForge.
    """

    @staticmethod
    async def emit_event(
        db: AsyncSession | None = None,
        *,
        project_id: str,
        message: str,
        severity: str = "info",
        event_type: str = "log_entry",
        category: str = "system",
        source: str = "system",
        status: str = "info",
        task_id: str | None = None,
        agent_run_id: str | None = None,
        trace_id: str | None = None,
        parent_event_id: str | None = None,
        duration_ms: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        """
        Record an immutable, redacted audit/monitoring event.
        If a DB session is not provided, one is created from the session factory.
        """
        safe_message = redact_string(message)
        safe_payload = redact_metadata(payload or {})
        resolved_trace_id = trace_id or get_current_trace_id()

        event = WorkflowEvent(
            project_id=project_id,
            message=safe_message,
            severity=severity.lower(),
            event_type=event_type,
            category=category,
            source=source,
            status=status,
            task_id=task_id,
            agent_run_id=agent_run_id,
            trace_id=resolved_trace_id,
            parent_event_id=parent_event_id,
            duration_ms=duration_ms,
            payload=safe_payload,
            created_at=datetime.now(UTC),
        )

        if db is not None:
            db.add(event)
            await db.flush()
            return event

        factory = get_session_factory()
        async with factory() as session:
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    @staticmethod
    async def get_filtered_events(
        db: AsyncSession,
        *,
        project_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        category: str | None = None,
        status: str | None = None,
        search: str | None = None,
        time_range: str | None = None,
        trace_id: str | None = None,
        task_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """
        Query and paginate events based on multi-dimensional filter criteria.
        """
        stmt = select(WorkflowEvent)

        # Filters
        if project_id and project_id != "all":
            stmt = stmt.where(WorkflowEvent.project_id == project_id)

        if severity and severity != "all":
            stmt = stmt.where(WorkflowEvent.severity == severity.lower())

        if source and source != "all":
            stmt = stmt.where(WorkflowEvent.source == source)

        if category and category != "all":
            stmt = stmt.where(WorkflowEvent.category == category)

        if status and status != "all":
            stmt = stmt.where(WorkflowEvent.status == status.lower())

        if trace_id:
            stmt = stmt.where(WorkflowEvent.trace_id == trace_id)

        if task_id:
            stmt = stmt.where(WorkflowEvent.task_id == task_id)

        # Time range filter
        if time_range and time_range != "all":
            now = datetime.now(UTC)
            ranges = {
                "5m": timedelta(minutes=5),
                "15m": timedelta(minutes=15),
                "1h": timedelta(hours=1),
                "24h": timedelta(hours=24),
                "7d": timedelta(days=7),
            }
            if time_range in ranges:
                cutoff = now - ranges[time_range]
                stmt = stmt.where(WorkflowEvent.created_at >= cutoff)

        # Full-text search across message, task_id, and trace_id
        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    WorkflowEvent.message.ilike(term),
                    WorkflowEvent.task_id.ilike(term),
                    WorkflowEvent.trace_id.ilike(term),
                    WorkflowEvent.event_type.ilike(term),
                    WorkflowEvent.source.ilike(term),
                )
            )

        # Count total matching records
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        # Ordering & Pagination
        offset = (page - 1) * page_size
        stmt = stmt.order_by(desc(WorkflowEvent.created_at), desc(WorkflowEvent.id))
        stmt = stmt.offset(offset).limit(page_size)

        result = await db.execute(stmt)
        events = result.scalars().all()

        total_pages = max(1, (total + page_size - 1) // page_size)

        return {
            "items": [
                {
                    "id": e.id,
                    "project_id": e.project_id,
                    "event_type": e.event_type,
                    "message": e.message,
                    "severity": e.severity,
                    "source": e.source or "system",
                    "category": e.category or "system",
                    "status": e.status or e.severity,
                    "task_id": e.task_id,
                    "agent_run_id": e.agent_run_id,
                    "trace_id": e.trace_id,
                    "parent_event_id": e.parent_event_id,
                    "duration_ms": e.duration_ms,
                    "payload": e.payload or {},
                    "timestamp": e.created_at.isoformat(),
                }
                for e in events
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def get_monitoring_stats(
        db: AsyncSession, project_id: str | None = None
    ) -> dict[str, Any]:
        """
        Aggregate high-level observability statistics for dashboard summary cards.
        """
        base = select(WorkflowEvent)
        if project_id and project_id != "all":
            base = base.where(WorkflowEvent.project_id == project_id)

        # Total events
        total_q = select(func.count()).select_from(base.subquery())
        total_events = (await db.execute(total_q)).scalar_one()

        # Severities
        def _sev_query(sev: str):
            q = select(func.count()).select_from(WorkflowEvent)
            if project_id and project_id != "all":
                q = q.where(WorkflowEvent.project_id == project_id)
            return q.where(WorkflowEvent.severity == sev)

        success_count = (await db.execute(_sev_query("success"))).scalar_one()
        warning_count = (await db.execute(_sev_query("warning"))).scalar_one()
        error_count = (await db.execute(_sev_query("error"))).scalar_one()
        critical_count = (await db.execute(_sev_query("critical"))).scalar_one()

        # Active agents
        active_agents_q = (
            select(func.count())
            .select_from(AgentRun)
            .where(AgentRun.status.in_(("running", "pending")))
        )
        if project_id and project_id != "all":
            active_agents_q = active_agents_q.where(AgentRun.project_id == project_id)
        active_agents = (await db.execute(active_agents_q)).scalar_one()

        # Active workflows
        active_wf_q = (
            select(func.count())
            .select_from(Project)
            .where(Project.status.in_(("in_progress", "planning", "implementing", "active")))
        )
        active_workflows = (await db.execute(active_wf_q)).scalar_one()

        return {
            "total_events": total_events,
            "successful_operations": success_count,
            "warnings": warning_count,
            "errors": error_count,
            "critical_events": critical_count,
            "active_agents": active_agents,
            "active_workflows": active_workflows,
        }

    @staticmethod
    async def get_agent_monitoring(
        db: AsyncSession, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Compute real-time operational status, task counts, and latencies for all agents.
        """
        agent_definitions = [
            {"id": "requirements-analyst", "name": "Requirements Analyst", "role": "Requirements"},
            {"id": "system-architect", "name": "System Architect", "role": "Architecture"},
            {"id": "task-planner", "name": "Task Planner", "role": "Planning"},
            {"id": "software-developer", "name": "Software Developer", "role": "Development"},
            {"id": "qa-engineer", "name": "QA Engineer", "role": "Verification"},
            {"id": "security-engineer", "name": "Security Engineer", "role": "Security"},
            {"id": "code-reviewer", "name": "Code Reviewer", "role": "Review"},
        ]

        results = []
        for agent in agent_definitions:
            aid = agent["id"]
            # Query runs
            q = select(AgentRun).where(AgentRun.agent_definition_id == aid)
            if project_id and project_id != "all":
                q = q.where(AgentRun.project_id == project_id)
            q = q.order_by(desc(AgentRun.started_at)).limit(10)

            runs_res = await db.execute(q)
            runs = runs_res.scalars().all()

            completed = sum(1 for r in runs if r.status == "success")
            failed = sum(1 for r in runs if r.status in ("failure", "error"))
            latest = runs[0] if runs else None

            # Current state
            if latest and latest.status == "running":
                status = "RUNNING"
            elif latest and latest.status == "pending":
                status = "INITIALIZING"
            elif latest and latest.status in ("failure", "error"):
                status = "FAILED"
            elif latest and latest.status == "success":
                status = "COMPLETED"
            else:
                status = "IDLE"

            results.append(
                {
                    "agent_id": aid,
                    "agent_name": agent["name"],
                    "role": agent["role"],
                    "status": status,
                    "current_task": latest.task_id if latest else None,
                    "completed_tasks": completed,
                    "failed_tasks": failed,
                    "total_runs": len(runs),
                    "model_used": latest.model_used if latest else "qwen2.5-coder:7b",
                    "last_active": latest.started_at.isoformat()
                    if latest and latest.started_at
                    else None,
                    "duration_seconds": latest.duration_seconds if latest else None,
                    "latest_summary": latest.output_summary if latest else None,
                }
            )

        return results

    @staticmethod
    async def get_llm_intelligence(
        db: AsyncSession, project_id: str | None = None
    ) -> dict[str, Any]:
        """
        Aggregate LLM request latency, token consumption, and inference records.
        """
        q = select(ModelUsageStat)
        if project_id and project_id != "all":
            q = q.where(ModelUsageStat.project_id == project_id)
        q = q.order_by(desc(ModelUsageStat.created_at)).limit(50)

        res = await db.execute(q)
        records = res.scalars().all()

        total = len(records)
        successful = sum(1 for r in records if r.success)
        failed = sum(1 for r in records if not r.success)
        durations = [r.duration_seconds for r in records if r.duration_seconds is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        slowest = max(durations) if durations else 0.0

        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "average_response_time": round(avg_duration, 2),
            "slowest_request_time": round(slowest, 2),
            "records": [
                {
                    "id": r.id,
                    "model_name": r.model_name,
                    "agent_role": r.agent_role or "agent",
                    "duration_seconds": r.duration_seconds,
                    "token_count_in": r.token_count_in,
                    "token_count_out": r.token_count_out,
                    "success": r.success,
                    "error_type": r.error_type,
                    "timestamp": r.created_at.isoformat(),
                }
                for r in records
            ],
        }

    @staticmethod
    async def get_tool_executions(
        db: AsyncSession, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List recorded tool executions from workflow events.
        """
        q = select(WorkflowEvent).where(
            WorkflowEvent.category.in_(
                ("tool_execution", "git_operation", "file_operation", "test_execution")
            )
        )
        if project_id and project_id != "all":
            q = q.where(WorkflowEvent.project_id == project_id)
        q = q.order_by(desc(WorkflowEvent.created_at)).limit(50)

        res = await db.execute(q)
        events = res.scalars().all()

        return [
            {
                "id": e.id,
                "project_id": e.project_id,
                "tool_name": e.payload.get("tool_name", e.event_type)
                if e.payload
                else e.event_type,
                "calling_agent": e.source or "system",
                "task_id": e.task_id,
                "duration_ms": e.duration_ms,
                "status": e.status or "completed",
                "command": e.payload.get("command") if e.payload else None,
                "exit_code": e.payload.get("exit_code") if e.payload else None,
                "message": e.message,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ]

    @staticmethod
    async def get_incident_intelligence(
        db: AsyncSession, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Aggregate incidents and defects from Bug table and critical events.
        """
        q = select(Bug)
        if project_id and project_id != "all":
            q = q.where(Bug.project_id == project_id)
        q = q.order_by(desc(Bug.created_at)).limit(50)

        res = await db.execute(q)
        bugs = res.scalars().all()

        return [
            {
                "id": b.id,
                "project_id": b.project_id,
                "task_id": b.task_id,
                "title": b.title,
                "description": b.description,
                "severity": b.severity,
                "status": b.status,
                "affected_files": b.affected_files or [],
                "created_at": b.created_at.isoformat(),
            }
            for b in bugs
        ]

    @staticmethod
    async def get_security_events(
        db: AsyncSession, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve security findings and audit logs.
        """
        q = select(SecurityFinding)
        if project_id and project_id != "all":
            q = q.where(SecurityFinding.project_id == project_id)
        q = q.order_by(desc(SecurityFinding.created_at)).limit(50)

        res = await db.execute(q)
        findings = res.scalars().all()

        return [
            {
                "id": f.id,
                "project_id": f.project_id,
                "scanner": f.scanner,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "affected_file": f.affected_file,
                "line_number": f.line_number,
                "evidence": redact_string(f.evidence or ""),
                "remediation": f.remediation,
                "created_at": f.created_at.isoformat(),
            }
            for f in findings
        ]

    @staticmethod
    async def export_logs(
        db: AsyncSession,
        *,
        format_type: str = "json",
        project_id: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        category: str | None = None,
        search: str | None = None,
        limit: int = 1000,
    ) -> tuple[str, str]:
        """
        Export filtered, redacted logs in JSON, CSV, Markdown, or TXT format.
        Returns: (data_string, media_type)
        """
        data = await EventService.get_filtered_events(
            db,
            project_id=project_id,
            severity=severity,
            source=source,
            category=category,
            search=search,
            page=1,
            page_size=limit,
        )
        events = data["items"]

        if format_type == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "timestamp",
                    "severity",
                    "source",
                    "category",
                    "status",
                    "message",
                    "task_id",
                    "trace_id",
                    "project_id",
                ],
                extrasaction="ignore",
            )
            writer.writeheader()
            for e in events:
                writer.writerow(e)
            return output.getvalue(), "text/csv"

        if format_type == "markdown":
            lines = [
                "# AgentForge System Intelligence & Log Report",
                f"Generated: {datetime.now(UTC).isoformat()} | Total Records: {len(events)}",
                "",
                "| Timestamp | Level | Source | Category | Message | Trace ID |",
                "|---|---|---|---|---|---|",
            ]
            for e in events:
                msg = e["message"].replace("|", "\\|")[:80]
                lines.append(
                    f"| {e['timestamp']} | {e['severity'].upper()} | {e['source']} | {e['category']} | {msg} | `{e['trace_id'] or '-'}` |"
                )
            return "\n".join(lines), "text/markdown"

        if format_type == "txt":
            lines = []
            for e in events:
                lines.append(
                    f"[{e['timestamp']}] [{e['severity'].upper()}] [{e['source'].upper()}] {e['message']} (Trace: {e['trace_id'] or 'none'})"
                )
            return "\n".join(lines), "text/plain"

        # Default JSON
        return json.dumps(events, indent=2), "application/json"
