"""
Agent Workflow — state machine for the full AgentForge pipeline.

Orchestrates agents through the following states:

  pending
    → [RequirementsAnalyst] → requirements_review   (human gate)
    → [SystemArchitect]     → architecture_review   (human gate)
    → [TaskPlanner]         → planning
    → [per-task loop]
        → SoftwareDeveloper → implementing
        → QAEngineer        → qa_review
        → SecurityEngineer  → security_review
        → CodeReviewer      → code_review
        → (repair loop if failed, up to max_repair_attempts)
    → completed | failed

This module is designed to be called from a FastAPI background task.
Progress is written to the DB workflow_events table and project.status is
updated at each state transition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentResult
from app.agents.code_reviewer import CodeReviewerAgent
from app.agents.qa_engineer import QAEngineerAgent
from app.agents.requirements_analyst import RequirementsAnalystAgent
from app.agents.security_engineer import SecurityEngineerAgent
from app.agents.software_developer import SoftwareDeveloperAgent
from app.agents.system_architect import SystemArchitectAgent
from app.agents.task_planner import TaskPlannerAgent
from app.models.db_models import (
    Artifact,
    Project,
    Task,
    TaskDependency,
    TaskExecutionAttempt,
    WorkflowEvent,
)
from app.services.runner import get_execution_runner
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Workflow context
# ---------------------------------------------------------------------------


@dataclass
class WorkflowContext:
    """All state accumulated as the workflow progresses."""

    project_id: str
    project_name: str
    project_description: str
    preferred_language: str
    preferred_framework: str
    preferred_database: str
    max_repair_attempts: int = 3

    # Accumulated agent outputs
    requirements_document: str = ""
    architecture_document: str = ""
    architecture_summary: str = ""
    task_plan: dict[str, Any] = field(default_factory=dict)

    # Per-task state (keyed by task_id)
    task_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Error tracking
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Status transition helper
# ---------------------------------------------------------------------------


async def _set_project_status(
    db: AsyncSession,
    project: Project,
    new_status: str,
    event_type: str,
    message: str,
    severity: str = "info",
) -> None:
    project.status = new_status
    project.updated_at = datetime.now(UTC)
    event = WorkflowEvent(
        project_id=project.id,
        event_type=event_type,
        message=message,
        severity=severity,
    )
    db.add(event)
    await db.flush()
    logger.info("[%s] %s → %s: %s", project.id, event_type, new_status, message)


async def _add_event(
    db: AsyncSession,
    project_id: str,
    event_type: str,
    message: str,
    severity: str = "info",
    agent_run_id: str | None = None,
) -> None:
    event = WorkflowEvent(
        project_id=project_id,
        event_type=event_type,
        message=message,
        severity=severity,
        agent_run_id=agent_run_id,
    )
    db.add(event)
    await db.flush()


async def _save_artifact(
    db: AsyncSession,
    project_id: str,
    artifact_type: str,
    name: str,
    content: str,
    agent_run_id: str | None = None,
) -> None:
    artifact = Artifact(
        project_id=project_id,
        artifact_type=artifact_type,
        name=name,
        content=content,
        agent_run_id=agent_run_id,
        created_at=datetime.now(UTC),
    )
    db.add(artifact)
    await db.flush()


# ---------------------------------------------------------------------------
# Phase 1: Requirements Analysis
# ---------------------------------------------------------------------------


async def run_requirements_phase(
    ctx: WorkflowContext,
    db: AsyncSession,
    project: Project,
) -> AgentResult:
    agent = RequirementsAnalystAgent()
    result = await agent.run(
        {
            "project_name": ctx.project_name,
            "project_description": ctx.project_description,
            "preferred_language": ctx.preferred_language,
            "preferred_framework": ctx.preferred_framework,
            "preferred_database": ctx.preferred_database,
        },
        db=db,
        project_id=ctx.project_id,
    )

    if result.success:
        ctx.requirements_document = result.output
        await _save_artifact(
            db, ctx.project_id, "requirements", "requirements.md", result.output
        )
        await _set_project_status(
            db, project,
            "requirements_review",
            "requirements_generated",
            "Requirements analysis complete. Awaiting human review.",
        )
    else:
        ctx.errors.append(f"Requirements analysis failed: {result.error}")
        await _add_event(
            db, ctx.project_id, "requirements_failed",
            f"Requirements analysis failed: {result.error}", severity="error"
        )

    return result


# ---------------------------------------------------------------------------
# Phase 2: System Architecture
# ---------------------------------------------------------------------------


async def run_architecture_phase(
    ctx: WorkflowContext,
    db: AsyncSession,
    project: Project,
) -> AgentResult:
    agent = SystemArchitectAgent()
    result = await agent.run(
        {
            "project_name": ctx.project_name,
            "requirements_document": ctx.requirements_document,
            "preferred_language": ctx.preferred_language,
            "preferred_framework": ctx.preferred_framework,
            "preferred_database": ctx.preferred_database,
        },
        db=db,
        project_id=ctx.project_id,
    )

    if result.success:
        ctx.architecture_document = result.output
        # Create a shorter summary for later agent context
        ctx.architecture_summary = result.output[:3000]
        await _save_artifact(
            db, ctx.project_id, "architecture", "architecture.md", result.output
        )
        await _set_project_status(
            db, project,
            "architecture_review",
            "architecture_generated",
            "Architecture design complete. Awaiting human review.",
        )
    else:
        ctx.errors.append(f"Architecture design failed: {result.error}")
        await _add_event(
            db, ctx.project_id, "architecture_failed",
            f"Architecture design failed: {result.error}", severity="error"
        )

    return result


# ---------------------------------------------------------------------------
# Phase 3: Task Planning
# ---------------------------------------------------------------------------


async def run_planning_phase(
    ctx: WorkflowContext,
    db: AsyncSession,
    project: Project,
) -> AgentResult:
    await _set_project_status(
        db, project, "planning", "planning_started", "Task planning in progress."
    )

    agent = TaskPlannerAgent()
    result = await agent.run(
        {
            "project_name": ctx.project_name,
            "requirements_document": ctx.requirements_document,
            "architecture_document": ctx.architecture_document,
        },
        db=db,
        project_id=ctx.project_id,
    )

    if result.success:
        ctx.task_plan = result.parsed
        # Persist tasks to the DB
        await _persist_tasks(db, ctx.project_id, result.parsed.get("tasks", []))
        await _add_event(
            db, ctx.project_id, "tasks_created",
            f"{result.parsed.get('total_tasks', 0)} tasks created from task plan."
        )
    else:
        ctx.errors.append(f"Task planning failed: {result.error}")
        await _add_event(
            db, ctx.project_id, "planning_failed",
            f"Task planning failed: {result.error}", severity="error"
        )

    return result


async def _persist_tasks(
    db: AsyncSession, project_id: str, tasks: list[dict]
) -> None:
    """Insert tasks from the planner into the DB, resolving dependency titles."""
    title_to_id: dict[str, str] = {}

    for task_data in tasks:
        task = Task(
            project_id=project_id,
            title=task_data["title"],
            description=task_data["description"],
            priority=task_data.get("priority", "medium"),
            assigned_agent=task_data.get("assigned_agent", "software-developer"),
            acceptance_criteria=task_data.get("acceptance_criteria", ""),
            complexity_estimate=task_data.get("complexity_estimate", "unknown"),
            order_index=task_data.get("order_index", 0),
            status="pending",
        )
        db.add(task)
        await db.flush()
        title_to_id[task.title] = task.id

    # Second pass: wire up dependencies
    result = await db.execute(
        select(Task).where(Task.project_id == project_id)
    )
    db_tasks = {t.title: t for t in result.scalars().all()}

    for task_data in tasks:
        dep_titles = task_data.get("dependency_titles", [])
        task = db_tasks.get(task_data["title"])
        if task is None:
            continue
        for dep_title in dep_titles:
            dep_task = db_tasks.get(dep_title)
            if dep_task:
                db.add(TaskDependency(task_id=task.id, depends_on_task_id=dep_task.id))

    await db.flush()


# ---------------------------------------------------------------------------
# Phase 4: Per-task implementation loop
# ---------------------------------------------------------------------------


async def run_implementation_phase(
    ctx: WorkflowContext,
    db: AsyncSession,
    project: Project,
) -> bool:
    """
    Run all tasks through the implement → QA → security → review pipeline.

    Returns True if all tasks completed successfully.
    """
    await _set_project_status(
        db, project, "implementing", "implementation_started",
        "Implementation phase started."
    )

    # Load tasks ordered by dependency order
    result = await db.execute(
        select(Task)
        .where(Task.project_id == ctx.project_id)
        .order_by(Task.order_index, Task.created_at)
    )
    tasks = result.scalars().all()

    all_success = True
    for task in tasks:
        success = await _run_task_pipeline(ctx, db, task)
        if not success:
            all_success = False
            logger.warning("Task '%s' failed — continuing with remaining tasks.", task.title)

    return all_success


async def _run_task_pipeline(
    ctx: WorkflowContext,
    db: AsyncSession,
    task: Task,
) -> bool:
    """Run a single task through: implement → QA → security → review (with repair loop)."""
    logger.info("Starting pipeline for task '%s'", task.title)
    implemented_files: dict[str, str] = {}
    prior_attempts: list[dict] = []

    for attempt in range(ctx.max_repair_attempts):
        logger.info("Task '%s' attempt %d/%d", task.title, attempt + 1, ctx.max_repair_attempts)

        # --- Implement ---
        dev_agent = SoftwareDeveloperAgent()
        dev_result = await dev_agent.run(
            {
                "task_title": task.title,
                "task_description": task.description,
                "acceptance_criteria": task.acceptance_criteria or "",
                "architecture_summary": ctx.architecture_summary,
                "existing_files": implemented_files,
                "prior_attempts": prior_attempts,
            },
            db=db,
            project_id=ctx.project_id,
        )

        attempt_record = TaskExecutionAttempt(
            task_id=task.id,
            attempt_number=attempt + 1,
            status="in_progress",
            started_at=datetime.now(UTC),
        )
        db.add(attempt_record)
        await db.flush()

        if not dev_result.success:
            prior_attempts.append({
                "output": dev_result.output,
                "error": dev_result.error,
            })
            _update_attempt(attempt_record, "failed", dev_result.error)
            await db.flush()
            continue

        # Persist files to workspace and git branch
        workspace = get_workspace_service()
        runner = get_execution_runner()
        branch_name = f"feat/task-{task.id[:8]}"

        workspace.init_git_repo(ctx.project_id)
        workspace.create_or_checkout_branch(ctx.project_id, branch_name)

        syntax_error = None
        for f in dev_result.parsed.get("files", []):
            action = f.get("action", "create")
            file_path = f["path"]
            content = f.get("content", "")

            if action == "delete":
                workspace.delete_file(ctx.project_id, file_path)
                implemented_files.pop(file_path, None)
            else:
                workspace.write_file(ctx.project_id, file_path, content)
                implemented_files[file_path] = content

                # Validate syntax for Python files
                if file_path.endswith(".py"):
                    chk = runner.check_python_syntax(ctx.project_id, file_path)
                    if not chk.success:
                        syntax_error = f"Syntax error in '{file_path}': {chk.stderr.strip()}"
                        break

        if syntax_error:
            prior_attempts.append({
                "output": dev_result.output,
                "error": syntax_error,
            })
            _update_attempt(attempt_record, "syntax_failed", syntax_error)
            await _add_event(
                db, ctx.project_id, "syntax_check_failed",
                f"Task '{task.title}': {syntax_error}", severity="warning"
            )
            await db.flush()
            continue

        # Commit verified files to the task branch
        workspace.commit_all(ctx.project_id, f"feat: implement {task.title}")

        # --- QA Review ---
        qa_agent = QAEngineerAgent()
        qa_result = await qa_agent.run(
            {
                "task_title": task.title,
                "acceptance_criteria": task.acceptance_criteria or "",
                "implemented_files": implemented_files,
                "architecture_summary": ctx.architecture_summary,
            },
            db=db,
            project_id=ctx.project_id,
        )

        qa_parsed = qa_result.parsed if qa_result.success else {}
        qa_passed = qa_parsed.get("passed", False)

        if not qa_passed and qa_result.success:
            bugs = qa_parsed.get("bugs", [])
            bug_summary = "; ".join(b["title"] for b in bugs[:3])
            prior_attempts.append({
                "output": dev_result.output,
                "error": f"QA failed: {bug_summary}",
            })
            _update_attempt(attempt_record, "qa_failed", f"QA failed: {bug_summary}")
            await db.flush()
            continue

        # --- Security Review ---
        sec_agent = SecurityEngineerAgent()
        sec_result = await sec_agent.run(
            {
                "task_title": task.title,
                "implemented_files": implemented_files,
                "architecture_summary": ctx.architecture_summary,
            },
            db=db,
            project_id=ctx.project_id,
        )

        sec_parsed = sec_result.parsed if sec_result.success else {}
        sec_approved = sec_parsed.get("approved_for_deployment", False)

        if not sec_approved and sec_result.success:
            crit = sec_parsed.get("critical_finding_count", 0)
            high = sec_parsed.get("high_finding_count", 0)
            prior_attempts.append({
                "output": dev_result.output,
                "error": f"Security review failed: {crit} critical, {high} high findings.",
            })
            _update_attempt(
                attempt_record, "security_failed",
                f"Security: {crit} critical, {high} high findings"
            )
            await db.flush()
            continue

        # --- Code Review ---
        cr_agent = CodeReviewerAgent()
        cr_result = await cr_agent.run(
            {
                "task_title": task.title,
                "acceptance_criteria": task.acceptance_criteria or "",
                "implemented_files": implemented_files,
                "qa_report": qa_parsed,
                "security_report": sec_parsed,
                "architecture_summary": ctx.architecture_summary,
            },
            db=db,
            project_id=ctx.project_id,
        )

        cr_parsed = cr_result.parsed if cr_result.success else {}
        cr_approved = cr_parsed.get("approved", False)

        if not cr_approved:
            blockers = cr_parsed.get("blockers_count", 0)
            prior_attempts.append({
                "output": dev_result.output,
                "error": f"Code review: {blockers} blockers. Decision: {cr_parsed.get('decision')}",
            })
            _update_attempt(
                attempt_record, "review_failed",
                f"Code review rejected: {blockers} blockers"
            )
            await db.flush()
            continue

        # --- All gates passed — mark task complete ---
        task.status = "completed"
        task.completed_at = datetime.now(UTC)
        _update_attempt(attempt_record, "completed", None)
        await db.flush()

        ctx.task_results[task.id] = {
            "implemented_files": implemented_files,
            "qa": qa_parsed,
            "security": sec_parsed,
            "review": cr_parsed,
        }

        await _add_event(
            db, ctx.project_id, "task_completed",
            f"Task '{task.title}' completed after {attempt + 1} attempt(s)."
        )
        logger.info("Task '%s' completed on attempt %d.", task.title, attempt + 1)
        return True

    # Exhausted retries
    task.status = "failed"
    task.updated_at = datetime.now(UTC)
    await db.flush()
    await _add_event(
        db, ctx.project_id, "task_failed",
        f"Task '{task.title}' failed after {ctx.max_repair_attempts} attempts.",
        severity="error",
    )
    return False


def _update_attempt(
    attempt: TaskExecutionAttempt, status: str, error: str | None
) -> None:
    attempt.status = status
    attempt.error_message = error
    attempt.completed_at = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Master workflow runner
# ---------------------------------------------------------------------------


async def run_project_workflow(
    project_id: str,
    db: AsyncSession,
    *,
    skip_to_phase: str | None = None,
) -> None:
    """
    Execute the full AgentForge workflow for a project.

    This is designed to run as a FastAPI BackgroundTask.
    Human-in-the-loop gates pause execution (project status is set to
    '*_review') and workflow resumes when the approval API is called.

    Args:
        project_id: The project to run.
        db: AsyncSession — caller is responsible for commit/rollback.
        skip_to_phase: If provided, skip earlier phases (for resuming).
    """
    project = await db.get(Project, project_id)
    if project is None:
        logger.error("Project %s not found — cannot run workflow.", project_id)
        return

    ctx = WorkflowContext(
        project_id=project_id,
        project_name=project.name,
        project_description=project.description,
        preferred_language=project.preferred_language or "python",
        preferred_framework=project.preferred_framework or "fastapi",
        preferred_database=project.preferred_database or "sqlite",
        max_repair_attempts=project.max_repair_attempts,
    )

    logger.info("Starting workflow for project '%s' (%s)", project.name, project_id)

    try:
        # ── Phase 1: Requirements ────────────────────────────────────────────
        if skip_to_phase not in ("architecture", "planning", "implementation"):
            result = await run_requirements_phase(ctx, db, project)
            if not result.success:
                await _set_project_status(
                    db, project, "failed", "workflow_failed",
                    f"Workflow failed at requirements phase: {result.error}",
                    severity="error",
                )
                await db.commit()
                return
            # Pause for human review — workflow resumes via approval endpoint
            await db.commit()
            return

        # ── Phase 2: Architecture ────────────────────────────────────────────
        if skip_to_phase not in ("planning", "implementation"):
            # Reload requirements from artifacts
            ctx.requirements_document = await _load_artifact(
                db, project_id, "requirements"
            )
            result = await run_architecture_phase(ctx, db, project)
            if not result.success:
                await _set_project_status(
                    db, project, "failed", "workflow_failed",
                    f"Workflow failed at architecture phase: {result.error}",
                    severity="error",
                )
                await db.commit()
                return
            await db.commit()
            return

        # ── Phase 3: Planning ────────────────────────────────────────────────
        if skip_to_phase != "implementation":
            ctx.requirements_document = await _load_artifact(db, project_id, "requirements")
            ctx.architecture_document = await _load_artifact(db, project_id, "architecture")
            ctx.architecture_summary = ctx.architecture_document[:3000]

            result = await run_planning_phase(ctx, db, project)
            if not result.success:
                await _set_project_status(
                    db, project, "failed", "workflow_failed",
                    f"Workflow failed at planning phase: {result.error}",
                    severity="error",
                )
                await db.commit()
                return

        # ── Phase 4: Implementation ──────────────────────────────────────────
        ctx.requirements_document = await _load_artifact(db, project_id, "requirements")
        ctx.architecture_document = await _load_artifact(db, project_id, "architecture")
        ctx.architecture_summary = ctx.architecture_document[:3000]

        all_success = await run_implementation_phase(ctx, db, project)

        final_status = "completed" if all_success else "failed"
        final_message = (
            "All tasks completed successfully." if all_success
            else f"Workflow completed with failures. Errors: {ctx.errors[:3]}"
        )
        await _set_project_status(
            db, project, final_status, "workflow_finished", final_message,
            severity="info" if all_success else "error",
        )
        await db.commit()

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unhandled exception in workflow for project %s: %s", project_id, exc)
        try:
            await _set_project_status(
                db, project, "failed", "workflow_error",
                f"Unhandled workflow error: {exc}", severity="critical"
            )
            await db.commit()
        except Exception as inner_exc:  # noqa: BLE001
            logger.warning(
                "Failed to persist 'failed' status for project %s after workflow error: %s",
                project_id,
                inner_exc,
            )


async def _load_artifact(db: AsyncSession, project_id: str, artifact_type: str) -> str:
    """Load the most recent artifact of a given type for a project."""
    result = await db.execute(
        select(Artifact)
        .where(Artifact.project_id == project_id, Artifact.artifact_type == artifact_type)
        .order_by(Artifact.created_at.desc())
        .limit(1)
    )
    artifact = result.scalar_one_or_none()
    return artifact.content if artifact else ""
