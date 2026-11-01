"""
Test-Driven Development (TDD) Red-Green-Refactor Lifecycle Manager.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.runner import ExecutionRunner, get_execution_runner
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


@dataclass
class TDDPhaseResult:
    phase: str  # "RED" | "GREEN" | "REFACTOR"
    passed: bool
    expected_failure_confirmed: bool = False
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    summary: str = ""


class TDDRunner:
    """
    Coordinates strict Red -> Green -> Refactor cycles:
    1. RED: Write test first; verify it fails for expected reason.
    2. GREEN: Implement minimum code; verify test passes.
    3. REFACTOR: Refactor code; verify test still passes.
    """

    def __init__(self, runner: ExecutionRunner | None = None) -> None:
        self.runner = runner or get_execution_runner()
        self.workspace = get_workspace_service()

    def run_red_phase(self, project_id: str, test_file_rel: str) -> TDDPhaseResult:
        """
        Execute newly written test before implementation.
        Must fail to confirm test validity (RED).
        """
        cmd = ["pytest", "-v", test_file_rel]
        res = self.runner.run_command(project_id, cmd, timeout=30)

        # RED phase expects failure (exit code != 0)
        expected_failure = not res.success
        summary = (
            "Confirmed RED phase: Test failed as expected prior to implementation."
            if expected_failure
            else "TDD Violation: Test passed unexpectedly before implementation was provided!"
        )

        return TDDPhaseResult(
            phase="RED",
            passed=expected_failure,
            expected_failure_confirmed=expected_failure,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_seconds=res.duration_seconds,
            summary=summary,
        )

    def run_green_phase(self, project_id: str, test_file_rel: str) -> TDDPhaseResult:
        """
        Execute test after implementation is written.
        Must pass (GREEN).
        """
        cmd = ["pytest", "-v", test_file_rel]
        res = self.runner.run_command(project_id, cmd, timeout=30)

        passed = res.success
        summary = (
            "Confirmed GREEN phase: Implementation successfully satisfied the test criteria."
            if passed
            else f"GREEN phase failed: Implementation did not satisfy the test. Exit code {res.exit_code}."
        )

        return TDDPhaseResult(
            phase="GREEN",
            passed=passed,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_seconds=res.duration_seconds,
            summary=summary,
        )

    def run_refactor_phase(self, project_id: str, test_file_rel: str) -> TDDPhaseResult:
        """
        Execute test suite after code cleanup and optimization.
        Must still pass (REFACTOR).
        """
        cmd = ["pytest", "-v", test_file_rel]
        res = self.runner.run_command(project_id, cmd, timeout=30)

        passed = res.success
        summary = (
            "Confirmed REFACTOR phase: Refactored code preserved 100% test pass rate."
            if passed
            else f"REFACTOR regression: Refactored code broke existing test cases. Exit code {res.exit_code}."
        )

        return TDDPhaseResult(
            phase="REFACTOR",
            passed=passed,
            exit_code=res.exit_code,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_seconds=res.duration_seconds,
            summary=summary,
        )


_tdd_runner_instance: TDDRunner | None = None


def get_tdd_runner() -> TDDRunner:
    global _tdd_runner_instance
    if _tdd_runner_instance is None:
        _tdd_runner_instance = TDDRunner()
    return _tdd_runner_instance

