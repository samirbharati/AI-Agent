"""
QA Verification & Security Scan API endpoints.

  GET  /api/v1/projects/{project_id}/security/scan  — full deterministic security scan
  GET  /api/v1/projects/{project_id}/security/tools — detect available security CLI tools
  POST /api/v1/projects/{project_id}/qa/run-tests   — run pytest in project workspace
  GET  /api/v1/projects/{project_id}/qa/test-files  — discover automated test files
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.db_models import Project
from app.services.qa_runner import get_qa_runner
from app.services.security_scanner import get_security_scanner

logger = logging.getLogger(__name__)
router = APIRouter(tags=["qa-security"])


async def _get_project_or_404(db: AsyncSession, project_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "project_not_found", "message": f"Project '{project_id}' not found."},
        )
    return project


# ---------------------------------------------------------------------------
# Security Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/security/scan",
    summary="Run deterministic application security scan on project workspace",
)
async def scan_project_security(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    scanner = get_security_scanner()
    return scanner.scan_project(project_id)


@router.get(
    "/security/tools",
    summary="Check availability of deterministic security scanners on host",
)
async def get_detected_security_tools() -> dict[str, Any]:
    scanner = get_security_scanner()
    return {
        "tools": scanner.detect_available_tools(),
    }


# ---------------------------------------------------------------------------
# QA Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/projects/{project_id}/qa/run-tests",
    summary="Execute automated test suite in the project workspace",
)
async def run_project_tests(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    timeout: int = Query(default=60, ge=10, le=180),
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    qa_runner = get_qa_runner()
    result = qa_runner.run_tests(project_id, timeout=timeout)

    return {
        "project_id": result.project_id,
        "passed": result.passed,
        "status": result.status,
        "total_tests": result.total_tests,
        "passed_count": result.passed_count,
        "failed_count": result.failed_count,
        "blocked_count": result.blocked_count,
        "not_executed_count": result.not_executed_count,
        "duration_seconds": result.duration_seconds,
        "bugs": result.bugs,
        "raw_stdout": result.raw_stdout,
        "raw_stderr": result.raw_stderr,
    }


@router.get(
    "/projects/{project_id}/qa/test-files",
    summary="Discover test files in the project workspace",
)
async def discover_project_test_files(
    project_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    await _get_project_or_404(db, project_id)
    qa_runner = get_qa_runner()
    files = qa_runner.discover_test_files(project_id)
    return {
        "project_id": project_id,
        "total": len(files),
        "test_files": files,
    }

