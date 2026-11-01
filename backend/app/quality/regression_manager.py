"""
Automated Regression Testing and Baseline Tracking Manager.
Compares current test execution outputs against previous established baselines
to immediately flag regression defects (tests that were passing and now fail).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.quality.schemas import (
    ApiTestSummary,
    IntegrationTestSummary,
    TestStatus,
    UnitTestSummary,
)
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


@dataclass
class RegressionAnalysisResult:
    """Outcome of comparing a test suite execution against the baseline."""

    has_regressions: bool
    regressed_tests: list[str]  # Test names/IDs that flipped from PASS to FAIL
    newly_passing_tests: list[str]
    total_baseline_tests: int
    current_total_tests: int
    summary: str


class RegressionManager:
    """
    Manages persistence of known-good test execution snapshots and diffing for regressions.
    """

    BASELINE_FILENAME = "test_baseline.json"

    def __init__(self) -> None:
        self.workspace = get_workspace_service()

    def _get_baseline_path(self, project_id: str) -> str:
        return f".agentforge/{self.BASELINE_FILENAME}"

    def load_baseline(self, project_id: str) -> dict[str, Any] | None:
        """Read existing baseline snapshot from project workspace if present."""
        rel_path = self._get_baseline_path(project_id)
        try:
            content = self.workspace.read_file(project_id, rel_path)
            return json.loads(content)
        except Exception:
            return None

    def save_baseline(
        self,
        project_id: str,
        unit_summary: UnitTestSummary,
        integration_summary: IntegrationTestSummary,
        api_summary: ApiTestSummary,
    ) -> None:
        """Persist current test outcomes as the approved known-good baseline."""
        passing_tests: list[str] = []
        for t in unit_summary.test_cases:
            if t.status == TestStatus.PASSED:
                passing_tests.append(t.name)
        for s in integration_summary.scenarios:
            if s.status == TestStatus.PASSED:
                passing_tests.append(s.name)
        for ep in api_summary.endpoints:
            if ep.passed:
                passing_tests.append(f"{ep.method} {ep.path}")

        snapshot = {
            "project_id": project_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "passing_tests": sorted(passing_tests),
            "unit_passed": unit_summary.passed,
            "integration_passed": integration_summary.passed,
            "api_passed": api_summary.passed,
        }
        rel_path = self._get_baseline_path(project_id)
        self.workspace.write_file(project_id, rel_path, json.dumps(snapshot, indent=2))
        logger.info("Saved test baseline with %d passing tests for %s", len(passing_tests), project_id)

    def analyze_regressions(
        self,
        project_id: str,
        unit_summary: UnitTestSummary,
        integration_summary: IntegrationTestSummary,
        api_summary: ApiTestSummary,
    ) -> RegressionAnalysisResult:
        """
        Compare current results to saved baseline to detect regressions.
        """
        baseline = self.load_baseline(project_id)
        if not baseline:
            logger.info("No baseline found for project %s. Establishing current as initial.", project_id)
            self.save_baseline(project_id, unit_summary, integration_summary, api_summary)
            return RegressionAnalysisResult(
                has_regressions=False,
                regressed_tests=[],
                newly_passing_tests=[],
                total_baseline_tests=unit_summary.passed + integration_summary.passed + api_summary.passed,
                current_total_tests=unit_summary.total_tests + integration_summary.total_scenarios + api_summary.total_endpoints,
                summary="Initial test run established as baseline. No prior regressions.",
            )

        baseline_passing: set[str] = set(baseline.get("passing_tests", []))

        # Current failing/passed sets
        current_failed: set[str] = set()
        current_passed: set[str] = set()

        for t in unit_summary.test_cases:
            if t.status == TestStatus.PASSED:
                current_passed.add(t.name)
            elif t.status == TestStatus.FAILED:
                current_failed.add(t.name)

        for s in integration_summary.scenarios:
            if s.status == TestStatus.PASSED:
                current_passed.add(s.name)
            elif s.status == TestStatus.FAILED:
                current_failed.add(s.name)

        for ep in api_summary.endpoints:
            key = f"{ep.method} {ep.path}"
            if ep.passed:
                current_passed.add(key)
            else:
                current_failed.add(key)

        # Regressions: tests that were in baseline_passing but are now in current_failed
        regressed = sorted(baseline_passing.intersection(current_failed))
        newly_passing = sorted(current_passed - baseline_passing)

        has_reg = len(regressed) > 0
        summary = (
            f"Regression check: {len(regressed)} regressions detected out of {len(baseline_passing)} baseline tests."
            if has_reg
            else f"Clean run: 0 regressions detected across {len(baseline_passing)} baseline tests."
        )

        return RegressionAnalysisResult(
            has_regressions=has_reg,
            regressed_tests=regressed,
            newly_passing_tests=newly_passing,
            total_baseline_tests=len(baseline_passing),
            current_total_tests=len(current_passed) + len(current_failed),
            summary=summary,
        )
