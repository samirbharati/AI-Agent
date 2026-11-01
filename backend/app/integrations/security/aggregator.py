"""
Security Aggregator orchestrating Semgrep, Gitleaks, and Trivy scanners.
"""

from __future__ import annotations

import logging
from typing import Any

from app.integrations.security.gitleaks_runner import get_gitleaks_runner
from app.integrations.security.schemas import (
    IntegratedSecurityFinding,
    SecurityScanReport,
)
from app.integrations.security.semgrep_runner import get_semgrep_runner
from app.integrations.security.trivy_runner import get_trivy_runner
from app.logging.correlation import generate_trace_id, get_current_trace_id
from app.logging.event_service import EventService
from app.services.workspace import get_workspace_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class SecurityAggregator:
    """
    Coordinates multi-scanner security audits (SAST, Secret Detection, Dependency CVEs)
    and emits correlated events.
    """

    def __init__(self) -> None:
        self.semgrep = get_semgrep_runner()
        self.gitleaks = get_gitleaks_runner()
        self.trivy = get_trivy_runner()
        self._workspace = get_workspace_service()

    async def run_full_security_audit(
        self,
        project_id: str,
        db: AsyncSession | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute enabled security scanners against the project workspace.
        """
        trace = trace_id or get_current_trace_id() or generate_trace_id()
        workspace_dir = self._workspace.get_workspace_path(project_id)

        reports: list[SecurityScanReport] = []
        all_findings: list[IntegratedSecurityFinding] = []

        # 1. Semgrep SAST
        if self.semgrep.is_enabled():
            r = self.semgrep.scan_directory(workspace_dir, project_id)
            reports.append(r)
            all_findings.extend(r.findings)

        # 2. Gitleaks Secret Detection
        if self.gitleaks.is_enabled():
            r = self.gitleaks.scan_directory(workspace_dir, project_id)
            reports.append(r)
            all_findings.extend(r.findings)

        # 3. Trivy Dependency & Config
        if self.trivy.is_enabled():
            r = self.trivy.scan_directory(workspace_dir, project_id)
            reports.append(r)
            all_findings.extend(r.findings)

        total_critical = sum(r.critical_count for r in reports)
        total_high = sum(r.high_count for r in reports)
        total_medium = sum(r.medium_count for r in reports)
        total_low = sum(r.low_count for r in reports)

        passed = total_critical == 0 and total_high == 0

        # Log security audit to Central Logs if DB session provided
        if db:
            severity = "info" if passed else ("critical" if total_critical > 0 else "error")
            await EventService.emit_event(
                db,
                project_id=project_id,
                event_type="security_audit_completed",
                message=f"Multi-scanner security audit: {len(all_findings)} findings (Crit: {total_critical}, High: {total_high}, Med: {total_medium})",
                severity=severity,
                source="security-aggregator",
                category="security_scan",
                trace_id=trace,
                payload={
                    "passed": passed,
                    "total_findings": len(all_findings),
                    "critical": total_critical,
                    "high": total_high,
                    "medium": total_medium,
                    "low": total_low,
                    "scanners": [r.scanner.value for r in reports],
                },
            )

        return {
            "project_id": project_id,
            "passed": passed,
            "total_findings": len(all_findings),
            "critical_count": total_critical,
            "high_count": total_high,
            "medium_count": total_medium,
            "low_count": total_low,
            "reports": [r.model_dump() for r in reports],
            "findings": [f.model_dump() for f in all_findings],
        }


_security_aggregator_instance: SecurityAggregator | None = None


def get_security_aggregator() -> SecurityAggregator:
    global _security_aggregator_instance
    if _security_aggregator_instance is None:
        _security_aggregator_instance = SecurityAggregator()
    return _security_aggregator_instance
