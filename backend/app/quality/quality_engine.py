"""
AgentForge Product Quality Engineering Engine.
Central coordinator orchestrating:
- Test-Driven Development & Unit Test execution
- Multi-component integration scenarios
- API contract & schema validation
- Adversarial security breaker audits
- Performance latency percentiles & resource profiling
- Progressive multi-stage concurrency load testing
- Regression testing against known-good baselines
- Independent architectural code review
- Evaluation of all 10 Evidence-Based Quality Gates
- Defect filing & automated repair lifecycle tracking
- Formal Quality Certification Report generation
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import QualityReportRecord
from app.quality.api_test_runner import ApiTestRunner
from app.quality.bug_lifecycle import BugLifecycleManager
from app.quality.code_review_manager import CodeReviewManager
from app.quality.integration_runner import IntegrationRunner
from app.quality.load_test_runner import LoadTestRunner
from app.quality.performance_runner import PerformanceRunner
from app.quality.quality_gate_evaluator import QualityGateEvaluator
from app.quality.regression_manager import RegressionManager
from app.quality.report_generator import ReportGenerator
from app.quality.schemas import (
    GateStatus,
    OverallQualityStatus,
    QualityCertificationReport,
)
from app.quality.security_suite import SecurityBreakerSuite
from app.quality.unit_test_runner import UnitTestRunner

logger = logging.getLogger(__name__)


class QualityEngine:
    """
    Coordinates end-to-end quality validation across the 10 gates.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self.unit_runner = UnitTestRunner()
        self.integration_runner = IntegrationRunner()
        self.api_runner = ApiTestRunner()
        self.security_suite = SecurityBreakerSuite()
        self.perf_runner = PerformanceRunner()
        self.load_runner = LoadTestRunner(db=db)
        self.regression_manager = RegressionManager()
        self.code_review_mgr = CodeReviewManager()
        self.gate_evaluator = QualityGateEvaluator(db=db)
        self.report_generator = ReportGenerator()
        self.bug_manager = BugLifecycleManager(db) if db else None

    async def run_full_quality_audit(
        self,
        project_id: str,
        build_id: str | None = None,
        run_load_test: bool = True,
        max_load_stages: int = 3,  # default 3 stages for fast audit
    ) -> QualityCertificationReport:
        """
        Execute comprehensive product quality engineering suite.
        """
        b_id = build_id or f"build-{uuid.uuid4().hex[:8]}"
        logger.info("Starting Product Quality Audit for project %s (Build: %s)", project_id, b_id)

        # 1. Unit Tests
        unit_summary = self.unit_runner.run_unit_tests(project_id)

        # 2. Integration Tests
        integration_summary = self.integration_runner.run_integration_tests(project_id)

        # 3. API Contract Tests
        api_summary = self.api_runner.run_api_tests(project_id)

        # 4. Security Breaker
        security_summary = self.security_suite.run_security_break(project_id)

        # 5. Performance Benchmarks
        perf_metrics = await self.perf_runner.benchmark_endpoint(
            endpoint="/api/v1/health",
            total_requests=50,
            concurrency=5,
        )

        # 6. Progressive Load Tests
        load_stages = []
        if run_load_test:
            try:
                load_stages = await self.load_runner.run_progressive_load_test(
                    project_id=project_id,
                    test_path="/api/v1/health",
                    max_stages=max_load_stages,
                )
            except Exception as exc:
                logger.warning("Load test encountered an issue on project %s: %s", project_id, exc)

        # 7. Regression Baseline Analysis
        regression_result = self.regression_manager.analyze_regressions(
            project_id=project_id,
            unit_summary=unit_summary,
            integration_summary=integration_summary,
            api_summary=api_summary,
        )

        # 8. Independent Code Review
        code_review = self.code_review_mgr.review_project(project_id)

        # 9. Evaluate 10 Quality Gates
        build_passed = code_review.blockers_count == 0
        build_error = None if build_passed else "Code review reported critical syntax/blocker errors."

        gates = await self.gate_evaluator.evaluate_all_gates(
            project_id=project_id,
            build_id=b_id,
            build_passed=build_passed,
            build_error=build_error,
            unit_summary=unit_summary,
            integration_summary=integration_summary,
            api_summary=api_summary,
            security_summary=security_summary,
            perf_metrics=perf_metrics,
            load_stages=load_stages,
            regression_result=regression_result,
            code_review=code_review,
        )

        # 10. Automatically file defects into Bug Lifecycle if critical defects found
        open_criticals = security_summary.critical_count
        open_highs = security_summary.high_count + unit_summary.failed

        if self.bug_manager:
            for finding in security_summary.findings:
                if finding.severity in ("critical", "high"):
                    try:
                        await self.bug_manager.report_defect(
                            project_id=project_id,
                            title=f"Security: {finding.title}",
                            description=finding.description,
                            severity=finding.severity,
                            affected_files=[finding.affected_file] if finding.affected_file else [],
                            reproduction_steps=finding.reproduction_steps,
                            expected_behavior="Code must pass security scans with zero vulnerabilities.",
                            actual_behavior=f"Found {finding.vector} pattern in code.",
                        )
                    except Exception as exc:
                        logger.debug("Failed logging security defect to DB: %s", exc)

        # 11. Determine Overall Quality Status and Score
        passed_gates = sum(1 for g in gates if g.status == GateStatus.PASSED)
        blocked_gates = sum(1 for g in gates if g.status == GateStatus.BLOCKED)
        failed_gates = sum(1 for g in gates if g.status == GateStatus.FAILED)

        # Score calculation: base 100, weighted by gate passes and test results
        base_score = int((passed_gates / len(gates)) * 60)
        unit_bonus = int((unit_summary.passed / max(1, unit_summary.total_tests)) * 20) if unit_summary.total_tests > 0 else 20
        sec_penalty = (security_summary.critical_count * 20) + (security_summary.high_count * 10)
        quality_score = max(0, min(100, base_score + unit_bonus + int(code_review.score * 0.2) - sec_penalty))

        if blocked_gates > 0 or failed_gates >= 3 or security_summary.critical_count > 0:
            overall_status = OverallQualityStatus.BLOCKED
        elif failed_gates > 0 or passed_gates < 8:
            overall_status = OverallQualityStatus.CONDITIONALLY_APPROVED
        else:
            overall_status = OverallQualityStatus.APPROVED

        report = QualityCertificationReport(
            project_id=project_id,
            build_id=b_id,
            overall_status=overall_status,
            quality_score=quality_score,
            gates=gates,
            unit_summary=unit_summary,
            integration_summary=integration_summary,
            api_summary=api_summary,
            security_summary=security_summary,
            performance_metrics=perf_metrics,
            load_test_stages=load_stages,
            open_critical_bugs=open_criticals,
            open_high_bugs=open_highs,
        )

        # 12. Generate HTML & PDF artifacts
        html_path, pdf_path = self.report_generator.generate_and_save_reports(report)

        # 13. Persist QualityReportRecord in DB
        if self.db:
            try:
                max_conc = max((s.target_concurrency for s in load_stages), default=None)
                rec = QualityReportRecord(
                    project_id=project_id,
                    build_id=b_id,
                    overall_status=overall_status.value,
                    total_tests=unit_summary.total_tests + integration_summary.total_scenarios + api_summary.total_endpoints,
                    passed_tests=unit_summary.passed + integration_summary.passed + api_summary.passed,
                    failed_tests=unit_summary.failed + integration_summary.failed + api_summary.failed,
                    coverage_percent=unit_summary.coverage_percent,
                    critical_bugs_count=open_criticals,
                    high_bugs_count=open_highs,
                    security_findings_count=security_summary.total_vulnerabilities,
                    p95_latency_ms=perf_metrics.p95_latency_ms,
                    max_concurrency_tested=max_conc,
                    summary_markdown=report.summary_markdown,
                    html_report_path=html_path,
                    pdf_report_path=pdf_path,
                )
                self.db.add(rec)
                await self.db.commit()
            except Exception as exc:
                logger.warning("Failed saving QualityReportRecord to DB: %s", exc)

        logger.info(
            "Quality Audit Completed for %s: Status=%s, Score=%d, Gates=%d/%d passed",
            project_id,
            overall_status.value,
            quality_score,
            passed_gates,
            len(gates),
        )

        return report
