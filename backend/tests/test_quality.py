"""
Comprehensive test suite for AgentForge Product Quality Engineering System.
Tests TDD runner, unit/integration/api runners, security breaker,
performance & load testing, regression manager, code review, 10 quality gates,
defect lifecycle, and certification report generation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.db_models import Bug
from app.quality.api_test_runner import ApiTestRunner
from app.quality.bug_lifecycle import BugLifecycleManager
from app.quality.code_review_manager import CodeReviewManager
from app.quality.integration_runner import IntegrationRunner
from app.quality.load_test_runner import LoadTestRunner, calculate_percentile
from app.quality.performance_runner import PerformanceRunner
from app.quality.quality_engine import QualityEngine
from app.quality.quality_gate_evaluator import QualityGateEvaluator
from app.quality.regression_manager import RegressionAnalysisResult, RegressionManager
from app.quality.report_generator import (
    ReportGenerator,
)
from app.quality.schemas import (
    ApiTestSummary,
    GateStatus,
    IntegrationTestSummary,
    LoadTestStageResult,
    OverallQualityStatus,
    PerformanceMetrics,
    QualityCertificationReport,
    QualityGateResult,
    SecurityBreakerSummary,
    TestCaseResult,
    TestStatus,
    TestType,
    UnitTestSummary,
)
from app.quality.security_suite import SecurityBreakerSuite
from app.quality.tdd_runner import TDDRunner
from app.quality.unit_test_runner import UnitTestRunner
from app.services.runner import ExecutionResult

TestCaseResult.__test__ = False  # type: ignore[attr-defined]
TestStatus.__test__ = False  # type: ignore[attr-defined]
TestType.__test__ = False  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Percentile Helper Test
# ---------------------------------------------------------------------------

def test_calculate_percentile():
    data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    assert calculate_percentile(data, 50) == 55.0
    assert calculate_percentile(data, 90) == 91.0
    assert calculate_percentile([], 50) == 0.0


# ---------------------------------------------------------------------------
# TDD Runner Tests
# ---------------------------------------------------------------------------

def test_tdd_runner_red_phase():
    runner = TDDRunner()
    exec_res = ExecutionResult(
        command=["pytest"],
        exit_code=1,
        stdout="AssertionError: Expected 200 but got 404",
        stderr="",
        duration_seconds=0.1,
    )
    with patch.object(runner.runner, "run_command", return_value=exec_res):
        res = runner.run_red_phase("test-proj", "tests/test_feature.py")
        assert res.phase == "RED"
        assert res.passed is True  # In RED phase, failure is expected!
        assert "AssertionError" in res.stdout


def test_tdd_runner_green_phase():
    runner = TDDRunner()
    exec_res = ExecutionResult(
        command=["pytest"],
        exit_code=0,
        stdout="1 passed in 0.05s",
        stderr="",
        duration_seconds=0.1,
    )
    with patch.object(runner.runner, "run_command", return_value=exec_res):
        res = runner.run_green_phase("test-proj", "tests/test_feature.py")
        assert res.phase == "GREEN"
        assert res.passed is True


# ---------------------------------------------------------------------------
# Unit Test Runner Tests
# ---------------------------------------------------------------------------

def test_unit_test_runner_parsing():
    runner = UnitTestRunner()
    mock_pytest_output = (
        "tests/test_one.py::test_alpha PASSED\n"
        "tests/test_one.py::test_beta FAILED\n"
        "TOTAL 100 15 85%\n"
    )
    exec_res = ExecutionResult(
        command=["pytest"],
        exit_code=1,
        stdout=mock_pytest_output,
        stderr="",
        duration_seconds=0.2,
    )
    mock_ws = MagicMock()
    mock_test_file = MagicMock()
    mock_ws.glob.return_value = [mock_test_file]

    with patch.object(runner.workspace, "get_project_dir", return_value=mock_ws), \
         patch.object(runner.runner, "run_command", return_value=exec_res):
        summary = runner.run_unit_tests("test-proj")
        assert summary.total_tests == 2
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.coverage_percent == 85.0


# ---------------------------------------------------------------------------
# Integration Runner Tests
# ---------------------------------------------------------------------------

def test_integration_runner():
    runner = IntegrationRunner()
    mock_output = "tests/integration/test_flow.py::test_full_checkout PASSED\n"
    exec_res = ExecutionResult(
        command=["pytest"],
        exit_code=0,
        stdout=mock_output,
        stderr="",
        duration_seconds=0.2,
    )
    mock_ws = MagicMock()
    mock_test_file = MagicMock()
    mock_ws.glob.side_effect = [[mock_test_file], []]

    with patch.object(runner.workspace, "get_project_dir", return_value=mock_ws), \
         patch.object(runner.runner, "run_command", return_value=exec_res):
        summary = runner.run_integration_tests("test-proj")
        assert summary.passed == 1
        assert summary.failed == 0


# ---------------------------------------------------------------------------
# API Test Runner Tests
# ---------------------------------------------------------------------------

def test_api_test_runner_endpoint_discovery():
    runner = ApiTestRunner()
    mock_file = MagicMock()
    mock_file.read_text.return_value = """
