"""Pydantic schemas for Task resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import AppBaseModel

TASK_STATUSES = {"pending", "ready", "in_progress", "completed", "failed", "blocked", "cancelled"}
TASK_PRIORITIES = {"critical", "high", "medium", "low"}
COMPLEXITY_ESTIMATES = {"xs", "s", "m", "l", "xl"}

VALID_AGENT_IDS = {
    "requirements-analyst",
    "system-architect",
    "task-planner",
    "software-developer",
    "qa-engineer",
    "security-engineer",
    "code-reviewer",
}


class TaskCreateRequest(AppBaseModel):
    """Request body for POST /api/v1/projects/{project_id}/tasks."""

    title: str = Field(..., min_length=1, max_length=256)
    description: str = Field(..., min_length=1, max_length=10_000)
    priority: str = Field(default="medium")
    assigned_agent: str | None = Field(default=None)
    acceptance_criteria: str | None = Field(default=None, max_length=5000)
    complexity_estimate: str | None = Field(default=None)
    requires_human_approval: bool = Field(default=False)
    dependency_ids: list[str] = Field(default_factory=list, max_length=20)
    order_index: int = Field(default=0, ge=0)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in TASK_PRIORITIES:
            raise ValueError(f"priority must be one of: {sorted(TASK_PRIORITIES)}")
        return v

    @field_validator("assigned_agent")
    @classmethod
    def validate_agent(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_AGENT_IDS:
            raise ValueError(f"assigned_agent must be one of: {sorted(VALID_AGENT_IDS)}")
        return v

    @field_validator("complexity_estimate")
    @classmethod
    def validate_complexity(cls, v: str | None) -> str | None:
        if v is not None and v not in COMPLEXITY_ESTIMATES:
            raise ValueError(f"complexity_estimate must be one of: {sorted(COMPLEXITY_ESTIMATES)}")
        return v


class TaskUpdateRequest(AppBaseModel):
    """Request body for PATCH /api/v1/projects/{project_id}/tasks/{task_id}."""

    status: str | None = None
    priority: str | None = None
    assigned_agent: str | None = None
    acceptance_criteria: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in TASK_STATUSES:
            raise ValueError(f"status must be one of: {sorted(TASK_STATUSES)}")
        return v


class TaskResponse(AppBaseModel):
    """Task response schema."""

    id: str
    project_id: str
    title: str
    description: str
    status: str
    priority: str
    assigned_agent: str | None = None
    acceptance_criteria: str | None = None
    complexity_estimate: str | None = None
    attempt_count: int
    requires_human_approval: bool
    order_index: int
    created_at: datetime
    updated_at: datetime
