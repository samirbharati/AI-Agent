"""
Workflow API endpoints.

  POST /api/v1/projects/{project_id}/workflow/start   — start the workflow
  POST /api/v1/projects/{project_id}/workflow/resume  — resume after approval
  GET  /api/v1/projects/{project_id}/workflow/events  — SSE live event stream
  GET  /api/v1/projects/{project_id}/workflow/status  — current status summary
  GET  /api/v1/projects/{project_id}/artifacts        — list project artifacts
  GET  /api/v1/projects/{project_id}/artifacts/{name} — get artifact content
  GET  /api/v1/projects/{project_id}/agent-runs       — list agent runs
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.database.base import get_session_factory
from app.models.db_models import AgentRun, Artifact, Project, Task, WorkflowEvent
from app.schemas.common import StatusResponse
from app.services.workflow import run_project_workflow

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workflow"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_project_or_404(db: AsyncSession, project_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "project_not_found", "message": f"Project '{project_id}' not found."},
        )
    return project


# ---------------------------------------------------------------------------
# Start workflow
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/workflow/start",
    response_model=StatusResponse,
    summary="Start the AI agent workflow for a project",
    description=(
        "Kicks off the requirements analysis phase. The workflow pauses at each "
        "human-in-the-loop gate (requirements review, architecture review). "
        "Call /workflow/resume after approving to continue."
    ),
)
async def start_workflow(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusResponse:
    project = await _get_project_or_404(db, project_id)

    if project.status not in ("pending",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "invalid_state",
                "message": (
                    f"Workflow can only be started from 'pending' status. "
                    f"Current: '{project.status}'."
                ),
            },
        )

    # Launch workflow in background — it will commit its own transactions
    background_tasks.add_task(_run_workflow_background, project_id, "requirements")
    logger.info("Workflow started for project %s", project_id)

    return StatusResponse(
        status="ok",
        message="Workflow started. Requirements analysis is running in the background.",
    )


# ---------------------------------------------------------------------------
# Resume workflow after a human-gate approval
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/workflow/resume",
    response_model=StatusResponse,
    summary="Resume workflow after a human approval gate",
    description=(
        "Call this after approving requirements (→ starts architecture) or "
        "after approving architecture (→ starts planning + implementation)."
    ),
)
async def resume_workflow(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusResponse:
    project = await _get_project_or_404(db, project_id)

    resumable_states = {
        "requirements_approved": "architecture",
        "architecture_approved": "planning",
    }

    if project.status not in resumable_states:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "not_resumable",
                "message": (
                    f"Workflow can only be resumed from "
                    f"{sorted(resumable_states.keys())}. Current: '{project.status}'."
                ),
            },
        )

    next_phase = resumable_states[project.status]
    background_tasks.add_task(_run_workflow_background, project_id, next_phase)
    logger.info("Workflow resumed for project %s (phase: %s)", project_id, next_phase)

    return StatusResponse(
        status="ok",
        message=f"Workflow resumed. Starting '{next_phase}' phase in the background.",
    )


async def _run_workflow_background(project_id: str, skip_to_phase: str | None = None) -> None:
    """Background task wrapper — creates its own DB session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            await run_project_workflow(project_id, session, skip_to_phase=skip_to_phase)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Background workflow error for project %s: %s", project_id, exc)


