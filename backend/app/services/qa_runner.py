"""
QA and Automated Test Execution Runner.

Executes tests within the project workspace, parses results, distinguishes
between passed, failed, blocked, and not executed, and generates structured
bug reports for the Developer repair loop.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass
from typing import Any

from app.services.runner import get_execution_runner
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


@dataclass
class BugReport:
    """A structured defect detected during automated testing."""

    id: str
    title: str
    severity: str  # "critical" | "high" | "medium" | "low"
    test_name: str | None
    steps_to_reproduce: list[str]
    expected_result: str
    actual_result: str
    stacktrace: str | None = None


@dataclass
class QATestSuiteResult:
    """Complete summary of a test execution run."""

    project_id: str
    passed: bool
    status: str  # "passed" | "failed" | "not_executed" | "inconclusive"
    total_tests: int
    passed_count: int
    failed_count: int
    blocked_count: int
    not_executed_count: int
    duration_seconds: float
    bugs: list[dict[str, Any]]
    raw_stdout: str
    raw_stderr: str


class QARunnerService:
    """
    Executes automated tests and parses results for verification and bug detection.
    """

    def __init__(self) -> None:
        self.workspace_service = get_workspace_service()
        self.runner = get_execution_runner()

    def discover_test_files(self, project_id: str) -> list[str]:
        """Find all test files within the project workspace."""
        files = self.workspace_service.list_files(project_id)
        test_patterns = (r"(?:^|/)test_[^/]+\.py$", r"(?:^|/)[^/]+_test\.py$")
        test_files: list[str] = []

        for f in files:
            if any(re.search(pat, f.path) for pat in test_patterns):
                test_files.append(f.path)

        return test_files

    def run_tests(self, project_id: str, timeout: int = 60) -> QATestSuiteResult:
        """
        Execute automated test suite for the project and parse results.

        Never marks a test suite as passing if required tests were not executed.
        """
        test_files = self.discover_test_files(project_id)

        # If no test files are present in the project
        if not test_files:
            return QATestSuiteResult(
                project_id=project_id,
                passed=False,
                status="not_executed",
                total_tests=0,
                passed_count=0,
                failed_count=0,
                blocked_count=0,
                not_executed_count=1,
                duration_seconds=0.0,
                bugs=[
                    asdict(
                        BugReport(
                            id="BUG-NO-TESTS",
                            title="No automated tests found in workspace",
                            severity="high",
                            test_name=None,
                            steps_to_reproduce=[
                                "Search workspace for test_*.py or *_test.py files"
                            ],
                            expected_result="Project should include unit test fixtures for implemented modules",
                            actual_result="0 test files discovered",
                            stacktrace=None,
                        )
                    )
                ],
                raw_stdout="",
                raw_stderr="No test files discovered in project workspace.",
            )

        # Run pytest via ExecutionRunner
        exec_result = self.runner.run_pytest(project_id, timeout=timeout)

        # Parse pytest output
        combined_output = f"{exec_result.stdout}\n{exec_result.stderr}"
        parsed = self._parse_pytest_output(combined_output)

        bugs: list[dict[str, Any]] = []
        for idx, failure in enumerate(parsed["failures"], start=1):
            bugs.append(
                asdict(
                    BugReport(
                        id=f"BUG-{idx:03d}",
                        title=f"Test failure: {failure['test_name']}",
                        severity="high",
                        test_name=failure["test_name"],
                        steps_to_reproduce=[f"Run pytest {failure['test_name']}"],
                        expected_result="Test assertion should pass cleanly",
                        actual_result=failure.get("error_message", "Test assertion failed"),
                        stacktrace=failure.get("stacktrace"),
                    )
                )
            )

        # If command timed out
        if exec_result.timed_out:
            bugs.append(
                asdict(
                    BugReport(
                        id="BUG-TIMEOUT",
                        title=f"Test suite execution timed out after {timeout}s",
                        severity="critical",
                        test_name=None,
                        steps_to_reproduce=["Execute test suite"],
                        expected_result="Tests complete within bounded timeout",
                        actual_result=f"Execution timed out after {timeout} seconds",
                        stacktrace=exec_result.stderr,
                    )
                )
            )

        total = parsed["passed"] + parsed["failed"]
        all_passed = exec_result.success and parsed["failed"] == 0 and parsed["passed"] > 0

        status = "passed" if all_passed else "failed"

        return QATestSuiteResult(
            project_id=project_id,
            passed=all_passed,
            status=status,
            total_tests=total,
            passed_count=parsed["passed"],
            failed_count=parsed["failed"],
            blocked_count=1 if exec_result.timed_out else 0,
            not_executed_count=0,
            duration_seconds=exec_result.duration_seconds,
            bugs=bugs,
            raw_stdout=exec_result.stdout,
            raw_stderr=exec_result.stderr,
        )

    def _parse_pytest_output(self, output: str) -> dict[str, Any]:
        """Parse pytest stdout to extract counts and failure stacktraces."""
        passed = 0
        failed = 0

        # Look for summary lines like: "5 passed, 1 failed in 0.5s" or "3 passed in 0.2s"
        passed_match = re.search(r"(\d+)\s+passed", output)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed = int(failed_match.group(1))

        # Extract failure blocks
        failures: list[dict[str, Any]] = []

        # 1. Match from FAILURES section headers: "___ test_name ___"
        failure_headers = re.findall(r"_{3,}\s+(.+?)\s+_{3,}", output)
        for h in failure_headers:
            name = h.strip()
            if name != "FAILURES":
                failures.append(
                    {
                        "test_name": name,
                        "error_message": f"Failure in test: {name}",
                        "stacktrace": None,
                    }
                )

        # 2. Match from short summary lines: "FAILED tests/test_fail.py::test_intentional_failure - ..."
        if not failures:
            for match in re.finditer(r"^FAILED\s+([^\s-]+)", output, re.MULTILINE):
                t_name = match.group(1).strip()
                failures.append(
                    {
                        "test_name": t_name,
                        "error_message": f"Failure in test: {t_name}",
                        "stacktrace": None,
                    }
                )

        return {
            "passed": passed,
            "failed": failed,
            "failures": failures,
        }


# Global singleton
_qa_runner: QARunnerService | None = None


def get_qa_runner() -> QARunnerService:
    global _qa_runner
    if _qa_runner is None:
        _qa_runner = QARunnerService()
    return _qa_runner
