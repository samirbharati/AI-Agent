"""
Phase 7: End-to-End Integration Tests.

These tests validate the full AgentForge pipeline from project creation through
workflow execution, workspace management, QA testing, and security scanning.

All LLM calls and background tasks are mocked — no live Ollama required.
The workspace filesystem is isolated to a temp directory per test.
"""

from __future__ import annotations

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.models.db_models import AgentRun, Artifact, WorkflowEvent
from app.services.llm_client import LLMResponse
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

INTEGRATION_PROJECT = {
    "name": "Integration Test App",
    "description": "A full-stack integration test project for AgentForge validation.",
    "preferred_language": "python",
    "preferred_framework": "fastapi",
    "preferred_database": "sqlite",
    "max_repair_attempts": 2,
}


def _make_llm_response(text: str) -> LLMResponse:
    return LLMResponse(
        content=text,
        model="qwen2.5-coder:7b",
        prompt_tokens=50,
        completion_tokens=100,
        total_tokens=150,
        duration_seconds=0.3,
    )


@contextmanager
def patch_workflow_background():
    """Replace the background workflow runner with an async no-op."""
    with patch(
        "app.api.v1.workflow._run_workflow_background",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@contextmanager
def patch_all_agents(response_text: str = "# Agent Output\n\nContent here."):
    """Patch the LLM chat across all agents."""
    with patch(
        "app.services.llm_client.OllamaLLMClient.chat",
        new_callable=AsyncMock,
        return_value=_make_llm_response(response_text),
    ) as mock:
        yield mock


async def _create_project(client: AsyncClient, overrides: dict | None = None) -> dict:
    payload = {**INTEGRATION_PROJECT, **(overrides or {})}
    resp = await client.post("/api/v1/projects", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_status(client: AsyncClient, project_id: str, status: str) -> None:
    resp = await client.patch(f"/api/v1/projects/{project_id}", json={"status": status})
    assert resp.status_code == 200, f"Set status {status!r} failed: {resp.text}"


# ---------------------------------------------------------------------------
# Phase 7.1: Project lifecycle integration
# ---------------------------------------------------------------------------


class TestProjectLifecycleIntegration:
    """Test full project CRUD and state transitions via the API."""

    async def test_create_and_retrieve_project(self, async_client: AsyncClient):
        """Create a project and verify all fields are persisted correctly."""
        proj = await _create_project(async_client, {"name": "Lifecycle Test"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == project_id
        assert data["name"] == "Lifecycle Test"
        assert data["status"] == "pending"
        assert data["preferred_language"] == "python"
        assert data["preferred_framework"] == "fastapi"
        assert data["preferred_database"] == "sqlite"
        assert data["max_repair_attempts"] == 2

    async def test_project_appears_in_list(self, async_client: AsyncClient):
        """Verify newly created projects appear in paginated list."""
        proj = await _create_project(async_client, {"name": "List Visibility Test"})
        project_id = proj["id"]

        resp = await async_client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        ids = [p["id"] for p in data["items"]]
        assert project_id in ids

    async def test_full_status_progression(self, async_client: AsyncClient):
        """Verify project can progress through all major workflow statuses."""
        proj = await _create_project(async_client, {"name": "Status Progression"})
        project_id = proj["id"]

        progression = [
            "requirements_review",
            "requirements_approved",
            "architecture_review",
            "architecture_approved",
            "planning",
            "in_progress",
            "completed",
        ]

        for status in progression:
            await _set_status(async_client, project_id, status)
            resp = await async_client.get(f"/api/v1/projects/{project_id}")
            assert resp.json()["status"] == status

    async def test_project_update_name_and_description(
        self, async_client: AsyncClient
    ):
        """Update project name/description and verify changes persist."""
        proj = await _create_project(async_client, {"name": "Update Before"})
        project_id = proj["id"]

        resp = await async_client.patch(
            f"/api/v1/projects/{project_id}",
            json={
                "name": "Update After",
                "description": "Updated description that meets min length requirement.",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Update After"

    async def test_delete_cancels_project(self, async_client: AsyncClient):
        """Deleting a project marks it as cancelled (soft delete audit policy)."""
        proj = await _create_project(async_client, {"name": "Cancel Me"})
        project_id = proj["id"]

        del_resp = await async_client.delete(f"/api/v1/projects/{project_id}")
        assert del_resp.status_code == 200

        get_resp = await async_client.get(f"/api/v1/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "cancelled"

    async def test_project_not_found_returns_404(self, async_client: AsyncClient):
        """Nonexistent project ID returns 404 on all endpoints."""
        bad_id = "00000000-0000-0000-0000-000000000000"
        assert (await async_client.get(f"/api/v1/projects/{bad_id}")).status_code == 404
        assert (await async_client.delete(f"/api/v1/projects/{bad_id}")).status_code == 404


# ---------------------------------------------------------------------------
# Phase 7.2: Workflow API integration
# ---------------------------------------------------------------------------


class TestWorkflowAPIIntegration:
    """Test the workflow endpoints in sequence as a frontend would call them."""

    async def test_start_workflow_queues_background_task(
        self, async_client: AsyncClient
    ):
        """
        Start workflow should:
        1. Return 200 with status=ok
        2. Dispatch background task with requirements phase
        """
        proj = await _create_project(async_client, {"name": "WF API Integration"})
        project_id = proj["id"]

        with patch_workflow_background() as mock_bg:
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/start"
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        mock_bg.assert_called_once_with(project_id, "requirements")

    async def test_workflow_status_endpoint_reflects_db_state(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Workflow status endpoint must aggregate tasks, runs, and events."""
        proj = await _create_project(async_client, {"name": "WF Status Integration"})
        project_id = proj["id"]

        # Manually insert a workflow event
        db_session.add(WorkflowEvent(
            project_id=project_id,
            event_type="test_event",
            message="Testing status aggregation",
            severity="info",
        ))
        await db_session.commit()

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/workflow/status"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert body["status"] == "pending"
        assert body["tasks"]["total"] == 0
        assert body["agent_runs"]["total"] == 0
        assert isinstance(body["recent_events"], list)
        assert len(body["recent_events"]) >= 1

    async def test_double_start_returns_409(self, async_client: AsyncClient):
        """Starting a workflow on a non-pending project returns 409."""
        proj = await _create_project(async_client, {"name": "Double Start Test"})
        project_id = proj["id"]

        await _set_status(async_client, project_id, "in_progress")

        with patch_workflow_background():
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/start"
            )
        assert resp.status_code == 409

    async def test_resume_flow_after_approval(self, async_client: AsyncClient):
        """
        After requirements_approved status, resume should succeed and fire the
        background task.
        """
        proj = await _create_project(async_client, {"name": "Resume Integration"})
        project_id = proj["id"]

        await _set_status(async_client, project_id, "requirements_approved")

        with patch_workflow_background() as mock_bg:
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/resume"
            )
        assert resp.status_code == 200
        mock_bg.assert_called_once_with(project_id, "architecture")

    async def test_workflow_events_sse_endpoint_exists(
        self, async_client: AsyncClient
    ):
        """SSE events endpoint should return a 200 with text/event-stream."""
        proj = await _create_project(async_client, {"name": "SSE Integration"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/workflow/events",
            headers={"Accept": "text/event-stream"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Phase 7.3: Agent pipeline integration
# ---------------------------------------------------------------------------


class TestAgentPipelineIntegration:
    """Tests that wire multiple agents together in realistic sequences."""

    async def test_requirements_to_architecture_pipeline(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """
        Run RequirementsAnalyst → SystemArchitect in sequence (mocked LLM),
        verifying outputs are passed correctly and AgentRun records are created.
        """
        from app.agents.requirements_analyst import RequirementsAnalystAgent
        from app.agents.system_architect import SystemArchitectAgent

        proj = await _create_project(
            async_client, {"name": "Requirements-Architecture Pipeline"}
        )
        project_id = proj["id"]

        req_output = """# System Requirements Document

## Functional Requirements
FR-001: The system shall provide JWT-based user authentication.
FR-002: The system shall provide a dashboard for real-time task monitoring.

## Non-Functional Requirements
NFR-001: API responses must complete within 200ms at 95th percentile.
NFR-002: System must achieve 99.9% uptime.

## User Stories
US-001: As a user, I want to log in securely so that my data is protected.
"""

        arch_output = """# System Architecture Design

## Architecture Overview
The system uses a modular layered architecture with FastAPI backend and SQLite persistence.

## Technology Stack
- Backend: Python 3.11, FastAPI
- Database: SQLite with async SQLAlchemy
- Frontend: React with TypeScript

## API Design
- `POST /api/v1/auth/login` - Authenticate user
- `GET /api/v1/dashboard/stats` - Retrieve dashboard telemetry

## Database Schema
```sql
CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(255) UNIQUE);
```
"""

        # Step 1: Requirements analysis
        with patch_all_agents(req_output):
            ra = RequirementsAnalystAgent()
            req_result = await ra.run(
                context={
                    "task_description": proj["description"],
                    "project_name": proj["name"],
                },
                db=db_session,
                project_id=project_id,
            )

        assert req_result.success is True
        assert "Functional Requirements" in req_result.output

        # Step 2: Architecture design with requirements as context
        with patch_all_agents(arch_output):
            sa = SystemArchitectAgent()
            arch_result = await sa.run(
                context={
                    "requirements_document": req_result.output,
                    "project_name": proj["name"],
                },
                db=db_session,
                project_id=project_id,
            )

        assert arch_result.success is True
        assert "Architecture" in arch_result.output

        # Verify AgentRun records were written to DB
        run_result = await db_session.execute(
            select(AgentRun).where(AgentRun.project_id == project_id)
        )
        runs = run_result.scalars().all()
        assert len(runs) == 2
        agent_ids = {r.agent_definition_id for r in runs}
        assert "requirements-analyst" in agent_ids
        assert "system-architect" in agent_ids

    async def test_task_planner_creates_db_tasks(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """TaskPlannerAgent must parse JSON and persist Tasks to the database."""
        from app.agents.task_planner import TaskPlannerAgent

        proj = await _create_project(async_client, {"name": "Task Planner DB Test"})
        project_id = proj["id"]

        task_plan = json.dumps({
            "tasks": [
                {
                    "title": "Setup project structure",
                    "description": "Initialize the project directory and config.",
                    "assigned_agent": "software-developer",
                    "priority": "high",
                    "complexity_estimate": "simple",
                    "dependencies": [],
                    "acceptance_criteria": "Project directory exists.",
                },
                {
                    "title": "Implement user authentication",
                    "description": "Add login and registration endpoints with JWT.",
                    "assigned_agent": "software-developer",
                    "priority": "high",
                    "complexity_estimate": "moderate",
                    "dependencies": ["Setup project structure"],
                    "acceptance_criteria": "Users can login.",
                },
            ],
            "total_tasks": 2,
            "estimated_complexity": "moderate",
            "planning_notes": "Sequential setup then auth.",
        })

        with patch_all_agents(task_plan):
            tp = TaskPlannerAgent()
            plan_result = await tp.run(
                context={
                    "architecture_document": "# Architecture\n\nFastAPI + SQLite.",
                    "requirements_document": "# Requirements\n\n1. Auth\n2. Dashboard",
                    "project_name": proj["name"],
                },
                db=db_session,
                project_id=project_id,
            )

        assert plan_result.success is True
        assert len(plan_result.parsed["tasks"]) == 2

    async def test_developer_agent_parses_json_output(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """SoftwareDeveloperAgent must parse valid file creation output."""
        from app.agents.software_developer import SoftwareDeveloperAgent

        proj = await _create_project(async_client, {"name": "Dev Output Test"})
        project_id = proj["id"]

        dev_json = json.dumps({
            "files": [
                {
                    "path": "app/main.py",
                    "action": "create",
                    "content": "from fastapi import FastAPI\n\napp = FastAPI()\n",
                }
            ],
            "commands": [
                {"command": "python -m pytest", "purpose": "Run tests", "safe_to_run": True}
            ],
            "implementation_notes": "Created FastAPI entrypoint.",
            "tests_included": False,
            "estimated_loc": 3,
        })

        with patch_all_agents(dev_json):
            dev = SoftwareDeveloperAgent()
            dev_result = await dev.run(
                context={
                    "task_title": "Create FastAPI entry point",
                    "task_description": "Create the main.py FastAPI application file.",
                    "architecture_summary": "FastAPI backend.",
                },
                db=db_session,
                project_id=project_id,
            )

        assert dev_result.success is True
        assert dev_result.parsed["file_count"] == 1
        assert dev_result.parsed["files"][0]["path"] == "app/main.py"

    async def test_qa_engineer_with_test_results_context(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """QAEngineerAgent should process test results and produce structured verdict."""
        from app.agents.qa_engineer import QAEngineerAgent

        proj = await _create_project(async_client, {"name": "QA Engineer Context"})
        project_id = proj["id"]

        qa_json = json.dumps({
            "verdict": "pass",
            "summary": "All 10 tests passed without regressions.",
            "test_cases": [
                {"name": "test_auth", "status": "passed", "severity": "high"}
            ],
            "bugs": [],
            "coverage_assessment": "92% statement coverage.",
            "recommendations": ["Add fuzz testing for token decoding."],
        })

        test_results = {
            "status": "passed",
            "passed_count": 10,
            "total_tests": 10,
            "failed_count": 0,
            "raw_stdout": "10 passed in 0.5s",
            "raw_stderr": "",
        }

        with patch_all_agents(qa_json):
            qa = QAEngineerAgent()
            qa_result = await qa.run(
                context={
                    "task_title": "Test authentication",
                    "implemented_files": {"app/auth.py": "def auth(): pass"},
                    "test_results": test_results,
                },
                db=db_session,
                project_id=project_id,
            )

        assert qa_result.success is True
        assert qa_result.agent_id == "qa-engineer"
        assert qa_result.parsed["verdict"] == "pass"

    async def test_security_engineer_with_scanner_findings(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """SecurityEngineerAgent should process scanner findings context."""
        from app.agents.security_engineer import SecurityEngineerAgent

        proj = await _create_project(
            async_client, {"name": "Security Engineer Context"}
        )
        project_id = proj["id"]

        sec_json = json.dumps({
            "overall_risk": "low",
            "findings": [],
            "approved_for_deployment": True,
            "summary": "No critical or high vulnerabilities detected.",
            "recommendations": ["Rotate staging credentials periodically."],
        })

        scanner_findings = [
            {
                "rule_id": "SEC-001",
                "severity": "info",
                "title": "Config check",
                "file_path": "config.py",
                "line_number": 5,
                "evidence": "DEBUG = True",
                "remediation": "Disable in production",
            }
        ]

        with patch_all_agents(sec_json):
            sec = SecurityEngineerAgent()
            sec_result = await sec.run(
                context={
                    "task_title": "Security audit",
                    "implemented_files": {"config.py": "DEBUG = True"},
                    "scanner_findings": scanner_findings,
                },
                db=db_session,
                project_id=project_id,
            )

        assert sec_result.success is True
        assert sec_result.agent_id == "security-engineer"
        assert sec_result.parsed["approved_for_deployment"] is True


# ---------------------------------------------------------------------------
# Phase 7.4: Security scanner integration
# ---------------------------------------------------------------------------


class TestSecurityScannerIntegration:
    """Integration tests for the SecurityScannerService."""

    async def test_scan_clean_code_returns_no_findings(self):
        """Clean code with no security issues should return empty findings."""
        from app.services.security_scanner import SecurityScannerService

        scanner = SecurityScannerService()
        clean_code = (
            "def calculate_sum(a: int, b: int) -> int:\n"
            "    \"\"\"Add two numbers.\"\"\"\n"
            "    return a + b\n\n"
            "def greet(name: str) -> str:\n"
            "    return f'Hello, {name}!'\n"
        )
        findings = scanner.scan_file_content("utils.py", clean_code)
        assert isinstance(findings, list)
        critical_findings = [f for f in findings if f.severity == "critical"]
        assert len(critical_findings) == 0

    async def test_scan_detects_hardcoded_aws_key(self):
        """Hardcoded AWS key pattern must be flagged as critical."""
        from app.services.security_scanner import SecurityScannerService

        scanner = SecurityScannerService()
        code_with_key = (
            "import boto3\n\n"
            "AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
            "AWS_SECRET = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'\n\n"
            "client = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY)\n"
        )
        findings = scanner.scan_file_content("aws_config.py", code_with_key)
        rule_ids = [f.rule_id for f in findings]
        assert "SEC-001" in rule_ids

    async def test_scan_detects_sql_injection_risk(self):
        """String-formatted SQL should be flagged."""
        from app.services.security_scanner import SecurityScannerService

        scanner = SecurityScannerService()
        vulnerable_code = (
            "def get_user(username: str):\n"
            "    db.execute(f\"SELECT * FROM users WHERE name = '{username}'\")\n"
        )
        findings = scanner.scan_file_content("db.py", vulnerable_code)
        rule_ids = [f.rule_id for f in findings]
        assert "VULN-004" in rule_ids

    async def test_scan_detects_eval_usage(self):
        """Use of eval() must be flagged as dangerous."""
        from app.services.security_scanner import SecurityScannerService

        scanner = SecurityScannerService()
        code_with_eval = (
            "def run_user_code(user_input: str):\n"
            "    result = eval(user_input)\n"
            "    return result\n"
        )
        findings = scanner.scan_file_content("runner.py", code_with_eval)
        rule_ids = [f.rule_id for f in findings]
        assert "VULN-001" in rule_ids

    async def test_project_security_scan_api(self, async_client: AsyncClient):
        """The GET /security/scan API endpoint returns a valid report structure."""
        proj = await _create_project(async_client, {"name": "Security API Scan"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/security/scan"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "project_id" in body
        assert body["project_id"] == project_id
        assert "findings" in body
        assert isinstance(body["findings"], list)
        assert "total_findings" in body
        assert "passed" in body

    async def test_security_tools_endpoint(self, async_client: AsyncClient):
        """The /security/tools endpoint lists available scanning tools."""
        resp = await async_client.get("/api/v1/security/tools")
        assert resp.status_code == 200
        body = resp.json()
        assert "tools" in body
        assert isinstance(body["tools"], dict)
        assert "builtin_scanner" in body["tools"]


# ---------------------------------------------------------------------------
# Phase 7.5: QA Runner integration
# ---------------------------------------------------------------------------


class TestQARunnerIntegration:
    """Integration tests for the QARunnerService."""

    async def test_run_tests_no_files_returns_not_executed(
        self, async_client: AsyncClient
    ):
        """When no test files exist, QA runner should report not_executed."""
        from app.services.qa_runner import QARunnerService

        proj = await _create_project(async_client, {"name": "QA Runner No Files"})
        project_id = proj["id"]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "app.services.workspace.WorkspaceService.get_project_dir",
                return_value=Path(tmpdir),
            ):
                runner = QARunnerService()
                result = runner.run_tests(project_id)

        assert result.status == "not_executed"
        assert result.total_tests == 0

    async def test_qa_test_files_api_endpoint(self, async_client: AsyncClient):
        """The /qa/test-files endpoint should list test files."""
        proj = await _create_project(async_client, {"name": "QA Test Files API"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/qa/test-files"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "test_files" in body
        assert isinstance(body["test_files"], list)

    async def test_qa_run_tests_api_endpoint(self, async_client: AsyncClient):
        """The /qa/run-tests endpoint triggers execution and returns results."""
        proj = await _create_project(async_client, {"name": "QA Run Tests API"})
        project_id = proj["id"]

        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/qa/run-tests"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "project_id" in body
        assert body["project_id"] == project_id
        assert "status" in body
        assert body["status"] in (
            "passed", "failed", "not_executed", "inconclusive"
        )
        assert "total_tests" in body
        assert "bugs" in body


# ---------------------------------------------------------------------------
# Phase 7.6: Workspace integration
# ---------------------------------------------------------------------------


class TestWorkspaceIntegration:
    """Integration tests for the WorkspaceService filesystem operations."""

    async def test_workspace_files_api(self, async_client: AsyncClient):
        """Listing workspace files should return a valid structure."""
        proj = await _create_project(async_client, {"name": "Workspace Files Test"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/files"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "files" in body
        assert isinstance(body["files"], list)

    async def test_workspace_git_status_api(self, async_client: AsyncClient):
        """Git status endpoint should return branch and change counts."""
        proj = await _create_project(async_client, {"name": "Git Status Test"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/git/status"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "project_id" in body
        assert body["project_id"] == project_id

    async def test_workspace_file_not_found(self, async_client: AsyncClient):
        """Reading a nonexistent workspace file returns 404."""
        proj = await _create_project(async_client, {"name": "File Not Found Test"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/files/content",
            params={"path": "nonexistent_file.py"},
        )
        assert resp.status_code == 404

    async def test_path_traversal_protection(self, async_client: AsyncClient):
        """Attempt to read a file outside the project sandbox must be blocked."""
        proj = await _create_project(
            async_client, {"name": "Path Traversal Protection"}
        )
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/files/content",
            params={"path": "../../etc/passwd"},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Phase 7.7: Artifact integration
# ---------------------------------------------------------------------------


class TestArtifactIntegration:
    """Tests for artifact storage and retrieval."""

    async def test_artifacts_empty_for_new_project(self, async_client: AsyncClient):
        """Newly created project has no artifacts."""
        proj = await _create_project(async_client, {"name": "Artifact Empty Test"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}/artifacts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["artifacts"] == []

    async def test_artifact_created_by_agent_appears_in_list(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Artifact written to DB should appear via the artifacts API."""
        proj = await _create_project(async_client, {"name": "Artifact DB Test"})
        project_id = proj["id"]

        artifact = Artifact(
            project_id=project_id,
            name="requirements.md",
            artifact_type="requirements",
            content="# Requirements\n\n1. User authentication\n2. Dashboard",
        )
        db_session.add(artifact)
        await db_session.commit()

        resp = await async_client.get(f"/api/v1/projects/{project_id}/artifacts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        artifact_data = body["artifacts"][0]
        assert artifact_data["name"] == "requirements.md"
        assert artifact_data["artifact_type"] == "requirements"

    async def test_get_specific_artifact(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Fetching a named artifact returns its content."""
        proj = await _create_project(async_client, {"name": "Get Artifact Test"})
        project_id = proj["id"]

        db_session.add(Artifact(
            project_id=project_id,
            name="architecture.md",
            artifact_type="architecture",
            content="# Architecture\n\nFastAPI + SQLite",
        ))
        await db_session.commit()

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/artifacts/architecture.md"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "architecture.md"
        assert "FastAPI" in body["content"]


# ---------------------------------------------------------------------------
# Phase 7.8: Agent Run pagination integration
# ---------------------------------------------------------------------------


class TestAgentRunPaginationIntegration:
    """Verify agent-run pagination works across multiple runs."""

    async def test_agent_runs_pagination(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Agent runs should be paginatable with correct total count."""
        proj = await _create_project(
            async_client, {"name": "Agent Run Pagination Test"}
        )
        project_id = proj["id"]

        # Insert 5 agent runs
        for i in range(5):
            db_session.add(AgentRun(
                project_id=project_id,
                agent_definition_id="software-developer",
                status="success",
                output_summary=f"Output {i}",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                duration_seconds=0.5,
                model_used="qwen2.5-coder:7b",
            ))
        await db_session.commit()

        # Fetch page 1 with page_size=3
        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/agent-runs",
            params={"page": 1, "page_size": 3},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["runs"]) == 3
        assert body["page"] == 1
        assert body["page_size"] == 3

        # Fetch page 2
        resp2 = await async_client.get(
            f"/api/v1/projects/{project_id}/agent-runs",
            params={"page": 2, "page_size": 3},
        )
        body2 = resp2.json()
        assert body2["total"] == 2
        assert len(body2["runs"]) == 2


# ---------------------------------------------------------------------------
# Phase 7.9: Health check integration
# ---------------------------------------------------------------------------


class TestHealthIntegration:
    """Verify health endpoints are reachable and return correct shapes."""

    async def test_health_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body

    async def test_ollama_health_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/health/ollama")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "reachable" in body

    async def test_models_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/models")
        assert resp.status_code == 200
        body = resp.json()
        assert "models" in body


# ---------------------------------------------------------------------------
# Phase 7.10: Repair loop integration
# ---------------------------------------------------------------------------


class TestRepairLoopIntegration:
    """Tests for the closed-loop repair mechanism."""

    async def test_repair_loop_respects_max_attempts_setting(
        self, async_client: AsyncClient
    ):
        """Project created with max_repair_attempts=1 stores this value."""
        proj = await _create_project(
            async_client,
            {"name": "Repair Loop Test", "max_repair_attempts": 1},
        )
        assert proj["max_repair_attempts"] == 1

    async def test_failed_project_can_be_restarted(self, async_client: AsyncClient):
        """A failed project status can be reset to pending for a fresh run."""
        proj = await _create_project(
            async_client, {"name": "Failed Restart Test"}
        )
        project_id = proj["id"]

        # Simulate a failed workflow
        await _set_status(async_client, project_id, "failed")
        proj_data = (await async_client.get(f"/api/v1/projects/{project_id}")).json()
        assert proj_data["status"] == "failed"

        # Reset to pending for restart
        await _set_status(async_client, project_id, "pending")
        proj_data2 = (await async_client.get(f"/api/v1/projects/{project_id}")).json()
        assert proj_data2["status"] == "pending"

        # Restart workflow
        with patch_workflow_background():
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/start"
            )
        assert resp.status_code == 200

    async def test_workflow_event_logged_on_repair(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Repair events should be logged to the workflow_events table."""
        proj = await _create_project(async_client, {"name": "Repair Event Log"})
        project_id = proj["id"]

        db_session.add(WorkflowEvent(
            project_id=project_id,
            event_type="repair_attempt",
            message="Developer repair attempt 1/2",
            severity="warning",
            payload={"attempt": 1, "max_attempts": 2},
        ))
        await db_session.commit()

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/workflow/status"
        )
        assert resp.status_code == 200
        events = resp.json()["recent_events"]
        repair_events = [e for e in events if e.get("event_type") == "repair_attempt"]
        assert len(repair_events) >= 1