# ---------------------------------------------------------------------------
# Workflow status
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/workflow/status",
    summary="Get current workflow status and progress",
)
async def get_workflow_status(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    project = await _get_project_or_404(db, project_id)

    # Count tasks by status
    task_result = await db.execute(
        select(Task.status, Task.id).where(Task.project_id == project_id)
    )
    tasks = task_result.all()
    task_counts: dict[str, int] = {}
    for row in tasks:
        task_counts[row[0]] = task_counts.get(row[0], 0) + 1

    # Recent events
    events_result = await db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.project_id == project_id)
        .order_by(WorkflowEvent.created_at.desc())
        .limit(10)
    )
    recent_events = [
        {
            "event_type": e.event_type,
            "message": e.message,
            "severity": e.severity,
            "created_at": e.created_at.isoformat(),
        }
        for e in events_result.scalars().all()
    ]

    # Agent run stats
    runs_result = await db.execute(select(AgentRun).where(AgentRun.project_id == project_id))
    runs = runs_result.scalars().all()
    total_tokens = sum(r.total_tokens or 0 for r in runs)

    return {
        "project_id": project_id,
        "project_name": project.name,
        "status": project.status,
        "tasks": {
            "total": len(tasks),
            "by_status": task_counts,
        },
        "agent_runs": {
            "total": len(runs),
            "total_tokens_used": total_tokens,
        },
        "recent_events": recent_events,
        "updated_at": project.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# SSE live event stream
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/workflow/events",
    summary="Stream live workflow events via Server-Sent Events",
    description=(
        "Connect to this endpoint to receive real-time workflow progress. "
        "Events are sent as SSE (text/event-stream). "
        "The stream ends when the project reaches 'completed' or 'failed'. "
        "Pass the last received event id in the 'lastEventId' query parameter "
        "to resume without replaying old events."
    ),
)
async def stream_workflow_events(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    last_event_id: str = Query(default="", alias="lastEventId"),
) -> StreamingResponse:
    # Verify the project exists
    project = await _get_project_or_404(db, project_id)  # noqa: F841

    async def event_generator():
        # Track the created_at timestamp of the last delivered event so we
        # can page forward efficiently. UUID strings are not sortable as ints,
        # so we use created_at ordering + the seen set to deduplicate events
        # that share the same timestamp.
        seen_ids: set[str] = set()
        after_dt: datetime | None = None
        terminal_statuses = {"completed", "failed", "cancelled"}

        # If the caller passed a lastEventId, find that event's created_at
        # so we can start the cursor just past it.
        if last_event_id:
            factory = get_session_factory()
            async with factory() as seed_session:
                seed_result = await seed_session.execute(
                    select(WorkflowEvent.created_at).where(WorkflowEvent.id == last_event_id)
                )
                row = seed_result.scalar_one_or_none()
                if row is not None:
                    after_dt = row
                    seen_ids.add(last_event_id)

        # Use a fresh session for each poll cycle
        factory = get_session_factory()

        while True:
            async with factory() as poll_session:
                proj = await poll_session.get(Project, project_id)
                if proj is None:
                    break

                # Build query — filter by created_at if we have a cursor
                q = (
                    select(WorkflowEvent)
                    .where(WorkflowEvent.project_id == project_id)
                    .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
                    .limit(20)
                )
                if after_dt is not None:
                    q = q.where(WorkflowEvent.created_at >= after_dt)

                events_result = await poll_session.execute(q)
                events = events_result.scalars().all()

                # Filter out already-delivered events (handles same-second duplicates)
                new_events = [e for e in events if e.id not in seen_ids]

                for event in new_events:
                    seen_ids.add(event.id)
                    after_dt = event.created_at
                    data = json.dumps(
                        {
                            "id": event.id,
                            "event_type": event.event_type,
                            "message": event.message,
                            "severity": event.severity,
                            "project_status": proj.status,
                            "created_at": event.created_at.isoformat(),
                        }
                    )
                    yield f"id: {event.id}\ndata: {data}\n\n"

                # Send heartbeat if no new events
                if not new_events:
                    heartbeat = json.dumps(
                        {
                            "event_type": "heartbeat",
                            "project_status": proj.status,
                            "timestamp": datetime.now(UTC).isoformat(),
                        }
                    )
                    yield f"data: {heartbeat}\n\n"

                if proj.status in terminal_statuses:
                    final = json.dumps(
                        {
                            "event_type": "stream_end",
                            "project_status": proj.status,
                            "message": f"Project reached terminal status: {proj.status}",
                        }
                    )
                    yield f"data: {final}\n\n"
                    break

            await asyncio.sleep(2)  # Poll every 2 seconds

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/artifacts",
    summary="List all artifacts for a project",
)
async def list_artifacts(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_project_or_404(db, project_id)

    result = await db.execute(
        select(Artifact)
        .where(Artifact.project_id == project_id)
        .order_by(Artifact.created_at.desc())
    )
    artifacts = result.scalars().all()

    return {
        "project_id": project_id,
        "artifacts": [
            {
                "id": a.id,
                "artifact_type": a.artifact_type,
                "name": a.name,
                "created_at": a.created_at.isoformat(),
                "content_length": len(a.content or ""),
            }
            for a in artifacts
        ],
        "total": len(artifacts),
    }


@router.get(
    "/projects/{project_id}/artifacts/{artifact_name}",
    summary="Get the content of a specific artifact",
)
async def get_artifact(
    project_id: str,
    artifact_name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await _get_project_or_404(db, project_id)

    result = await db.execute(
        select(Artifact)
        .where(
            Artifact.project_id == project_id,
            Artifact.name == artifact_name,
        )
        .order_by(Artifact.created_at.desc())
        .limit(1)
    )
    artifact = result.scalar_one_or_none()

    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "artifact_not_found",
                "message": f"Artifact '{artifact_name}' not found for project '{project_id}'.",
            },
        )

    return {
        "id": artifact.id,
        "project_id": project_id,
        "artifact_type": artifact.artifact_type,
        "name": artifact.name,
        "content": artifact.content,
        "created_at": artifact.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Agent runs
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/agent-runs",
    summary="List all agent runs for a project",
)
async def list_agent_runs(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    await _get_project_or_404(db, project_id)

    offset = (page - 1) * page_size
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.project_id == project_id)
        .order_by(AgentRun.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    runs = result.scalars().all()

    return {
        "project_id": project_id,
        "page": page,
        "page_size": page_size,
        "runs": [
            {
                "id": r.id,
                "agent_definition_id": r.agent_definition_id,
                "status": r.status,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "duration_seconds": r.duration_seconds,
                "model_used": r.model_used,
                "error_message": r.error_message,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }
