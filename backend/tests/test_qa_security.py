"""
Tests for Phase 6: Automated QA test runner and SecurityScannerService.

Covers:
  - Security tool detection (Semgrep, Gitleaks, Bandit, Builtin).
  - Deterministic secret detection (AWS, Private Keys, generic secrets).
  - Deterministic code vulnerability detection (eval, exec, shell=True, SQL injection).
  - Evidence redaction for credentials.
  - QA test discovery and pytest execution runner.
  - Distinguishing passed vs failed vs not executed test suites.
  - Structured bug report generation with reproduction steps.
  - QA and Security REST API endpoints.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.qa_runner import QARunnerService
from app.services.security_scanner import SecurityScannerService
from app.services.workspace import WorkspaceService
from httpx import AsyncClient

VALID_PROJECT = {
    "name": "QA Security Test Project",
    "description": "Testing automated QA verification and security analysis.",
    "preferred_language": "python",
    "preferred_framework": "fastapi",
    "preferred_database": "sqlite",
}


async def _create_project(client: AsyncClient, overrides: dict | None = None) -> dict:
    payload = {**VALID_PROJECT, **(overrides or {})}
    resp = await client.post("/api/v1/projects", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Security Scanner Unit Tests
# ---------------------------------------------------------------------------


class TestSecurityScanner:
    def test_detect_available_tools(self):
        scanner = SecurityScannerService()
        tools = scanner.detect_available_tools()
        assert "builtin_scanner" in tools
        assert tools["builtin_scanner"]["installed"] is True
        assert "semgrep" in tools
        assert "gitleaks" in tools
        assert "bandit" in tools

    def test_scan_clean_code(self):
        scanner = SecurityScannerService()
        code = """\
def calculate_sum(numbers: list[int]) -> int:
    return sum(numbers)
"""
        findings = scanner.scan_file_content("calc.py", code)
        assert len(findings) == 0

    def test_scan_hardcoded_aws_key(self):
        scanner = SecurityScannerService()
        code = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
        findings = scanner.scan_file_content("config.py", code)
        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "SEC-001"
        assert f.severity == "critical"
        # Evidence must redact secret
        assert "AKIA" in f.evidence
        assert "LE" in f.evidence
        assert "AKIAIOSFODNN7EXAMPLE" not in f.evidence

    def test_scan_private_key(self):
        scanner = SecurityScannerService()
        code = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n"
        findings = scanner.scan_file_content("server.key", code)
        assert any(f.rule_id == "SEC-002" for f in findings)
        assert any(f.severity == "critical" for f in findings)

    def test_scan_unsafe_eval_exec(self):
        scanner = SecurityScannerService()
        code = """\
def run_user_code(user_input):
    return eval(user_input)
"""
        findings = scanner.scan_file_content("handler.py", code)
        assert any(f.rule_id == "VULN-001" for f in findings)

    def test_scan_subprocess_shell_true(self):
        scanner = SecurityScannerService()
        code = "subprocess.run(user_cmd, shell=True)\n"
        findings = scanner.scan_file_content("runner.py", code)
        assert any(f.rule_id == "VULN-003" for f in findings)
        assert any(f.severity == "high" for f in findings)

    def test_scan_sql_injection(self):
        scanner = SecurityScannerService()
        code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
        findings = scanner.scan_file_content("db.py", code)
        assert any(f.rule_id == "VULN-004" for f in findings)

    def test_scan_project_workflow(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            scanner = SecurityScannerService()
            scanner.workspace_service = ws
            project_id = "proj-sec-test"

            ws.write_file(project_id, "clean.py", "x = 42\n")
            ws.write_file(project_id, "vulnerable.py", "eval('1+1')\n")

            report = scanner.scan_project(project_id)
            assert report["passed"] is False
            assert report["approved_for_deployment"] is False
            assert report["critical_count"] >= 1
            assert len(report["findings"]) >= 1


# ---------------------------------------------------------------------------
# QA Runner Unit Tests
# ---------------------------------------------------------------------------


class TestQARunner:
    def test_discover_test_files(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            qa = QARunnerService()
            qa.workspace_service = ws
            project_id = "qa-discover"

            ws.write_file(project_id, "app/main.py", "x = 1")
            ws.write_file(project_id, "tests/test_api.py", "def test_ok(): pass")
            ws.write_file(project_id, "service_test.py", "def test_srv(): pass")

            discovered = qa.discover_test_files(project_id)
            assert len(discovered) == 2
            assert any("test_api.py" in p for p in discovered)
            assert any("service_test.py" in p for p in discovered)

    def test_run_tests_no_test_files(self):
        """Rule: Never report a test suite as passing if required tests were not executed."""
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            qa = QARunnerService()
            qa.workspace_service = ws
            project_id = "qa-no-tests"

            ws.write_file(project_id, "app/main.py", "x = 1")
            result = qa.run_tests(project_id)

            assert result.passed is False
            assert result.status == "not_executed"
            assert result.not_executed_count == 1
            assert len(result.bugs) >= 1
            assert result.bugs[0]["id"] == "BUG-NO-TESTS"

    def test_run_tests_passing_suite(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            qa = QARunnerService()
            qa.workspace_service = ws
            qa.runner.workspace_service = ws
            project_id = "qa-pass-suite"

            ws.write_file(
                project_id,
                "tests/test_calc.py",
                "def test_simple_addition():\n    assert 2 + 2 == 4\n",
            )
            result = qa.run_tests(project_id)

            assert result.passed is True
            assert result.status == "passed"
            assert result.passed_count >= 1
            assert result.failed_count == 0
            assert len(result.bugs) == 0

    def test_run_tests_failing_suite_creates_bugs(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            qa = QARunnerService()
            qa.workspace_service = ws
            qa.runner.workspace_service = ws
            project_id = "qa-fail-suite"

            ws.write_file(
                project_id,
                "tests/test_fail.py",
                "def test_intentional_failure():\n    assert 1 == 2\n",
            )
            result = qa.run_tests(project_id)

            assert result.passed is False
            assert result.status == "failed"
            assert result.failed_count >= 1
            assert len(result.bugs) >= 1
            bug = result.bugs[0]
            assert "test_intentional_failure" in bug["title"]
            assert bug["severity"] == "high"


# ---------------------------------------------------------------------------
# QA & Security REST API Endpoints Tests
# ---------------------------------------------------------------------------


class TestQASecurityEndpoints:
    async def test_get_detected_security_tools(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/security/tools")
        assert resp.status_code == 200
        body = resp.json()
        assert "tools" in body
        assert "builtin_scanner" in body["tools"]

    async def test_scan_project_security(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Security Scan Proj"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}/security/scan")
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert "passed" in body
        assert "findings" in body
        assert "critical_count" in body

    async def test_run_project_tests_endpoint(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "QA Tests Proj"})
        project_id = proj["id"]

        resp = await async_client.post(f"/api/v1/projects/{project_id}/qa/run-tests")
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert "passed" in body
        assert "bugs" in body
        assert "status" in body

    async def test_discover_test_files_endpoint(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Discover Tests Proj"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}/qa/test-files")
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert "test_files" in body
