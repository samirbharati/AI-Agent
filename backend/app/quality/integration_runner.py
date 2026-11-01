"""
Cross-Component Integration Testing Runner.
"""

from __future__ import annotations

import logging

from app.quality.schemas import IntegrationTestSummary, TestCaseResult, TestStatus, TestType
from app.services.runner import ExecutionRunner, get_execution_runner
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


class IntegrationRunner:
    """
    Executes integration tests testing cross-module workflows,
    database transactional consistency, and agent orchestration channels.
    """

    def __init__(self, runner: ExecutionRunner | None = None) -> None:
        self.runner = runner or get_execution_runner()
        self.workspace = get_workspace_service()

    def run_integration_tests(
        self, project_id: str, timeout: int = 120
    ) -> IntegrationTestSummary:
        """
        Execute integration test suite.
        Targeting files matching: test_*integration*.py or tests/integration/**
        """
        ws_path = self.workspace.get_project_dir(project_id)
        integration_files = list(ws_path.glob("**/test_*integration*.py")) + list(
            ws_path.glob("tests/integration/**/*.py")
        )

        if not integration_files:
            return IntegrationTestSummary(
                total_scenarios=0,
                passed=0,
                failed=0,
                duration_seconds=0.0,
                scenarios=[],
            )

        cmd = ["pytest", "-v", "-m", "integration"]
        res = self.runner.run_command(project_id, cmd, timeout=timeout)

        # If markers weren't used, fall back to running the specific integration files
        if res.exit_code == 5 or ("no tests ran" in res.stdout.lower()):
            file_args = [str(f.relative_to(ws_path)) for f in integration_files]
            res = self.runner.run_command(project_id, ["pytest", "-v"] + file_args, timeout=timeout)

        scenarios: list[TestCaseResult] = []

        for idx, f in enumerate(integration_files, 1):
            passed = res.success
            scenarios.append(
                TestCaseResult(
                    id=f"int-scenario-{idx}",
                    name=f"Integration Scenario: {f.name}",
                    test_type=TestType.INTEGRATION,
                    status=TestStatus.PASSED if passed else TestStatus.FAILED,
                    duration_ms=round(res.duration_seconds * 1000 / len(integration_files), 1),
                    file_path=str(f.relative_to(ws_path)),
                    error_message=None if passed else "Integration scenario failed verification.",
                )
            )

        passed_count = sum(1 for s in scenarios if s.status == TestStatus.PASSED)
        failed_count = len(scenarios) - passed_count

        return IntegrationTestSummary(
            total_scenarios=len(scenarios),
            passed=passed_count,
            failed=failed_count,
            duration_seconds=res.duration_seconds,
            scenarios=scenarios,
        )


_integration_runner_instance: IntegrationRunner | None = None


def get_integration_runner() -> IntegrationRunner:
    global _integration_runner_instance
    if _integration_runner_instance is None:
        _integration_runner_instance = IntegrationRunner()
    return _integration_runner_instance

