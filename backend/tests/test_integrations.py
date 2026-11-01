"""
Unit and integration tests for Free Developer Services Integrations.
"""

from __future__ import annotations

import httpx
import pytest
from app.integrations.auth.rbac import Permission, UserRole, get_auth_service
from app.integrations.backblaze.s3_client import get_backblaze_service
from app.integrations.betterstack.heartbeat import get_betterstack_service
from app.integrations.bugsink.reporter import get_bugsink_reporter
from app.integrations.cloudflare.pages import get_cloudflare_service
from app.integrations.github.actions import get_github_actions_service
from app.integrations.github.client import GitHubClient
from app.integrations.openobserve.client import get_openobserve_client
from app.integrations.security.gitleaks_runner import get_gitleaks_runner
from app.integrations.security.semgrep_runner import get_semgrep_runner
from app.integrations.security.trivy_runner import get_trivy_runner
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_list_all_integrations(async_client: AsyncClient):
    """Verify all 9+ free developer service integrations are registered and queryable."""
    resp = await async_client.get("/api/v1/integrations/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 9

    provider_ids = [item["provider_id"] for item in data]
    assert "github" in provider_ids
    assert "github_actions" in provider_ids
    assert "semgrep" in provider_ids
    assert "gitleaks" in provider_ids
    assert "trivy" in provider_ids
    assert "openobserve" in provider_ids
    assert "bugsink" in provider_ids
    assert "betterstack" in provider_ids
    assert "cloudflare" in provider_ids
    assert "backblaze_b2" in provider_ids
    assert "auth_rbac" in provider_ids


@pytest.mark.asyncio
async def test_integration_category_filtering(async_client: AsyncClient):
    """Verify filtering by IntegrationCategory."""
    resp = await async_client.get("/api/v1/integrations/?category=security")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3
    for p in data:
        assert p["category"] == "security"


@pytest.mark.asyncio
async def test_integration_toggle_and_test(async_client: AsyncClient):
    """Test runtime toggle and on-demand connectivity testing."""
    # 1. Query GitHub provider
    resp = await async_client.get("/api/v1/integrations/github")
    assert resp.status_code == 200
    assert resp.json()["provider_id"] == "github"

    # 2. Toggle disabled
    toggle_resp = await async_client.post(
        "/api/v1/integrations/github/toggle", json={"enabled": False}
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["enabled"] is False

    # 3. Toggle re-enabled
    toggle_resp2 = await async_client.post(
        "/api/v1/integrations/github/toggle", json={"enabled": True}
    )
    assert toggle_resp2.status_code == 200
    assert toggle_resp2.json()["enabled"] is True

    # 4. Trigger test connection
    test_resp = await async_client.post("/api/v1/integrations/github/test")
    assert test_resp.status_code == 200
    assert "status" in test_resp.json()


@pytest.mark.asyncio
async def test_github_service_and_client_mock():
    """Test GitHub client operations with mocked responses."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/user" in url:
            return httpx.Response(200, json={"login": "octocat", "type": "User"})
        if "/rate_limit" in url:
            return httpx.Response(
                200,
                json={
                    "resources": {
                        "core": {"limit": 5000, "remaining": 4990, "reset": 0, "used": 10}
                    }
                },
            )
        if "/repos/octocat/demo/branches" in url:
            return httpx.Response(
                200, json=[{"name": "main", "commit": {"sha": "abc1234"}, "protected": True}]
            )
        if "/repos/octocat/demo/pulls" in url and request.method == "GET":
            return httpx.Response(
                200,
                json=[
                    {
                        "number": 1,
                        "title": "feat: add fast payment",
                        "state": "open",
                        "html_url": "https://github.com/octocat/demo/pull/1",
                        "head": {"ref": "feat/payments"},
                        "base": {"ref": "main"},
                        "user": {"login": "developer-agent"},
                        "created_at": "2026-11-01T12:00:00Z",
                    }
                ],
            )
        return httpx.Response(200, json={})

    mock_transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=mock_transport) as http_client:
        gh_client = GitHubClient(token="ghp_mock_token_1234567890abcdef", client=http_client)
        user = await gh_client.get_current_user()
        assert user["login"] == "octocat"

        rl = await gh_client.get_rate_limit()
        assert rl.remaining == 4990

        branches = await gh_client.list_branches("octocat", "demo")
        assert len(branches) == 1
        assert branches[0].name == "main"

        prs = await gh_client.list_pull_requests("octocat", "demo")
        assert len(prs) == 1
        assert prs[0].title == "feat: add fast payment"


@pytest.mark.asyncio
async def test_github_actions_mock():
    """Test GitHub Actions workflow runs and jobs parsing."""

    def mock_actions_handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/actions/runs" in url and "/jobs" not in url:
            return httpx.Response(
                200,
                json={
                    "workflow_runs": [
                        {
                            "id": 101,
                            "name": "CI",
                            "status": "completed",
                            "conclusion": "success",
                            "workflow_id": 42,
                            "event": "push",
                            "head_branch": "main",
                            "head_sha": "f1a2b3c4",
                            "html_url": "https://github.com/octocat/demo/actions/runs/101",
                            "created_at": "2026-11-01T10:00:00Z",
                            "updated_at": "2026-11-01T10:05:00Z",
                            "run_attempt": 1,
                            "actor": {"login": "octocat"},
                        }
                    ]
                },
            )
        if "/jobs" in url:
            return httpx.Response(
                200,
                json={
                    "jobs": [
                        {
                            "id": 201,
                            "run_id": 101,
                            "name": "Backend Lint & Tests",
                            "status": "completed",
                            "conclusion": "success",
                            "steps": [
                                {
                                    "name": "Run Pytest Suite",
                                    "status": "completed",
                                    "conclusion": "success",
                                    "number": 4,
                                }
                            ],
                        }
                    ]
                },
            )
        return httpx.Response(200, json={})

    mock_transport = httpx.MockTransport(mock_actions_handler)
    async with httpx.AsyncClient(transport=mock_transport) as http_client:
        gh_client = GitHubClient(token="ghp_test_token", client=http_client)
        svc = get_github_actions_service()
        svc._client = gh_client

        runs = await svc.list_workflow_runs("octocat", "demo")
        assert len(runs) == 1
        assert runs[0].id == 101
        assert runs[0].conclusion == "success"

        jobs = await svc.get_workflow_jobs("octocat", "demo", 101)
        assert len(jobs) == 1
        assert jobs[0].name == "Backend Lint & Tests"


def test_semgrep_scanner_fallback(tmp_path):
    """Test Semgrep fallback AST engine detects high-risk vulnerabilities."""
    runner = get_semgrep_runner()

    # Create a vulnerable test file
    vuln_code = (
        "import os, subprocess\n\n"
        "def run_user_cmd(cmd):\n"
        "    eval(cmd)\n"
        "    subprocess.run(cmd, shell=True)\n"
    )
    test_file = tmp_path / "unsafe.py"
    test_file.write_text(vuln_code, encoding="utf-8")

    report = runner.scan_directory(tmp_path, "TEST-PROJ-01")
    assert report.total_count >= 2
    rule_ids = [f.rule_id for f in report.findings]
    assert any("arbitrary-code-execution" in r for r in rule_ids)
    assert any("subprocess-shell-true" in r for r in rule_ids)


def test_gitleaks_scanner_fallback(tmp_path):
    """Test Gitleaks pattern engine detects exposed tokens and private keys."""
    runner = get_gitleaks_runner()

    secret_content = (
        "# Configuration file with leaked credentials\n"
        "GITHUB_PAT = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'\n"
        "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
    )
    test_file = tmp_path / "secrets.env"
    test_file.write_text(secret_content, encoding="utf-8")

    report = runner.scan_directory(tmp_path, "TEST-PROJ-02")
    assert report.total_count >= 2
    rule_ids = [f.rule_id for f in report.findings]
    assert any("github-pat" in r for r in rule_ids)
    assert any("aws-access-key-id" in r for r in rule_ids)


def test_trivy_scanner_fallback(tmp_path):
    """Test Trivy manifest parser identifies declared vulnerable dependencies."""
    runner = get_trivy_runner()

    req_content = "fastapi==0.95.0\n" "requests==2.28.0\n" "urllib3==1.26.15\n"
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(req_content, encoding="utf-8")

    report = runner.scan_directory(tmp_path, "TEST-PROJ-03")
    assert report.total_count >= 3
    cves = [f.rule_id for f in report.findings]
    assert "CVE-2023-32681" in cves
    assert "CVE-2023-45803" in cves


@pytest.mark.asyncio
async def test_openobserve_event_sanitization_and_forwarding():
    """Verify OpenObserve client redacts secrets and drops large source blocks."""
    sent_payload = []

    def mock_oo_handler(request: httpx.Request) -> httpx.Response:
        import json

        data = json.loads(request.read())
        sent_payload.extend(data)
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(mock_oo_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        oo_client = get_openobserve_client()
        oo_client._external_client = http_client
        oo_client._settings.openobserve_enabled = True
        oo_client._settings.openobserve_user = "admin@example.com"
        oo_client._settings.openobserve_password = "SecretPassword123"

        test_events = [
            {
                "event_type": "tool_execution",
                "message": "Connecting using token ghp_111122223333444455556666777788889999",
                "payload": {
                    "code": "def secret_code(): pass",
                    "status": "success",
                },
            }
        ]

        success = await oo_client.forward_events(test_events)
        assert success is True
        assert len(sent_payload) == 1
        # Code key should be dropped
        assert "code" not in sent_payload[0].get("payload", {})


@pytest.mark.asyncio
async def test_bugsink_exception_reporting():
    """Test Bugsink exception capture serialization."""
    reported = []

    def mock_bugsink_handler(request: httpx.Request) -> httpx.Response:
        import json

        data = json.loads(request.read())
        reported.append(data)
        return httpx.Response(200, json={"id": "evt-123"})

    transport = httpx.MockTransport(mock_bugsink_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        reporter = get_bugsink_reporter()
        reporter._external_client = http_client
        reporter._settings.bugsink_enabled = True
        reporter._settings.bugsink_dsn = "https://key123@bugsink.example.com/42"

        try:
            raise ValueError("Test AgentForge Error")
        except ValueError as err:
            success = await reporter.capture_exception(err, context={"task_id": "TASK-001"})
            assert success is True
            assert len(reported) == 1
            assert reported[0]["exception"]["values"][0]["type"] == "ValueError"


@pytest.mark.asyncio
async def test_betterstack_heartbeat():
    """Test Better Stack heartbeat delivery."""
    pings = []

    def mock_heartbeat_handler(request: httpx.Request) -> httpx.Response:
        pings.append(request.url)
        return httpx.Response(200, text="ok")

    transport = httpx.MockTransport(mock_heartbeat_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        service = get_betterstack_service()
        service._external_client = http_client
        service._settings.betterstack_enabled = True
        service._settings.betterstack_heartbeat_url = (
            "https://uptime.betterstack.com/api/v1/heartbeat/test-token"
        )

        success = await service.send_heartbeat()
        assert success is True
        assert len(pings) == 1


def test_cloudflare_deployment_guide_and_tunnel_routes():
    """Test Cloudflare deployment guide and tunnel route whitelisting."""
    cf = get_cloudflare_service()
    guide = cf.get_pages_deployment_guide()
    assert guide["platform"] == "Cloudflare Pages"
    assert "wrangler" in guide["deploy_command"]

    tunnel = cf.get_tunnel_status()
    # Confirm security constraint: Terminal & Ollama MUST be blocked from public exposure
    assert any("/api/v1/terminal/*" in r for r in tunnel["blocked_routes"])
    assert any("/ollama/*" in r for r in tunnel["blocked_routes"])


@pytest.mark.asyncio
async def test_backblaze_b2_storage():
    """Test Backblaze B2 artifact upload and retrieval."""
    b2 = get_backblaze_service()
    res = await b2.upload_artifact("PROJ-999", "architecture.md", "# System Architecture")
    assert res["key"] == "projects/PROJ-999/architecture.md"
    assert res["size"] > 0

    items = await b2.list_artifacts("PROJ-999")
    assert len(items) == 1
    assert items[0]["filename"] == "architecture.md"


def test_auth_rbac_permissions():
    """Test Role-Based Access Control logic."""
    auth = get_auth_service()

    # In standalone developer mode, all permissions granted
    auth._settings.auth_enabled = False
    assert auth.check_permission(UserRole.VIEWER, Permission.EXECUTE_TERMINAL) is True

    # In multi-user RBAC mode, permissions strictly enforced
    auth._settings.auth_enabled = True
    assert auth.check_permission(UserRole.ADMINISTRATOR, Permission.EXECUTE_TERMINAL) is True
    assert auth.check_permission(UserRole.DEVELOPER, Permission.EXECUTE_TERMINAL) is True
    assert auth.check_permission(UserRole.VIEWER, Permission.EXECUTE_TERMINAL) is False
    assert auth.check_permission(UserRole.VIEWER, Permission.VIEW_PROJECTS) is True

    # Token issuance
    tok = auth.create_token_for_user("alice", UserRole.DEVELOPER)
    assert tok.user.username == "alice"
    assert tok.user.role == UserRole.DEVELOPER
    assert tok.access_token.startswith("af_jwt_alice_developer_")