@router.get("/users")
def list_users():
    return []

@router.post("/users")
def create_user():
    return {}
"""
    mock_file.relative_to.return_value = "app/api/endpoints.py"
    mock_ws = MagicMock()
    mock_ws.glob.return_value = [mock_file]

    with patch.object(runner.workspace, "get_project_dir", return_value=mock_ws):
        endpoints = runner.discover_api_endpoints("test-proj")
        assert len(endpoints) == 2
        assert any(e["path"] == "/users" and e["method"] == "GET" for e in endpoints)
        assert any(e["path"] == "/users" and e["method"] == "POST" for e in endpoints)


# ---------------------------------------------------------------------------
# Security Breaker Tests
# ---------------------------------------------------------------------------

def test_security_breaker_suite():
    breaker = SecurityBreakerSuite()
    with patch.object(breaker.scanner_service, "scan_project", return_value={
        "findings": [
            {
                "rule_id": "SEC-001",
                "title": "AWS Key Leaked",
                "severity": "critical",
                "file_path": "config.py",
                "line_number": 5,
                "description": "Leaked AWS key",
                "remediation": "Remove key",
            }
        ]
    }), patch.object(breaker.workspace, "list_files", return_value=[]):
        summary = breaker.run_security_break("test-proj")
        assert summary.total_vulnerabilities == 1
        assert summary.critical_count == 1
        assert summary.exposed_secrets_count == 1
        assert summary.findings[0].vector == "secrets"


# ---------------------------------------------------------------------------
# Performance & Load Test Runner Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_performance_runner_metrics():
    runner = PerformanceRunner(base_url="http://mock-service")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        metrics = await runner.benchmark_endpoint(endpoint="/test", total_requests=10, concurrency=2)
        assert metrics.total_requests == 10
        assert metrics.requests_per_second > 0


@pytest.mark.asyncio
async def test_load_test_runner_stages():
    runner = LoadTestRunner(base_url="http://mock-service")
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        stages = await runner.run_progressive_load_test("test-proj", max_stages=2)
        assert len(stages) == 2
        assert stages[0].stage == 1
        assert stages[0].status == "passed"


# ---------------------------------------------------------------------------
# Regression Manager Tests
# ---------------------------------------------------------------------------

def test_regression_manager_detection():
    reg_mgr = RegressionManager()
    unit_summary = UnitTestSummary(
        total_tests=2,
        passed=1,
        failed=1,
        test_cases=[
            TestCaseResult(id="1", name="test_login", test_type=TestType.UNIT, status=TestStatus.FAILED),
            TestCaseResult(id="2", name="test_signup", test_type=TestType.UNIT, status=TestStatus.PASSED),
        ],
    )
    integ_summary = IntegrationTestSummary()
    api_summary = ApiTestSummary()

    # Mock baseline where test_login had passed
    baseline_data = {
        "project_id": "test-proj",
        "passing_tests": ["test_login", "test_signup"],
    }

    with patch.object(reg_mgr, "load_baseline", return_value=baseline_data):
        result = reg_mgr.analyze_regressions("test-proj", unit_summary, integ_summary, api_summary)
        assert result.has_regressions is True
        assert "test_login" in result.regressed_tests


# ---------------------------------------------------------------------------
# Code Review Manager Tests
# ---------------------------------------------------------------------------

def test_code_review_manager_ast():
    reviewer = CodeReviewManager()
    mock_file = MagicMock()
    mock_file.path = "app/service.py"
    bad_code = """
def bare_except_func():
    try:
        x = 1 / 0
    except:
        pass
