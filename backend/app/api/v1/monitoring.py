"""
Advanced Monitoring & Observability API Router for AgentForge.

Endpoints:
  GET /api/v1/monitoring/events        — paginated, filtered, search-enabled event log
  GET /api/v1/monitoring/stats         — SOC dashboard summary statistics
  GET /api/v1/monitoring/agents        — real-time agent activity & operational states
  GET /api/v1/monitoring/llm-requests  — local LLM inference telemetry & timing
  GET /api/v1/monitoring/tools         — tool & subprocess execution logs
  GET /api/v1/monitoring/incidents     — defects, bugs, and incident intelligence
  GET /api/v1/monitoring/security-events — security scan findings & audit events
  GET /api/v1/monitoring/export        — export filtered logs (JSON, CSV, Markdown, TXT)
  GET /api/v1/monitoring/stream        — live Server-Sent Events stream
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.database.base import get_session_factory
from app.logging.event_service import EventService
from app.models.db_models import WorkflowEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/events", summary="Get paginated, filtered event logs")
async def get_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    time_range: str | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return await EventService.get_filtered_events(
        db,
        project_id=project_id,
        severity=severity,
        source=source,
        category=category,
        status=status,
        search=search,
        time_range=time_range,
        trace_id=trace_id,
        task_id=task_id,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", summary="Get observability summary card statistics")
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return await EventService.get_monitoring_stats(db, project_id=project_id)


@router.get("/agents", summary="Get real-time agent activity & operational states")
async def get_agents(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    return await EventService.get_agent_monitoring(db, project_id=project_id)


@router.get("/llm-requests", summary="Get LLM inference requests and latency telemetry")
async def get_llm_requests(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
) -> dict[str, Any]:
    return await EventService.get_llm_intelligence(db, project_id=project_id)


@router.get("/tools", summary="Get tool & subprocess execution logs")
async def get_tools(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    return await EventService.get_tool_executions(db, project_id=project_id)


@router.get("/incidents", summary="Get bug and incident intelligence")
async def get_incidents(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    return await EventService.get_incident_intelligence(db, project_id=project_id)


@router.get("/security-events", summary="Get security scan findings and audit events")
async def get_security_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: str | None = Query(default=None),
) -> list[dict[str, Any]]:
    return await EventService.get_security_events(db, project_id=project_id)


@router.get("/export", summary="Export filtered logs in various formats")
async def export_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query(default="json", pattern="^(json|csv|markdown|txt)$"),
    project_id: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=10, le=5000),
) -> Response:
    content, media_type = await EventService.export_logs(
        db,
        format_type=format,
        project_id=project_id,
        severity=severity,
        source=source,
        category=category,
        search=search,
        limit=limit,
    )
    filename = f"agentforge_logs_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.{format if format != 'markdown' else 'md'}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stream", summary="Live SSE stream for real-time monitoring events")
async def stream_monitoring_events(
    project_id: str | None = Query(default=None),
    last_event_id: str | None = Query(default=None),
    max_iterations: int | None = Query(default=None),
) -> StreamingResponse:
    """
    Continuous real-time SSE stream for the monitoring command center.
    Emits newly created WorkflowEvents with cursor-based deduplication and heartbeats.
    """

    async def event_generator():
        seen_ids: set[str] = set()
        after_dt: datetime | None = None
        iteration = 0

        if last_event_id:
            factory = get_session_factory()
            async with factory() as seed_session:
                seed_res = await seed_session.execute(
                    select(WorkflowEvent.created_at).where(WorkflowEvent.id == last_event_id)
                )
                row = seed_res.scalar_one_or_none()
                if row is not None:
                    after_dt = row
                    seen_ids.add(last_event_id)

        factory = get_session_factory()

        while True:
            iteration += 1
            try:
                async with factory() as poll_session:
                    q = (
                        select(WorkflowEvent)
                        .order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc())
                        .limit(30)
                    )

                    if project_id and project_id != "all":
                        q = q.where(WorkflowEvent.project_id == project_id)

                    if after_dt is not None:
                        q = q.where(WorkflowEvent.created_at >= after_dt)

                    res = await poll_session.execute(q)
                    events = res.scalars().all()

                    new_events = [e for e in events if e.id not in seen_ids]

                    for event in new_events:
                        seen_ids.add(event.id)
                        after_dt = event.created_at
                        data = json.dumps(
                            {
                                "id": event.id,
                                "project_id": event.project_id,
                                "event_type": event.event_type,
                                "message": event.message,
                                "severity": event.severity,
                                "source": event.source or "system",
                                "category": event.category or "system",
                                "status": event.status or event.severity,
                                "task_id": event.task_id,
                                "trace_id": event.trace_id,
                                "duration_ms": event.duration_ms,
                                "payload": event.payload or {},
                                "timestamp": event.created_at.isoformat(),
                            }
                        )
                        yield f"id: {event.id}\ndata: {data}\n\n"

                    if not new_events:
                        heartbeat = json.dumps(
                            {
                                "event_type": "heartbeat",
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        )
                        yield f"data: {heartbeat}\n\n"

            except Exception as exc:  # noqa: BLE001
                logger.debug("Error in monitoring stream loop: %s", exc)

            if max_iterations and iteration >= max_iterations:
                break

            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
