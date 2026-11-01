"""Pydantic schemas for Project resources."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import AppBaseModel

# ---------------------------------------------------------------------------
# Enumerations (as string literals for simplicity — full Enum in Phase 3)
# ---------------------------------------------------------------------------

PROJECT_STATUSES = {
    # Initial / terminal states
    "pending",
    "active",
    "in_progress",
    "completed",
    "failed",
    "cancelled",
    # Requirements workflow
    "requirements_review",
    "requirements_approved",
    "requirements_revision",
    # Architecture workflow
    "architecture_review",
    "architecture_approved",
    "architecture_revision",
    # Task planning & implementation
    "planning",
    "implementing",
    # QA & security workflow
    "qa_review",
    "security_review",
    "code_review",
    "repair",
}
VALID_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "go",
    "rust",
    "java",
    "csharp",
    "ruby",
    "php",
    "kotlin",
    "swift",
    "other",
}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ProjectCreateRequest(AppBaseModel):
    """Request body for POST /api/v1/projects."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Short, human-readable project name.",
        examples=["My Todo App"],
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=10_000,
        description="Natural-language description of the application to build.",
        examples=["A REST API for managing personal tasks with authentication."],
    )
    preferred_language: str | None = Field(
        default=None,
        description="Preferred programming language for generated code.",
        examples=["python"],
    )
    preferred_framework: str | None = Field(
        default=None,
        max_length=64,
        description="Preferred application framework.",
        examples=["fastapi"],
    )
    preferred_database: str | None = Field(
        default=None,
        max_length=64,
        description="Preferred database system.",
        examples=["sqlite"],
    )
    max_repair_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum automated repair attempts per bug.",
    )
    settings: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional project settings.",
    )

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        if v is not None and v.lower() not in VALID_LANGUAGES:
            raise ValueError(f"preferred_language must be one of: {sorted(VALID_LANGUAGES)}")
        return v.lower() if v else v


class ProjectUpdateRequest(AppBaseModel):
    """Request body for PATCH /api/v1/projects/{project_id}."""

    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = Field(default=None, min_length=10, max_length=10_000)
    status: str | None = Field(default=None)
    max_repair_attempts: int | None = Field(default=None, ge=1, le=10)
    settings: dict[str, Any] | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in PROJECT_STATUSES:
            raise ValueError(f"status must be one of: {sorted(PROJECT_STATUSES)}")
        return v


class RequirementsSubmitRequest(AppBaseModel):
    """Request body for POST /api/v1/projects/{project_id}/requirements."""

    raw_requirements: str = Field(
        ...,
        min_length=10,
        max_length=50_000,
        description="Raw natural-language requirements text from the user.",
    )


class ApproveRequest(AppBaseModel):
    """Request body for approval endpoints (requirements / architecture)."""

    approved: bool = Field(..., description="True to approve, False to reject.")
    reviewer_notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional reviewer comments.",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ProjectSummaryResponse(AppBaseModel):
    """Lightweight project summary for list endpoints."""

    id: str
    name: str
    status: str
    preferred_language: str | None = None
    preferred_framework: str | None = None
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(AppBaseModel):
    """Full project detail response."""

    id: str
    name: str
    description: str
    status: str
    preferred_language: str | None = None
    preferred_framework: str | None = None
    preferred_database: str | None = None
    max_repair_attempts: int
    workspace_path: str | None = None
    git_branch: str | None = None
    settings: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
