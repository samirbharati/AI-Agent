"""
Automated Defect Lifecycle, Repair Loop, and Regression Verification Manager.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Bug
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)

MAX_REPAIR_ATTEMPTS = 3


class BugLifecycleManager:
    """
    Coordinates defect discovery, task assignment, root-cause tracking,
    repair attempts (up to 3), regression testing, and verification.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.workspace = get_workspace_service()

    async def report_defect(
        self,
        project_id: str,
        title: str,
        description: str,
        severity: str = "high",
        affected_files: list[str] | None = None,
        reproduction_steps: str | None = None,
        expected_behavior: str | None = None,
        actual_behavior: str | None = None,
        logs: str | None = None,
        task_id: str | None = None,
    ) -> Bug:
        """
        Record a newly discovered defect from QA, Security, or Load testing.
        """
        bug = Bug(
            project_id=project_id,
            task_id=task_id,
            title=title,
            description=description,
            severity=severity,
            status="open",
            affected_files=affected_files or [],
            reproduction_steps=reproduction_steps,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            logs=logs,
            attempt_count=0,
        )
        self.db.add(bug)
        await self.db.commit()
        await self.db.refresh(bug)
        logger.warning(
            "Defect recorded: [%s] %s (Severity: %s, Project: %s)",
            bug.id[:8],
            title,
            severity,
            project_id,
        )
        return bug

    async def record_repair_attempt(
        self,
        bug_id: str,
        fix_summary: str,
        retest_passed: bool,
        verification_evidence: str,
    ) -> Bug:
        """
        Record Developer repair attempt and QA verification outcome.
        """
        bug = await self.db.get(Bug, bug_id)
        if not bug:
            raise ValueError(f"Bug {bug_id} not found.")

        bug.attempt_count += 1
        bug.fix_summary = fix_summary
        bug.verification_evidence = verification_evidence
        bug.updated_at = datetime.now(UTC)

        if retest_passed:
            bug.status = "verified"
            logger.info("Bug %s successfully fixed and verified by QA on attempt %d", bug_id, bug.attempt_count)
        else:
            if bug.attempt_count >= MAX_REPAIR_ATTEMPTS:
                bug.status = "blocked"
                logger.error(
                    "Bug %s exceeded max repair attempts (%d). Marking as BLOCKED for human review.",
                    bug_id,
                    bug.attempt_count,
                )
            else:
                bug.status = "in_progress"
                logger.warning(
                    "Bug %s repair attempt %d failed verification. Returning to developer.",
                    bug_id,
                    bug.attempt_count,
                )

        await self.db.commit()
        await self.db.refresh(bug)
        return bug

    async def list_open_bugs(self, project_id: str) -> list[Bug]:
        """Fetch all unresolved bugs for a project."""
        stmt = (
            select(Bug)
            .where(Bug.project_id == project_id, Bug.status.in_(["open", "in_progress", "blocked"]))
            .order_by(Bug.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_blocking_bugs(self, project_id: str) -> list[Bug]:
        """Fetch bugs that block release (Critical/High unresolved defects)."""
        stmt = (
            select(Bug)
            .where(
                Bug.project_id == project_id,
                Bug.severity.in_(["critical", "high"]),
                Bug.status.in_(["open", "in_progress", "blocked"]),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

