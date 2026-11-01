"""
Pydantic schemas and DTOs for the Quality Engineering & Validation System.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TestType(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    API = "api"
    E2E = "e2e"
    SECURITY = "security"
    PERFORMANCE = "performance"
    LOAD = "load"
    REGRESSION = "regression"


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    NOT_RUN = "not_run"


class GateStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    WAIVED = "waived"


class OverallQualityStatus(str, Enum):
    APPROVED = "APPROVED"
    CONDITIONALLY_APPROVED = "CONDITIONALLY_APPROVED"
    BLOCKED = "BLOCKED"
    NOT_VERIFIED = "NOT_VERIFIED"


class TestCaseResult(BaseModel):
    id: str
    name: str
    test_type: TestType
    status: TestStatus
    duration_ms: float = 0.0
    file_path: str | None = None
    error_message: str | None = None
    stacktrace: str | None = None


class UnitTestSummary(BaseModel):
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    coverage_percent: float = 0.0
    duration_seconds: float = 0.0
    test_cases: list[TestCaseResult] = Field(default_factory=list)


class IntegrationTestSummary(BaseModel):
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    scenarios: list[TestCaseResult] = Field(default_factory=list)


class ApiEndpointTestResult(BaseModel):
    path: str
    method: str
    status_code: int
    expected_status: int
    contract_valid: bool
    response_time_ms: float
    passed: bool
    error: str | None = None


class ApiTestSummary(BaseModel):
    total_endpoints: int = 0
    passed: int = 0
    failed: int = 0
    contract_violations: int = 0
    endpoints: list[ApiEndpointTestResult] = Field(default_factory=list)


class SecurityBreakerFinding(BaseModel):
    id: str
    vector: str  # auth, idor, sqli, xss, ssrf, secrets, deps
    severity: str  # critical, high, medium, low
    title: str
    description: str
    reproduction_steps: str
    affected_file: str | None = None
    remediation: str | None = None


class SecurityBreakerSummary(BaseModel):
    total_vulnerabilities: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    exposed_secrets_count: int = 0
    findings: list[SecurityBreakerFinding] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p90_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    requests_per_second: float = 0.0
    total_requests: int = 0
    cpu_percent: float | None = None
    memory_mb: float | None = None


class LoadTestStageResult(BaseModel):
    stage: int
    target_concurrency: int
    actual_concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    cpu_percent: float | None = None
    memory_mb: float | None = None
    status: str
    bottlenecks: list[str] = Field(default_factory=list)


class QualityGateResult(BaseModel):
    gate_number: int
    gate_name: str
    status: GateStatus
    criterion: str
    evaluated_value: str
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class QualityCertificationReport(BaseModel):
    project_id: str
    build_id: str
    overall_status: OverallQualityStatus
    quality_score: int  # 0 to 100
    gates: list[QualityGateResult] = Field(default_factory=list)
    unit_summary: UnitTestSummary
    integration_summary: IntegrationTestSummary
    api_summary: ApiTestSummary
    security_summary: SecurityBreakerSummary
    performance_metrics: PerformanceMetrics
    load_test_stages: list[LoadTestStageResult] = Field(default_factory=list)
    open_critical_bugs: int = 0
    open_high_bugs: int = 0
    summary_markdown: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    html_report_path: str | None = None
    pdf_report_path: str | None = None

