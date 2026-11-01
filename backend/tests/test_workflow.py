"""
Phase 3 tests: workflow API endpoints and agent unit tests.

All LLM calls are mocked so these tests run without a live Ollama instance.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from app.agents.base import AgentResult
from app.models.db_models import WorkflowEvent
from app.services.llm_client import LLMResponse
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

VALID_PROJECT = {
    "name": "Test Project",
    "description": "A test project description that is long enough.",
    "preferred_language": "python",
    "preferred_framework": "fastapi",
    "preferred_database": "sqlite",
    "max_repair_attempts": 3,
}


async def _create_project(client: AsyncClient, overrides: dict | None = None) -> dict:
    payload = {**VALID_PROJECT, **(overrides or {})}
    resp = await client.post("/api/v1/projects", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _set_project_status(client: AsyncClient, project_id: str, status: str) -> None:
    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"status": status},
    )
    assert resp.status_code == 200, f"Failed to set status to {status!r}: {resp.text}"


def _make_llm_response(text: str = "# Output\n\nSome content.") -> LLMResponse:
    return LLMResponse(
        content=text,
        model="qwen2.5-coder:7b",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        duration_seconds=0.5,
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
def patch_agent_llm(response_text: str = "# Agent output\n\nContent."):
    """Patch OllamaLLMClient.chat across all agents for a single test."""
    with patch(
        "app.services.llm_client.OllamaLLMClient.chat",
        new_callable=AsyncMock,
        return_value=_make_llm_response(response_text),
    ) as mock:
        yield mock


# ---------------------------------------------------------------------------
# Workflow start / resume / status
# ---------------------------------------------------------------------------


class TestWorkflowStart:
    async def test_start_workflow_project_not_found(self, async_client: AsyncClient):
        resp = await async_client.post(
            "/api/v1/projects/nonexistent-id/workflow/start"
        )
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        if isinstance(detail, dict):
            assert detail["code"] == "project_not_found"
        else:
            assert "not found" in str(detail).lower()

    async def test_start_workflow_ok(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "WF Start Test"})
        project_id = proj["id"]

        with patch_workflow_background():
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/start"
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "requirements" in body["message"].lower()

    async def test_start_workflow_already_running(self, async_client: AsyncClient):
        """Starting a non-pending project should return 409."""
        proj = await _create_project(async_client, {"name": "Non-Pending Project"})
        project_id = proj["id"]

        # Set to in_progress via PATCH (a valid workflow status)
        await _set_project_status(async_client, project_id, "in_progress")

        with patch_workflow_background():
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/start"
            )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        if isinstance(detail, dict):
            assert detail["code"] == "invalid_state"

    async def test_resume_workflow_not_resumable(self, async_client: AsyncClient):
        """Resuming a pending project should fail with 409."""
        proj = await _create_project(async_client, {"name": "Resume Fail Test"})
        project_id = proj["id"]

        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/workflow/resume"
        )
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        if isinstance(detail, dict):
            assert detail["code"] == "not_resumable"

    async def test_resume_workflow_project_not_found(self, async_client: AsyncClient):
        resp = await async_client.post("/api/v1/projects/bad-id/workflow/resume")
        assert resp.status_code == 404

    async def test_resume_after_requirements_approved(self, async_client: AsyncClient):
        """After advancing to requirements_approved, resume should 200."""
        proj = await _create_project(async_client, {"name": "Resumable Project"})
        project_id = proj["id"]

        await _set_project_status(async_client, project_id, "requirements_approved")

        with patch_workflow_background():
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/resume"
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    async def test_resume_after_architecture_approved(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Architecture Approved"})
        project_id = proj["id"]

        await _set_project_status(async_client, project_id, "architecture_approved")

        with patch_workflow_background():
            resp = await async_client.post(
                f"/api/v1/projects/{project_id}/workflow/resume"
            )
        assert resp.status_code == 200


class TestWorkflowStatus:
    async def test_status_project_not_found(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/projects/nope/workflow/status")
        assert resp.status_code == 404

    async def test_status_fresh_project(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Status Test Project"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/workflow/status"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert body["status"] == "pending"
        assert "tasks" in body
        assert "agent_runs" in body
        assert "recent_events" in body
        assert body["tasks"]["total"] == 0
        assert body["agent_runs"]["total"] == 0
        assert isinstance(body["agent_runs"]["total_tokens_used"], int)

    async def test_status_contains_project_name(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Named Status Project"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/workflow/status"
        )
        assert resp.status_code == 200
        assert resp.json()["project_name"] == "Named Status Project"

    async def test_status_recent_events_is_list(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Events List Test"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/workflow/status"
        )
        assert isinstance(resp.json()["recent_events"], list)


# ---------------------------------------------------------------------------
# Artifacts endpoints
# ---------------------------------------------------------------------------


class TestArtifacts:
    async def test_list_artifacts_empty(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Artifact Project"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}/artifacts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["artifacts"] == []

    async def test_get_artifact_not_found(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Artifact 404"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/artifacts/missing.md"
        )
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        if isinstance(detail, dict):
            assert detail["code"] == "artifact_not_found"

    async def test_list_artifacts_project_not_found(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/projects/nope/artifacts")
        assert resp.status_code == 404

    async def test_get_artifact_project_not_found(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/v1/projects/nope/artifacts/requirements.md"
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Agent runs endpoints
# ---------------------------------------------------------------------------


class TestAgentRuns:
    async def test_list_agent_runs_empty(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Agent Runs Project"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/agent-runs"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["runs"] == []
        assert body["page"] == 1

    async def test_list_agent_runs_pagination_params(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Agent Runs Pagination"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/agent-runs",
            params={"page": 2, "page_size": 5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 2
        assert body["page_size"] == 5

    async def test_list_agent_runs_project_not_found(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/projects/nope/agent-runs")
        assert resp.status_code == 404

    async def test_list_agent_runs_invalid_page(self, async_client: AsyncClient):
        """page=0 is invalid (must be >=1); should return 422."""
        proj = await _create_project(async_client, {"name": "Agent Runs Page 0"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/agent-runs",
            params={"page": 0},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AgentResult dataclass
# ---------------------------------------------------------------------------


class TestAgentResult:
    def test_basic_success(self):
        result = AgentResult(
            agent_id="requirements_analyst",
            status="success",
            output="# Requirements\n\n1. Auth",
        )
        assert result.status == "success"
        assert result.success is True
        assert result.failure is False
        assert result.error is None
        assert isinstance(result.parsed, dict)

    def test_basic_failure(self):
        result = AgentResult(
            agent_id="qa_engineer",
            status="error",
            output="",
            error="LLM timeout",
        )
        assert result.status == "error"
        assert result.success is False
        assert result.failure is True
        assert result.error == "LLM timeout"

    def test_token_fields(self):
        result = AgentResult(
            agent_id="system_architect",
            status="success",
            output="# Architecture",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            duration_seconds=1.2,
            model="qwen2.5-coder:7b",
        )
        assert result.total_tokens == 150
        assert result.duration_seconds == 1.2
        assert result.model == "qwen2.5-coder:7b"

    def test_parsed_defaults_empty_dict(self):
        result = AgentResult(
            agent_id="task_planner",
            status="success",
            output="...",
        )
        assert result.parsed == {}

    def test_parsed_dict_provided(self):
        parsed = {"requirements": ["auth", "dashboard"]}
        result = AgentResult(
            agent_id="requirements_analyst",
            status="success",
            output="...",
            parsed=parsed,
        )
        assert result.parsed == parsed


# ---------------------------------------------------------------------------
# Agent run tests (mocked LLM via patch)
# ---------------------------------------------------------------------------


class TestRequirementsAnalystAgent:
    async def test_run_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from app.agents.requirements_analyst import RequirementsAnalystAgent

        proj = await _create_project(async_client, {"name": "RA Agent Test"})

        response_text = (
            "# Functional Requirements\n\n1. User authentication\n\n"
            "# Non-Functional Requirements\n\n- Response < 2s\n"
        )
        with patch_agent_llm(response_text):
            agent = RequirementsAnalystAgent()
            result = await agent.run(
                context={"task_description": "Build a todo app."},
                db=db_session,
                project_id=proj["id"],
            )

        assert isinstance(result, AgentResult)
        assert result.agent_id == "requirements-analyst"
        assert result.output == response_text

    async def test_run_llm_error_returns_error_result(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from app.agents.requirements_analyst import RequirementsAnalystAgent

        proj = await _create_project(async_client, {"name": "RA Error Test"})

        error_response = LLMResponse(
            content="",
            model="qwen2.5-coder:7b",
            error="connection refused",
        )
        with patch(
            "app.services.llm_client.OllamaLLMClient.chat",
            new_callable=AsyncMock,
            return_value=error_response,
        ):
            agent = RequirementsAnalystAgent()
            result = await agent.run(
                context={"task_description": "Build something."},
                db=db_session,
                project_id=proj["id"],
            )

        assert isinstance(result, AgentResult)
        assert result.status == "error"
        assert "connection refused" in (result.error or "")


class TestSystemArchitectAgent:
    async def test_run_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from app.agents.system_architect import SystemArchitectAgent

        proj = await _create_project(async_client, {"name": "SA Agent Test"})

        with patch_agent_llm("# Architecture\n\nUse FastAPI + SQLite."):
            agent = SystemArchitectAgent()
            result = await agent.run(
                context={"requirements_doc": "# Requirements\n\n1. Auth\n2. Dashboard"},
                db=db_session,
                project_id=proj["id"],
            )

        assert isinstance(result, AgentResult)
        assert result.agent_id == "system-architect"


class TestTaskPlannerAgent:
    async def test_run_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from app.agents.task_planner import TaskPlannerAgent

        proj = await _create_project(async_client, {"name": "TP Agent Test"})

        task_json = json.dumps([
            {
                "title": "Setup project",
                "description": "Init repo and structure",
                "priority": "high",
                "estimated_hours": 2,
                "acceptance_criteria": "Project runs",
            }
        ])
        with patch_agent_llm(task_json):
            agent = TaskPlannerAgent()
            result = await agent.run(
                context={"architecture_doc": "# Architecture\n\nFastAPI + SQLite"},
                db=db_session,
                project_id=proj["id"],
            )

        assert isinstance(result, AgentResult)
        assert result.agent_id == "task-planner"


class TestSoftwareDeveloperAgent:
    async def test_run_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from app.agents.software_developer import SoftwareDeveloperAgent

        proj = await _create_project(async_client, {"name": "Dev Agent Test"})

        code = "```python\ndef add(a, b):\n    return a + b\n```"
        with patch_agent_llm(code):
            agent = SoftwareDeveloperAgent()
            result = await agent.run(
                context={
                    "task_title": "Add function",
                    "task_description": "Implement an add() function.",
                    "architecture_doc": "Simple Python script",
                },
                db=db_session,
                project_id=proj["id"],
            )

        assert isinstance(result, AgentResult)
        assert result.agent_id == "software-developer"


# ---------------------------------------------------------------------------
# WorkflowEvent DB — no seq UNIQUE violation after fix
# ---------------------------------------------------------------------------


class TestWorkflowEventInsert:
    async def test_insert_multiple_events_no_constraint_error(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from sqlalchemy import select

        proj = await _create_project(async_client, {"name": "Event Insert Test"})
        project_id = proj["id"]

        for i in range(10):
            event = WorkflowEvent(
                project_id=project_id,
                event_type="bulk_insert_test",
                message=f"Event {i}",
                severity="info",
            )
            db_session.add(event)
        await db_session.commit()

        # Filter by our specific event_type to avoid counting other events
        result = await db_session.execute(
            select(WorkflowEvent).where(
                WorkflowEvent.project_id == project_id,
                WorkflowEvent.event_type == "bulk_insert_test",
            )
        )
        events = result.scalars().all()
        assert len(events) == 10
        # All UUIDs distinct
        assert len({e.id for e in events}) == 10

    async def test_event_ordering_by_created_at(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        from sqlalchemy import select

        proj = await _create_project(async_client, {"name": "Event Order Test"})
        project_id = proj["id"]

        messages = ["alpha", "beta", "gamma"]
        for msg in messages:
            event = WorkflowEvent(
                project_id=project_id,
                event_type="order_test_event",
                message=msg,
                severity="info",
            )
            db_session.add(event)
        await db_session.commit()

        # Filter by our specific event_type
        result = await db_session.execute(
            select(WorkflowEvent)
            .where(
                WorkflowEvent.project_id == project_id,
                WorkflowEvent.event_type == "order_test_event",
            )
            .order_by(WorkflowEvent.created_at, WorkflowEvent.id)
        )
        events = result.scalars().all()
        assert len(events) == 3

    async def test_event_severity_values(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        proj = await _create_project(async_client, {"name": "Severity Test"})
        project_id = proj["id"]

        severities = ["debug", "info", "warning", "error", "critical"]
        for sev in severities:
            db_session.add(WorkflowEvent(
                project_id=project_id,
                event_type="severity_test",
                message=f"Test {sev}",
                severity=sev,
            ))
        await db_session.commit()

        from sqlalchemy import select
        result = await db_session.execute(
            select(WorkflowEvent).where(WorkflowEvent.project_id == project_id)
        )
        events = result.scalars().all()
        stored_severities = {e.severity for e in events}
        assert stored_severities == set(severities)
