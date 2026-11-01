"""
Product Quality Engineering & Validation System API endpoints.
Provides endpoints for executing audits, tracking gates, running progressive load tests,
and managing the defect lifecycle.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.db_models import LoadTestRun, QualityGateRecord, QualityReportRecord
from app.quality.bug_lifecycle import BugLifecycleManager
from app.quality.load_test_runner import LoadTestRunner
from app.quality.quality_engine import QualityEngine
from app.quality.schemas import QualityCertificationReport
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quality", tags=["quality"])


class RunQualityAuditRequest(BaseModel):
    build_id: str | None = None
    run_load_test: bool = True
    max_load_stages: int = 3


class CreateBugRequest(BaseModel):
    title: str
    description: str
    severity: str = "high"
    affected_files: list[str] | None = None
    reproduction_steps: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    logs: str | None = None
    task_id: str | None = None


class BugRepairRequest(BaseModel):
    fix_summary: str
    retest_passed: bool
    verification_evidence: str


class RunLoadTestRequest(BaseModel):
    test_path: str = "/api/v1/health"
    max_stages: int = 3


@router.post("/{project_id}/run", response_model=QualityCertificationReport)
async def run_quality_audit(
    project_id: str,
    payload: RunQualityAuditRequest,
    db: AsyncSession = Depends(get_db),
) -> QualityCertificationReport:
    """Execute complete 10-gate product quality engineering validation suite."""
    engine = QualityEngine(db=db)
    try:
        report = await engine.run_full_quality_audit(
            project_id=project_id,
            build_id=payload.build_id,
            run_load_test=payload.run_load_test,
            max_load_stages=payload.max_load_stages,
        )
        return report
    except Exception as exc:
        logger.error("Quality audit execution failed for %s: %s", project_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quality audit failed: {exc}",
        ) from exc


@router.get("/{project_id}/reports")
async def list_quality_reports(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """List historical quality certification reports for a project."""
    stmt = (
        select(QualityReportRecord)
        .where(QualityReportRecord.project_id == project_id)
        .order_by(QualityReportRecord.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    records = res.scalars().all()
    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "build_id": r.build_id,
            "overall_status": r.overall_status,
            "total_tests": r.total_tests,
            "passed_tests": r.passed_tests,
            "failed_tests": r.failed_tests,
            "coverage_percent": r.coverage_percent,
            "critical_bugs_count": r.critical_bugs_count,
            "high_bugs_count": r.high_bugs_count,
            "security_findings_count": r.security_findings_count,
            "p95_latency_ms": r.p95_latency_ms,
            "max_concurrency_tested": r.max_concurrency_tested,
            "summary_markdown": r.summary_markdown,
            "html_report_path": r.html_report_path,
            "pdf_report_path": r.pdf_report_path,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/{project_id}/gates")
async def get_latest_gates(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Fetch the most recent evaluations for all 10 quality gates."""
    stmt = (
        select(QualityGateRecord)
        .where(QualityGateRecord.project_id == project_id)
        .order_by(QualityGateRecord.evaluated_at.desc())
    )
    res = await db.execute(stmt)
    all_gates = res.scalars().all()

    # Deduplicate to keep latest per gate_number
    latest_by_num: dict[int, QualityGateRecord] = {}
    for g in all_gates:
        if g.gate_number not in latest_by_num:
            latest_by_num[g.gate_number] = g

    return [
        {
            "id": r.id,
            "gate_number": r.gate_number,
            "gate_name": r.gate_name,
            "status": r.status,
            "criterion": r.criterion,
            "evaluated_value": r.evaluated_value,
            "reason": r.reason,
            "evidence": r.evidence_json or {},
            "evaluated_at": r.evaluated_at.isoformat() if r.evaluated_at else None,
        }
        for r in sorted(latest_by_num.values(), key=lambda x: x.gate_number)
    ]


