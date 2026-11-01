"""
Tests for Advanced Monitoring & Observability Architecture.

Tests cover:
- Redaction of sensitive credentials, tokens, and payloads
- Correlation ID tracking across spans
- EventService emission, multi-dimensional filtering, search, and pagination
- SOC summary metrics and agent activity aggregation
- LLM and tool execution telemetry
- Incident intelligence and security event audit logs
- Log export formats (JSON, CSV, Markdown, TXT)
- Real-time SSE streaming endpoints
"""

from __future__ import annotations

from app.logging.correlation import (
    get_current_trace_id,
    trace_context,
)
from app.logging.event_service import EventService
from app.logging.redaction import redact_metadata, redact_string
from app.models.db_models import ModelUsageStat, Project
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_test_project(db: AsyncSession, name: str = "Monitoring Project") -> Project:
    project = Project(
        name=name,
        description="A project for monitoring and observability testing.",
        status="active",
        preferred_language="python",
        preferred_framework="fastapi",
        preferred_database="sqlite",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


class TestRedactionAndCorrelation:
    """Test security redaction and correlation ID tracking."""

    def test_redact_aws_key(self):
        text = "Failed with AWS key AKIAIOSFODNN7EXAMPLE in query."
        redacted = redact_string(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_private_key(self):
        key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----"
        redacted = redact_string(key)
        assert "MIIEowIBAAKCAQEA0" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_metadata_dict(self):
        meta = {
            "user": "developer",
            "password": "SuperSecretPassword123!",
            "api_key": "ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            "nested": {
                "auth_token": "secret_token_val",
                "safe_info": "visible_data",
            },
        }
        clean = redact_metadata(meta)
        assert clean["password"] == "[REDACTED]"
        assert clean["api_key"] == "[REDACTED]"
        assert clean["nested"]["auth_token"] == "[REDACTED]"
        assert clean["nested"]["safe_info"] == "visible_data"

    def test_trace_context_manager(self):
        assert get_current_trace_id() is None
        with trace_context() as tid:
            assert len(tid) == 16
            assert get_current_trace_id() == tid
        assert get_current_trace_id() is None


class TestEventService:
    """Test EventService database operations and aggregations."""

    async def test_emit_event_redacts_message_and_payload(self, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "Redaction Test")
        event = await EventService.emit_event(
            db_session,
            project_id=proj.id,
            message="Connecting with token ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            severity="info",
            payload={"secret_key": "my_db_secret_key_123", "action": "test"},
        )
        assert "[REDACTED]" in event.message
        assert "1234567890abcdef" not in event.message
        assert event.payload["secret_key"] == "[REDACTED]"
        assert event.payload["action"] == "test"

    async def test_filtered_events_search_and_pagination(self, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "Search Test")

        # Emit 5 events
        for i in range(5):
            await EventService.emit_event(
                db_session,
                project_id=proj.id,
                message=f"Deployment step {i} executed",
                severity="success" if i % 2 == 0 else "warning",
                source="software-developer",
                category="tool_execution",
            )
        await db_session.commit()

        # Filter by severity
        res = await EventService.get_filtered_events(
            db_session, project_id=proj.id, severity="success", page=1, page_size=10
        )
        assert res["total"] == 3
        assert len(res["items"]) == 3

        # Search term
        search_res = await EventService.get_filtered_events(
            db_session, project_id=proj.id, search="step 3"
        )
        assert search_res["total"] == 1
        assert "step 3" in search_res["items"][0]["message"]

    async def test_monitoring_stats_aggregation(self, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "Stats Test")

        severities = ["success", "success", "warning", "error", "critical"]
        for sev in severities:
            await EventService.emit_event(
                db_session,
                project_id=proj.id,
                message=f"Event with {sev}",
                severity=sev,
            )
        await db_session.commit()

        stats = await EventService.get_monitoring_stats(db_session, project_id=proj.id)
        assert stats["total_events"] == 5
        assert stats["successful_operations"] == 2
        assert stats["warnings"] == 1
        assert stats["errors"] == 1
        assert stats["critical_events"] == 1

    async def test_agent_monitoring_returns_all_agents(self, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "Agents Monitor")
        agents = await EventService.get_agent_monitoring(db_session, project_id=proj.id)
        assert len(agents) == 7
        agent_ids = {a["agent_id"] for a in agents}
        assert "requirements-analyst" in agent_ids
        assert "software-developer" in agent_ids
        assert "security-engineer" in agent_ids

    async def test_llm_intelligence_aggregation(self, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "LLM Intel")

        db_session.add(
            ModelUsageStat(
                project_id=proj.id,
                model_name="qwen2.5-coder:7b",
                agent_role="software-developer",
                duration_seconds=1.5,
                token_count_in=100,
                token_count_out=50,
                success=True,
            )
        )
        db_session.add(
            ModelUsageStat(
                project_id=proj.id,
                model_name="qwen2.5-coder:7b",
                agent_role="qa-engineer",
                duration_seconds=2.5,
                token_count_in=150,
                token_count_out=75,
                success=False,
                error_type="Timeout",
            )
        )
        await db_session.commit()

        intel = await EventService.get_llm_intelligence(db_session, project_id=proj.id)
        assert intel["total_requests"] == 2
        assert intel["successful_requests"] == 1
        assert intel["failed_requests"] == 1
        assert intel["average_response_time"] == 2.0
        assert intel["slowest_request_time"] == 2.5

    async def test_export_logs_csv_and_markdown(self, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "Export Test")
        await EventService.emit_event(
            db_session,
            project_id=proj.id,
            message="Export sample event",
            severity="info",
            source="system",
        )
        await db_session.commit()

        # CSV export
        csv_data, media = await EventService.export_logs(
            db_session, format_type="csv", project_id=proj.id
        )
        assert media == "text/csv"
        assert "Export sample event" in csv_data

        # Markdown export
        md_data, media_md = await EventService.export_logs(
            db_session, format_type="markdown", project_id=proj.id
        )
        assert media_md == "text/markdown"
        assert "# AgentForge System Intelligence & Log Report" in md_data


class TestMonitoringAPIEndpoints:
    """Test HTTP API endpoints under /api/v1/monitoring/."""

    async def test_get_events_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "API Events")
        await EventService.emit_event(
            db_session,
            project_id=proj.id,
            message="API endpoint test event",
            severity="success",
        )
        await db_session.commit()

        resp = await async_client.get(
            "/api/v1/monitoring/events",
            params={"project_id": proj.id, "severity": "success"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] == 1
        assert body["items"][0]["message"] == "API endpoint test event"

    async def test_get_stats_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "API Stats")
        resp = await async_client.get(
            "/api/v1/monitoring/stats",
            params={"project_id": proj.id},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total_events" in body
        assert "successful_operations" in body
        assert "active_agents" in body

    async def test_get_agents_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/monitoring/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 7

    async def test_get_llm_requests_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/monitoring/llm-requests")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_requests" in body
        assert "records" in body

    async def test_get_tools_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/monitoring/tools")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_get_incidents_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/monitoring/incidents")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_get_security_events_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/monitoring/security-events")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_export_endpoint(self, async_client: AsyncClient, db_session: AsyncSession):
        proj = await _create_test_project(db_session, "Export API")
        await EventService.emit_event(
            db_session,
            project_id=proj.id,
            message="Export API event",
            severity="info",
        )
        await db_session.commit()

        resp = await async_client.get(
            "/api/v1/monitoring/export",
            params={"project_id": proj.id, "format": "json"},
        )
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_stream_monitoring_events_endpoint(self, async_client: AsyncClient):
        resp = await async_client.get(
            "/api/v1/monitoring/stream",
            params={"max_iterations": 1},
            headers={"Accept": "text/event-stream"},
        )
        assert resp.status_code == 200
