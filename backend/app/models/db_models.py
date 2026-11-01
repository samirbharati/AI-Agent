"""
ORM model definitions for AgentForge.

All tables use explicit column names, foreign keys, indexes, and status
enumerations. JSON fields are used only where structure is genuinely variable.

Naming conventions:
  - Tables: snake_case, plural
  - Primary keys: <table_singular>_id or id (for reference tables)
  - Timestamps: created_at, updated_at (UTC, stored as TEXT in SQLite ISO-8601)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Reference / lookup tables
# ---------------------------------------------------------------------------


class AgentDefinition(Base):
    """
    Static catalogue of agent types known to the system.

    Seeded at startup; not modified at runtime.
    """

    __tablename__ = "agent_definitions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    # Relationships
    runs: Mapped[list[AgentRun]] = relationship(back_populates="agent_definition")


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class Project(Base):
    """Top-level project record."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | active | completed | failed | cancelled
    preferred_language: Mapped[str | None] = mapped_column(String(64))
    preferred_framework: Mapped[str | None] = mapped_column(String(64))
    preferred_database: Mapped[str | None] = mapped_column(String(64))
    max_repair_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    workspace_path: Mapped[str | None] = mapped_column(String(512))
    git_branch: Mapped[str | None] = mapped_column(String(128))
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    # Relationships
    requirements: Mapped[list[Requirement]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[list[AgentRun]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    test_runs: Mapped[list[TestRun]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    security_findings: Mapped[list[SecurityFinding]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    bugs: Mapped[list[Bug]] = relationship(back_populates="project", cascade="all, delete-orphan")
    approval_requests: Mapped[list[ApprovalRequest]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    workflow_events: Mapped[list[WorkflowEvent]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_projects_status", "status"),)


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------


class Requirement(Base):
    """
    A single structured requirement extracted by the Requirements Analyst.
    """

    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    req_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # functional | non_functional | constraint | assumption | risk | question
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # critical | high | medium | low
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft"
    )  # draft | approved | rejected | deferred
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    source_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    project: Mapped[Project] = relationship(back_populates="requirements")

    __table_args__ = (
        Index("ix_requirements_project_id", "project_id"),
        Index("ix_requirements_req_type", "req_type"),
    )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class Task(Base):
    """A single implementation task created by the Task Planner."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | ready | in_progress | completed | failed | blocked | cancelled
    priority: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # critical | high | medium | low
    assigned_agent: Mapped[str | None] = mapped_column(
        ForeignKey("agent_definitions.id", ondelete="SET NULL")
    )
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    complexity_estimate: Mapped[str | None] = mapped_column(String(16))  # xs | s | m | l | xl
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    project: Mapped[Project] = relationship(back_populates="tasks")
    dependencies: Mapped[list[TaskDependency]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        cascade="all, delete-orphan",
    )
    execution_attempts: Mapped[list[TaskExecutionAttempt]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_status", "status"),
    )


class TaskDependency(Base):
    """Directed dependency edge between two tasks."""

    __tablename__ = "task_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id: Mapped[str] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
        Index("ix_task_dependencies_task_id", "task_id"),
    )


class TaskExecutionAttempt(Base):
    """
    Records each time a developer agent attempts to implement a task.
    """

    __tablename__ = "task_execution_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="in_progress"
    )  # in_progress | completed | failed
    summary: Mapped[str | None] = mapped_column(Text)
    files_changed: Mapped[list[str] | None] = mapped_column(JSON)
    commands_executed: Mapped[list[str] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    task: Mapped[Task] = relationship(back_populates="execution_attempts")

    __table_args__ = (Index("ix_task_exec_attempts_task_id", "task_id"),)


# ---------------------------------------------------------------------------
# Agent Runs
# ---------------------------------------------------------------------------


class AgentRun(Base):
    """
    A single invocation of an agent within a project.

    An agent run is associated with a project and optionally a task.
    """

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_definition_id: Mapped[str] = mapped_column(
        ForeignKey("agent_definitions.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | running | success | failure | error
    input_summary: Mapped[str | None] = mapped_column(Text)
    output_summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    model_used: Mapped[str | None] = mapped_column(String(128))
    duration_seconds: Mapped[float | None] = mapped_column()
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    project: Mapped[Project] = relationship(back_populates="runs")
    agent_definition: Mapped[AgentDefinition] = relationship(back_populates="runs")
    events: Mapped[list[WorkflowEvent]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_agent_runs_project_id", "project_id"),
        Index("ix_agent_runs_status", "status"),
    )


# ---------------------------------------------------------------------------
# Artifacts
# ---------------------------------------------------------------------------


class Artifact(Base):
    """A generated artifact document stored in the database."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # requirements | architecture | code | test_plan | test_report | security_report
    name: Mapped[str] = mapped_column(String(256), nullable=False)  # e.g. requirements.md
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")  # full text content
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="artifacts")

    __table_args__ = (
        Index("ix_artifacts_project_id", "project_id"),
        Index("ix_artifacts_artifact_type", "artifact_type"),
    )


# ---------------------------------------------------------------------------
# Test Runs
# ---------------------------------------------------------------------------


class TestRun(Base):
    """A single test execution."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    test_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # unit | integration | e2e | api
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_run"
    )  # not_run | passed | failed | error
    total_tests: Mapped[int | None] = mapped_column(Integer)
    passed: Mapped[int | None] = mapped_column(Integer)
    failed: Mapped[int | None] = mapped_column(Integer)
    skipped: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column()
    summary: Mapped[str | None] = mapped_column(Text)
    raw_output: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="test_runs")

    __table_args__ = (Index("ix_test_runs_project_id", "project_id"),)


# ---------------------------------------------------------------------------
# Security Findings
# ---------------------------------------------------------------------------


class SecurityFinding(Base):
    """A security vulnerability found during a security scan."""

    __tablename__ = "security_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    scanner: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # semgrep | gitleaks | trivy | llm_review
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # critical | high | medium | low | info
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    affected_file: Mapped[str | None] = mapped_column(String(512))
    line_number: Mapped[int | None] = mapped_column(Integer)
    evidence: Mapped[str | None] = mapped_column(Text)
    remediation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open"
    )  # open | fixed | accepted | false_positive
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="security_findings")

    __table_args__ = (
        Index("ix_security_findings_project_id", "project_id"),
        Index("ix_security_findings_severity", "severity"),
    )


# ---------------------------------------------------------------------------
# Bugs
# ---------------------------------------------------------------------------


class Bug(Base):
    """A structured bug record created by the QA agent."""

    __tablename__ = "bugs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="medium"
    )  # critical | high | medium | low
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="open"
    )  # open | in_progress | fixed | verified | wont_fix | blocked
    affected_files: Mapped[list[str] | None] = mapped_column(JSON)
    reproduction_steps: Mapped[str | None] = mapped_column(Text)
    expected_behavior: Mapped[str | None] = mapped_column(Text)
    actual_behavior: Mapped[str | None] = mapped_column(Text)
    logs: Mapped[str | None] = mapped_column(Text)
    assigned_agent: Mapped[str | None] = mapped_column(
        ForeignKey("agent_definitions.id", ondelete="SET NULL"), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fix_summary: Mapped[str | None] = mapped_column(Text)
    verification_evidence: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    project: Mapped[Project] = relationship(back_populates="bugs")

    __table_args__ = (
        Index("ix_bugs_project_id", "project_id"),
        Index("ix_bugs_status", "status"),
    )


# ---------------------------------------------------------------------------
# Approval Requests
# ---------------------------------------------------------------------------


class ApprovalRequest(Base):
    """
    A human approval gate.

    The workflow pauses until the user approves or rejects via the dashboard.
    """

    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    approval_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # requirements | architecture | code_change | deployment | destructive_operation
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending"
    )  # pending | approved | rejected | expired
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    project: Mapped[Project] = relationship(back_populates="approval_requests")

    __table_args__ = (
        Index("ix_approval_requests_project_id", "project_id"),
        Index("ix_approval_requests_status", "status"),
    )


# ---------------------------------------------------------------------------
# Workflow Events
# ---------------------------------------------------------------------------


class WorkflowEvent(Base):
    """
    An immutable audit log entry for agent actions and workflow transitions.

    Events are append-only and are never modified after creation.
    The SSE stream cursor uses ``created_at`` ordering and UUID ``id`` for
    deduplication. Sensitive values (tokens, passwords) must NOT be stored here.
    """

    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # e.g. orchestrator, requirements-analyst
    category: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # agent_lifecycle, llm_request, tool_execution, test_execution, security_scan, workflow_transition
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # running, success, failure, warning, info
    event_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # agent_started | agent_completed | agent_failed | status_changed | approval_requested | etc.
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, default="info"
    )  # debug | info | warning | error | critical
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped[Project] = relationship(back_populates="workflow_events")
    agent_run: Mapped[AgentRun] = relationship(back_populates="events")

    __table_args__ = (
        Index("ix_workflow_events_project_id", "project_id"),
        Index("ix_workflow_events_event_type", "event_type"),
        Index("ix_workflow_events_created_at", "created_at"),
        Index("ix_workflow_events_severity", "severity"),
        Index("ix_workflow_events_trace_id", "trace_id"),
        Index("ix_workflow_events_category", "category"),
    )


# ---------------------------------------------------------------------------
# Model Usage Statistics
# ---------------------------------------------------------------------------


class ModelUsageStat(Base):
    """
    Telemetry record for a single LLM inference request.

    Token counts may be None when the local model API does not report them.
    These are never presented as billing estimates.
    """

    __tablename__ = "model_usage_stats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_role: Mapped[str | None] = mapped_column(String(64))
    duration_seconds: Mapped[float | None] = mapped_column()
    token_count_in: Mapped[int | None] = mapped_column(Integer)
    token_count_out: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_type: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    __table_args__ = (
        Index("ix_model_usage_stats_project_id", "project_id"),
        Index("ix_model_usage_stats_created_at", "created_at"),
    )