@router.get("/{project_id}/load-tests")
async def list_load_test_runs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
) -> list[dict[str, Any]]:
    """List historical concurrency and load test stage results."""
    stmt = (
        select(LoadTestRun)
        .where(LoadTestRun.project_id == project_id)
        .order_by(LoadTestRun.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [
        {
            "id": r.id,
            "stage": r.stage,
            "target_concurrency": r.target_concurrency,
            "actual_concurrency": r.actual_concurrency,
            "total_requests": r.total_requests,
            "successful_requests": r.successful_requests,
            "failed_requests": r.failed_requests,
            "requests_per_second": r.requests_per_second,
            "avg_latency_ms": r.avg_latency_ms,
            "p50_latency_ms": r.p50_latency_ms,
            "p90_latency_ms": r.p90_latency_ms,
            "p95_latency_ms": r.p95_latency_ms,
            "p99_latency_ms": r.p99_latency_ms,
            "max_latency_ms": r.max_latency_ms,
            "cpu_percent": r.cpu_percent,
            "memory_mb": r.memory_mb,
            "status": r.status,
            "error_summary": r.error_summary,
            "bottlenecks": r.bottlenecks or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.post("/{project_id}/load-test")
async def run_load_test(
    project_id: str,
    payload: RunLoadTestRequest,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Trigger progressive multi-stage load simulation."""
    runner = LoadTestRunner(db=db)
    stages = await runner.run_progressive_load_test(
        project_id=project_id,
        test_path=payload.test_path,
        max_stages=payload.max_stages,
    )
    return [s.model_dump() for s in stages]


@router.get("/{project_id}/bugs")
async def list_project_bugs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all tracked bugs and defects in the defect lifecycle."""
    mgr = BugLifecycleManager(db)
    bugs = await mgr.list_open_bugs(project_id)
    return [
        {
            "id": b.id,
            "title": b.title,
            "description": b.description,
            "severity": b.severity,
            "status": b.status,
            "affected_files": b.affected_files or [],
            "reproduction_steps": b.reproduction_steps,
            "expected_behavior": b.expected_behavior,
            "actual_behavior": b.actual_behavior,
            "attempt_count": b.attempt_count,
            "fix_summary": b.fix_summary,
            "verification_evidence": b.verification_evidence,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        }
        for b in bugs
    ]


@router.post("/{project_id}/bugs")
async def create_project_bug(
    project_id: str,
    payload: CreateBugRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Report a newly identified defect into the defect lifecycle."""
    mgr = BugLifecycleManager(db)
    bug = await mgr.report_defect(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        affected_files=payload.affected_files,
        reproduction_steps=payload.reproduction_steps,
        expected_behavior=payload.expected_behavior,
        actual_behavior=payload.actual_behavior,
        logs=payload.logs,
        task_id=payload.task_id,
    )
    return {"id": bug.id, "status": bug.status, "message": "Defect successfully reported."}


@router.patch("/{project_id}/bugs/{bug_id}/repair")
async def record_bug_repair(
    project_id: str,
    bug_id: str,
    payload: BugRepairRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record Developer repair attempt and QA retest outcome."""
    mgr = BugLifecycleManager(db)
    try:
        bug = await mgr.record_repair_attempt(
            bug_id=bug_id,
            fix_summary=payload.fix_summary,
            retest_passed=payload.retest_passed,
            verification_evidence=payload.verification_evidence,
        )
        return {
            "id": bug.id,
            "status": bug.status,
            "attempt_count": bug.attempt_count,
            "fix_summary": bug.fix_summary,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{project_id}/reports/{report_id}/html")
async def get_report_html(
    project_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve standalone HTML quality report content."""
    rec = await db.get(QualityReportRecord, report_id)
    if not rec or not rec.html_report_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report HTML not found.")

    workspace = get_workspace_service()
    try:
        content = workspace.read_file(project_id, rec.html_report_path)
        return Response(content=content, media_type="text/html")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File read error: {exc}") from exc
