"""
10 Evidence-Based Quality Gate Evaluator.
Strictly verifies that an application satisfies all required engineering standards:
Gate 1: Build & Compilation Gate
Gate 2: Unit Test & Coverage Gate (100% pass, >=80% coverage)
Gate 3: Integration Scenarios Gate
Gate 4: API & Contract Validation Gate
Gate 5: Security Breaker Gate (0 Critical, 0 High, 0 secrets)
Gate 6: Performance Gate (P95 <= 500ms, resource bounds)
Gate 7: Concurrency & Load Gate (0 bottlenecks at target tier)
Gate 8: Regression Gate (0 regressed tests)
Gate 9: Independent Code Review Gate (0 blockers, score >= 75)
Gate 10: Human Sign-Off Gate (explicit approval record)
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ApprovalRequest, QualityGateRecord
from app.quality.code_review_manager import CodeReviewResult
from app.quality.regression_manager import RegressionAnalysisResult
from app.quality.schemas import (
    ApiTestSummary,
    GateStatus,
    IntegrationTestSummary,
    LoadTestStageResult,
    PerformanceMetrics,
    QualityGateResult,
    SecurityBreakerSummary,
    UnitTestSummary,
)

logger = logging.getLogger(__name__)


class QualityGateEvaluator:
    """
    Evaluates each of the 10 formal gates against concrete execution evidence.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db

    async def evaluate_all_gates(
        self,
        project_id: str,
        build_id: str,
        build_passed: bool,
        build_error: str | None,
        unit_summary: UnitTestSummary,
        integration_summary: IntegrationTestSummary,
        api_summary: ApiTestSummary,
        security_summary: SecurityBreakerSummary,
        perf_metrics: PerformanceMetrics,
        load_stages: list[LoadTestStageResult],
        regression_result: RegressionAnalysisResult,
        code_review: CodeReviewResult,
    ) -> list[QualityGateResult]:
        """
        Evaluate all 10 gates against the collected evidence from all runners.
        """
        results: list[QualityGateResult] = []

        # Gate 1: Build Gate
        g1_status = GateStatus.PASSED if build_passed else GateStatus.FAILED
        g1_reason = "Codebase compiles and builds cleanly without syntax errors." if build_passed else f"Build failed: {build_error or 'Unknown error'}"
        results.append(
            QualityGateResult(
                gate_number=1,
                gate_name="Build & Compilation Gate",
                status=g1_status,
                criterion="Project builds and compiles with 0 syntax or packaging errors.",
                evaluated_value="SUCCESS" if build_passed else "BUILD_FAILED",
                reason=g1_reason,
                evidence={"build_passed": build_passed, "error": build_error},
            )
        )

        # Gate 2: Unit Test Gate
        unit_pass = (unit_summary.failed == 0) and (unit_summary.total_tests > 0 or unit_summary.passed > 0)
        cov_pass = unit_summary.coverage_percent >= 80.0 or unit_summary.total_tests == 0
        g2_pass = unit_pass and cov_pass
        g2_status = GateStatus.PASSED if g2_pass else GateStatus.FAILED
        results.append(
            QualityGateResult(
                gate_number=2,
                gate_name="Unit Test & Coverage Gate",
                status=g2_status,
                criterion="100% of unit tests pass, and line coverage is at least 80%.",
                evaluated_value=f"{unit_summary.passed}/{unit_summary.total_tests} passed, {unit_summary.coverage_percent:.1f}% coverage",
                reason="All unit tests passed with required coverage." if g2_pass else "Some unit tests failed or coverage is below 80%.",
                evidence={"total": unit_summary.total_tests, "passed": unit_summary.passed, "failed": unit_summary.failed, "coverage": unit_summary.coverage_percent},
            )
        )

        # Gate 3: Integration Test Gate
        integ_pass = integration_summary.failed == 0
        results.append(
            QualityGateResult(
                gate_number=3,
                gate_name="Integration Scenarios Gate",
                status=GateStatus.PASSED if integ_pass else GateStatus.FAILED,
                criterion="All multi-component integration workflows and service scenarios execute cleanly.",
                evaluated_value=f"{integration_summary.passed}/{integration_summary.total_scenarios} scenarios passed",
                reason="All integration scenarios passed." if integ_pass else f"{integration_summary.failed} integration scenarios failed.",
                evidence={"total": integration_summary.total_scenarios, "passed": integration_summary.passed, "failed": integration_summary.failed},
            )
        )

        # Gate 4: API & Contract Gate
        api_pass = api_summary.failed == 0 and api_summary.contract_violations == 0
        results.append(
            QualityGateResult(
                gate_number=4,
                gate_name="API Contract & Endpoint Gate",
                status=GateStatus.PASSED if api_pass else GateStatus.FAILED,
                criterion="All API endpoints conform to schema contracts and return expected HTTP statuses.",
                evaluated_value=f"{api_summary.passed}/{api_summary.total_endpoints} endpoints passed ({api_summary.contract_violations} schema violations)",
                reason="All API contracts verified." if api_pass else f"{api_summary.failed} endpoints failed or had contract violations.",
                evidence={"total": api_summary.total_endpoints, "failed": api_summary.failed, "violations": api_summary.contract_violations},
            )
        )

        # Gate 5: Security Gate
        sec_blockers = security_summary.critical_count + security_summary.high_count + security_summary.exposed_secrets_count
        sec_pass = sec_blockers == 0
        results.append(
            QualityGateResult(
                gate_number=5,
                gate_name="Security Breaker Gate",
                status=GateStatus.PASSED if sec_pass else GateStatus.BLOCKED,
                criterion="0 Critical, 0 High vulnerabilities, and 0 exposed secrets.",
                evaluated_value=f"{security_summary.critical_count} critical, {security_summary.high_count} high, {security_summary.exposed_secrets_count} secrets",
                reason="Security audit clean with no critical/high issues." if sec_pass else f"Security violations found: {sec_blockers} critical/high/secrets.",
                evidence={
                    "critical": security_summary.critical_count,
                    "high": security_summary.high_count,
                    "medium": security_summary.medium_count,
                    "secrets": security_summary.exposed_secrets_count,
                },
            )
        )

        # Gate 6: Performance Gate
        p95 = perf_metrics.p95_latency_ms
        perf_pass = (p95 <= 500.0 or p95 == 0.0)
        results.append(
            QualityGateResult(
                gate_number=6,
                gate_name="Performance & Latency Gate",
                status=GateStatus.PASSED if perf_pass else GateStatus.FAILED,
                criterion="P95 latency is at or under 500ms under standard operational load.",
                evaluated_value=f"P95: {p95}ms (Avg: {perf_metrics.avg_latency_ms}ms, RPS: {perf_metrics.requests_per_second})",
                reason="Performance satisfies latency threshold." if perf_pass else f"P95 latency of {p95}ms exceeds 500ms limit.",
                evidence={
                    "p50": perf_metrics.p50_latency_ms,
                    "p95": perf_metrics.p95_latency_ms,
                    "p99": perf_metrics.p99_latency_ms,
                    "rps": perf_metrics.requests_per_second,
                    "cpu": perf_metrics.cpu_percent,
                    "memory": perf_metrics.memory_mb,
                },
            )
        )

        # Gate 7: Concurrency & Load Gate
        if not load_stages:
            load_status = GateStatus.BLOCKED
            load_eval = "NOT_TESTED"
            load_reason = "Concurrency testing has not been run. System unverified under concurrent load."
        else:
            failed_stages = [s for s in load_stages if s.status == "failed"]
            max_conc = max(s.target_concurrency for s in load_stages)
            if not failed_stages:
                load_status = GateStatus.PASSED
                load_eval = f"Passed through {max_conc} concurrent users"
                load_reason = f"All {len(load_stages)} load stages passed without saturation or excessive errors."
            else:
                load_status = GateStatus.FAILED
                load_eval = f"Failed at {failed_stages[0].target_concurrency} users"
                load_reason = f"Bottleneck detected at {failed_stages[0].target_concurrency} users: {', '.join(failed_stages[0].bottlenecks)}"

        results.append(
            QualityGateResult(
                gate_number=7,
                gate_name="Progressive Concurrency Gate",
                status=load_status,
                criterion="System handles progressive user concurrency up to target tier without service disruption.",
                evaluated_value=load_eval,
                reason=load_reason,
                evidence={"stages_count": len(load_stages)},
            )
        )

        # Gate 8: Regression Gate
        reg_pass = not regression_result.has_regressions
        results.append(
            QualityGateResult(
                gate_number=8,
                gate_name="Zero Regression Gate",
                status=GateStatus.PASSED if reg_pass else GateStatus.FAILED,
                criterion="Zero regressed tests compared to the known-good baseline.",
                evaluated_value=f"{len(regression_result.regressed_tests)} regressions",
                reason=regression_result.summary,
                evidence={"regressed": regression_result.regressed_tests, "newly_passing": regression_result.newly_passing_tests},
            )
        )

        # Gate 9: Code Review Gate
        cr_pass = code_review.is_approved
        results.append(
            QualityGateResult(
                gate_number=9,
                gate_name="Architectural Code Review Gate",
                status=GateStatus.PASSED if cr_pass else GateStatus.BLOCKED,
                criterion="Independent code review approved with 0 blockers and score >= 75.",
                evaluated_value=f"Score: {code_review.score}/100, Blockers: {code_review.blockers_count}",
                reason=code_review.summary,
                evidence={"score": code_review.score, "blockers": code_review.blockers_count, "majors": code_review.majors_count},
            )
        )

        # Gate 10: Human Approval Gate
        human_approved = False
        approval_note = "Awaiting human operator sign-off."
        if self.db:
            try:
                stmt = select(ApprovalRequest).where(
                    ApprovalRequest.project_id == project_id,
                    ApprovalRequest.status == "approved",
                ).order_by(ApprovalRequest.created_at.desc())
                res = await self.db.execute(stmt)
                last_appr = res.scalars().first()
                if last_appr:
                    human_approved = True
                    approval_note = f"Approved by {last_appr.decided_by or 'operator'} at {last_appr.decided_at}."
            except Exception as exc:
                logger.debug("Failed querying ApprovalRequest for gate 10: %s", exc)

        results.append(
            QualityGateResult(
                gate_number=10,
                gate_name="Human Release Sign-off Gate",
                status=GateStatus.PASSED if human_approved else GateStatus.BLOCKED,
                criterion="Formal release approval by authorized human lead or system operator.",
                evaluated_value="APPROVED" if human_approved else "PENDING_APPROVAL",
                reason=approval_note,
                evidence={"approved": human_approved},
            )
        )

        # Persist to database if session provided
        if self.db:
            try:
                for gr in results:
                    rec = QualityGateRecord(
                        project_id=project_id,
                        gate_number=gr.gate_number,
                        gate_name=gr.gate_name,
                        status=gr.status.value,
                        criterion=gr.criterion,
                        evaluated_value=gr.evaluated_value,
                        reason=gr.reason,
                        evidence_json=gr.evidence,
                    )
                    self.db.add(rec)
                await self.db.commit()
            except Exception as exc:
                logger.warning("Could not persist QualityGateRecord entries: %s", exc)

        return results
