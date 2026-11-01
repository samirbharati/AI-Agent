"""
Project CRUD endpoints.

  GET    /api/v1/projects                                  — list projects (paginated)
  POST   /api/v1/projects                                  — create project
  GET    /api/v1/projects/{project_id}                     — get project detail
  PATCH  /api/v1/projects/{project_id}                     — update project
  DELETE /api/v1/projects/{project_id}                     — cancel / soft-delete
  GET    /api/v1/projects/{project_id}/tasks               — list tasks
  POST   /api/v1/projects/{project_id}/tasks               — create task
  POST   /api/v1/projects/{project_id}/requirements/approve — approve requirements
  POST   /api/v1/projects/{project_id}/architecture/approve — approve architecture
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.db_models import (
    ApprovalRequest,
    Project,
    Task,
    TaskDependency,
    WorkflowEvent,
)
from app.schemas.common import PaginatedResponse, PaginationParams, StatusResponse
from app.schemas.project import (
    ApproveRequest,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectSummaryResponse,
    ProjectUpdateRequest,
)
from app.schemas.task import TaskCreateRequest, TaskResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["projects"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _project_or_404(project: Project | None, project_id: str) -> Project:
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "project_not_found", "message": f"Project '{project_id}' not found."},
        )
    return project


async def _log_event(
    db: AsyncSession,
    *,
    project_id: str,
    event_type: str,
    message: str,
    severity: str = "info",
) -> None:
    """Append an immutable workflow event."""
    event = WorkflowEvent(
        project_id=project_id,
        event_type=event_type,
        message=message,
        severity=severity,
    )
    db.add(event)


# ---------------------------------------------------------------------------
# Projects — CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/projects",
    response_model=PaginatedResponse[ProjectSummaryResponse],
    summary="List all projects",
)
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
) -> PaginatedResponse[ProjectSummaryResponse]:
    pagination = PaginationParams(page=page, page_size=page_size)

    query = select(Project)
    if status_filter:
        query = query.where(Project.status == status_filter)
    query = query.order_by(Project.created_at.desc())

    count_query = select(func.count()).select_from(Project)
    if status_filter:
        count_query = count_query.where(Project.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.offset(pagination.offset).limit(pagination.limit))
    projects = result.scalars().all()

    items = [ProjectSummaryResponse.model_validate(p) for p in projects]
    return PaginatedResponse.create(items=items, total=total, pagination=pagination)


@router.post(
    "/projects",
    response_model=ProjectDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    body: ProjectCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetailResponse:
    project = Project(
        name=body.name,
        description=body.description,
        status="pending",
        preferred_language=body.preferred_language,
        preferred_framework=body.preferred_framework,
        preferred_database=body.preferred_database,
        max_repair_attempts=body.max_repair_attempts,
        settings=body.settings,
    )
    db.add(project)
    await db.flush()  # populate project.id before logging

    await _log_event(
        db,
        project_id=project.id,
        event_type="project_created",
        message=f"Project '{project.name}' created.",
    )

    logger.info("Project created: %s (%s)", project.name, project.id)
    return ProjectDetailResponse.model_validate(project)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get project details",
)
async def get_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetailResponse:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)
    return ProjectDetailResponse.model_validate(project)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Update project fields",
)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectDetailResponse:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)

    update_data = body.model_dump(exclude_none=True)
    for field_name, value in update_data.items():
        setattr(project, field_name, value)
    project.updated_at = datetime.now(UTC)

    if "status" in update_data:
        await _log_event(
            db,
            project_id=project.id,
            event_type="status_changed",
            message=f"Project status updated to '{update_data['status']}'.",
        )

    await db.flush()  # make changes visible to subsequent queries in the same session
    return ProjectDetailResponse.model_validate(project)


@router.delete(
    "/projects/{project_id}",
    response_model=StatusResponse,
    summary="Cancel a project",
    description="Marks the project as cancelled. Does not delete data.",
)
async def cancel_project(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusResponse:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)

    if project.status in ("completed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "invalid_state_transition",
                "message": f"Project is already '{project.status}' and cannot be cancelled.",
            },
        )

    project.status = "cancelled"
    project.updated_at = datetime.now(UTC)

    await _log_event(
        db,
        project_id=project.id,
        event_type="project_cancelled",
        message="Project cancelled by user.",
        severity="warning",
    )

    await db.flush()  # make status change visible to subsequent queries
    return StatusResponse(status="ok", message=f"Project '{project_id}' cancelled.")


# ---------------------------------------------------------------------------
# Requirements approval gate
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/requirements/approve",
    response_model=StatusResponse,
    summary="Approve or reject generated requirements",
    description=(
        "Human approval gate. When approved, the workflow proceeds to architecture design. "
        "When rejected, the requirements agent is queued for revision."
    ),
)
async def approve_requirements(
    project_id: str,
    body: ApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusResponse:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)

    if project.status not in ("pending", "requirements_review"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "invalid_state",
                "message": (
                    f"Requirements can only be approved when project status is "
                    f"'pending' or 'requirements_review'. Current: '{project.status}'."
                ),
            },
        )

    approval = ApprovalRequest(
        project_id=project.id,
        approval_type="requirements",
        title="Requirements Review",
        description="Human review of AI-generated requirements.",
        status="approved" if body.approved else "rejected",
        reviewer_notes=body.reviewer_notes,
        resolved_at=datetime.now(UTC),
    )
    db.add(approval)

    if body.approved:
        project.status = "requirements_approved"
        event_type = "requirements_approved"
        msg = "Requirements approved. Proceeding to architecture design."
    else:
        project.status = "requirements_revision"
        event_type = "requirements_rejected"
        msg = f"Requirements rejected. Notes: {body.reviewer_notes or '(none)'}"

    project.updated_at = datetime.now(UTC)
    await _log_event(
        db,
        project_id=project.id,
        event_type=event_type,
        message=msg,
        severity="info" if body.approved else "warning",
    )

    return StatusResponse(status="ok", message=msg)


# ---------------------------------------------------------------------------
# Architecture approval gate
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/architecture/approve",
    response_model=StatusResponse,
    summary="Approve or reject the generated architecture",
)
async def approve_architecture(
    project_id: str,
    body: ApproveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StatusResponse:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)

    if project.status not in ("architecture_review",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "invalid_state",
                "message": (
                    f"Architecture can only be approved when project status is "
                    f"'architecture_review'. Current: '{project.status}'."
                ),
            },
        )

    approval = ApprovalRequest(
        project_id=project.id,
        approval_type="architecture",
        title="Architecture Review",
        description="Human review of AI-generated system architecture.",
        status="approved" if body.approved else "rejected",
        reviewer_notes=body.reviewer_notes,
        resolved_at=datetime.now(UTC),
    )
    db.add(approval)

    if body.approved:
        project.status = "architecture_approved"
        event_type = "architecture_approved"
        msg = "Architecture approved. Task planning will begin."
    else:
        project.status = "architecture_revision"
        event_type = "architecture_rejected"
        msg = f"Architecture rejected. Notes: {body.reviewer_notes or '(none)'}"

    project.updated_at = datetime.now(UTC)
    await _log_event(
        db,
        project_id=project.id,
        event_type=event_type,
        message=msg,
        severity="info" if body.approved else "warning",
    )

    return StatusResponse(status="ok", message=msg)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/tasks",
    response_model=PaginatedResponse[TaskResponse],
    summary="List tasks for a project",
)
async def list_tasks(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse[TaskResponse]:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)

    pagination = PaginationParams(page=page, page_size=page_size)

    count_result = await db.execute(
        select(func.count()).select_from(Task).where(Task.project_id == project_id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .order_by(Task.order_index, Task.created_at)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    tasks = result.scalars().all()

    items = [TaskResponse.model_validate(t) for t in tasks]
    return PaginatedResponse.create(items=items, total=total, pagination=pagination)


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task for a project",
)
async def create_task(
    project_id: str,
    body: TaskCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    project = await db.get(Project, project_id)
    _project_or_404(project, project_id)

    # Validate dependency IDs exist in this project
    if body.dependency_ids:
        dep_result = await db.execute(
            select(Task.id).where(Task.project_id == project_id, Task.id.in_(body.dependency_ids))
        )
        found_ids = {row[0] for row in dep_result}
        missing = set(body.dependency_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "invalid_dependency_ids",
                    "message": f"Task dependency IDs not found in project: {sorted(missing)}",
                },
            )

    task = Task(
        project_id=project_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        assigned_agent=body.assigned_agent,
        acceptance_criteria=body.acceptance_criteria,
        complexity_estimate=body.complexity_estimate,
        requires_human_approval=body.requires_human_approval,
        order_index=body.order_index,
        status="pending",
    )
    db.add(task)
    await db.flush()  # populate task.id

    for dep_id in body.dependency_ids:
        db.add(TaskDependency(task_id=task.id, depends_on_task_id=dep_id))

    await _log_event(
        db,
        project_id=project_id,
        event_type="task_created",
        message=f"Task '{task.title}' created.",
    )

    return TaskResponse.model_validate(task)