"""
    with patch.object(reviewer.workspace, "list_files", return_value=[mock_file]), \
         patch.object(reviewer.workspace, "read_file", return_value=bad_code):
        res = reviewer.review_project("test-proj")
        assert res.majors_count >= 1
        assert any(f.rule_id == "ERR-001" for f in res.findings)


# ---------------------------------------------------------------------------
# Quality Gate Evaluator Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quality_gate_evaluator_all_pass():
    evaluator = QualityGateEvaluator(db=None)

    unit = UnitTestSummary(total_tests=10, passed=10, failed=0, coverage_percent=88.0)
    integ = IntegrationTestSummary(total_scenarios=2, passed=2, failed=0)
    api = ApiTestSummary(total_endpoints=5, passed=5, failed=0, contract_violations=0)
    sec = SecurityBreakerSummary(total_vulnerabilities=0, critical_count=0, high_count=0)
    perf = PerformanceMetrics(p95_latency_ms=120.0, requests_per_second=80.0)
    load = [LoadTestStageResult(
        stage=1, target_concurrency=10, actual_concurrency=10, total_requests=50,
        successful_requests=50, failed_requests=0, requests_per_second=50.0,
        avg_latency_ms=15.0, p95_latency_ms=25.0, p99_latency_ms=30.0, status="passed"
    )]
    reg = RegressionAnalysisResult(has_regressions=False, regressed_tests=[], newly_passing_tests=[], total_baseline_tests=17, current_total_tests=17, summary="Clean")
    cr = MagicMock()
    cr.is_approved = True
    cr.score = 90
    cr.blockers_count = 0
    cr.summary = "Clean code"

    gates = await evaluator.evaluate_all_gates(
        project_id="test-proj",
        build_id="b-1",
        build_passed=True,
        build_error=None,
        unit_summary=unit,
        integration_summary=integ,
        api_summary=api,
        security_summary=sec,
        perf_metrics=perf,
        load_stages=load,
        regression_result=reg,
        code_review=cr,
    )

    assert len(gates) == 10
    assert gates[0].status == GateStatus.PASSED  # Build
    assert gates[1].status == GateStatus.PASSED  # Unit Test
    assert gates[2].status == GateStatus.PASSED  # Integration
    assert gates[3].status == GateStatus.PASSED  # API Contract
    assert gates[4].status == GateStatus.PASSED  # Security
    assert gates[5].status == GateStatus.PASSED  # Performance
    assert gates[6].status == GateStatus.PASSED  # Load
    assert gates[7].status == GateStatus.PASSED  # Regression
    assert gates[8].status == GateStatus.PASSED  # Code Review


# ---------------------------------------------------------------------------
# Report Generator Tests
# ---------------------------------------------------------------------------

def test_report_generator_html():
    gen = ReportGenerator()
    report = QualityCertificationReport(
        project_id="test-proj",
        build_id="build-test-01",
        overall_status=OverallQualityStatus.APPROVED,
        quality_score=95,
        gates=[
            QualityGateResult(
                gate_number=1, gate_name="Build Gate", status=GateStatus.PASSED,
                criterion="Compiles", evaluated_value="SUCCESS", reason="Clean build"
            )
        ],
        unit_summary=UnitTestSummary(total_tests=5, passed=5, coverage_percent=85.0),
        integration_summary=IntegrationTestSummary(),
        api_summary=ApiTestSummary(),
        security_summary=SecurityBreakerSummary(),
        performance_metrics=PerformanceMetrics(p95_latency_ms=45.0),
    )
    with patch.object(gen.workspace, "write_file") as mock_write:
        html_path, pdf_path = gen.generate_and_save_reports(report)
        assert html_path.endswith(".html")
        assert mock_write.called
        assert "APPROVED" in report.summary_markdown


# ---------------------------------------------------------------------------
# Bug Lifecycle Manager Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bug_lifecycle_repair_attempts():
    mock_db = AsyncMock()
    mock_bug = Bug(
        id="bug-123",
        project_id="test-proj",
        title="SQL Injection in auth",
        severity="critical",
        status="open",
        attempt_count=0,
    )
    mock_db.get.return_value = mock_bug

    mgr = BugLifecycleManager(mock_db)

    # Attempt 1: Failed verification
    updated = await mgr.record_repair_attempt("bug-123", "Patched query", False, "Test still failed")
    assert updated.attempt_count == 1
    assert updated.status == "in_progress"

    # Attempt 2: Failed verification
    updated = await mgr.record_repair_attempt("bug-123", "Tried parameterized", False, "Still failing")
    assert updated.attempt_count == 2
    assert updated.status == "in_progress"

    # Attempt 3: Failed verification -> MUST BE BLOCKED
    updated = await mgr.record_repair_attempt("bug-123", "Another fix", False, "Failed again")
    assert updated.attempt_count == 3
    assert updated.status == "blocked"


# ---------------------------------------------------------------------------
# Quality Engine Orchestrator Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quality_engine_orchestration():
    engine = QualityEngine(db=None)

    with patch.object(engine.unit_runner, "run_unit_tests", return_value=UnitTestSummary(total_tests=5, passed=5, coverage_percent=90.0)), \
         patch.object(engine.integration_runner, "run_integration_tests", return_value=IntegrationTestSummary(total_scenarios=2, passed=2)), \
         patch.object(engine.api_runner, "run_api_tests", return_value=ApiTestSummary(total_endpoints=3, passed=3)), \
         patch.object(engine.security_suite, "run_security_break", return_value=SecurityBreakerSummary(total_vulnerabilities=0)), \
         patch.object(engine.perf_runner, "benchmark_endpoint", return_value=PerformanceMetrics(p95_latency_ms=100.0, requests_per_second=50.0)), \
         patch.object(engine.load_runner, "run_progressive_load_test", return_value=[
             LoadTestStageResult(stage=1, target_concurrency=10, actual_concurrency=10, total_requests=10, successful_requests=10, failed_requests=0, requests_per_second=50.0, avg_latency_ms=10.0, p95_latency_ms=15.0, p99_latency_ms=20.0, status="passed")
         ]), \
         patch.object(engine.report_generator, "generate_and_save_reports", return_value=(".agentforge/quality_reports/test.html", None)):

        report = await engine.run_full_quality_audit(project_id="test-proj", run_load_test=True, max_load_stages=1)
        assert report.project_id == "test-proj"
        assert len(report.gates) == 10
        assert report.quality_score > 70

