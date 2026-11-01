"""
Comprehensive unit and integration tests for Terminal and Command Execution Center.
"""

from __future__ import annotations

import pytest
from app.models.db_models import Project
from app.terminal.command_policy import CommandCategory, CommandPolicyEngine, CommandSafetyLevel
from app.terminal.terminal_security import TerminalSecurity
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def sample_project(db_session: AsyncSession) -> Project:
    proj = Project(
        id="term-proj-001",
        name="Terminal Test Project",
        description="Testing integrated terminal executions",
        status="active",
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


@pytest.mark.asyncio
async def test_terminal_security_status(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/terminal/security/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "docker" in data
    assert "isolation_tier" in data
    assert "supported_shells" in data
    assert "powershell" in data["supported_shells"]


def test_command_policy_engine() -> None:
    # 1. Safe command
    safe_res = CommandPolicyEngine.evaluate("python -m pytest tests/ -v")
    assert safe_res.is_allowed is True
    assert safe_res.safety_level == CommandSafetyLevel.SAFE
    assert safe_res.category == CommandCategory.TEST

    # 2. Blocked commands
    blocked_res1 = CommandPolicyEngine.evaluate("rmdir /s /q c:\\")
    assert blocked_res1.is_allowed is False
    assert blocked_res1.safety_level == CommandSafetyLevel.BLOCKED

    blocked_res2 = CommandPolicyEngine.evaluate("format D: /fs:NTFS")
    assert blocked_res2.is_allowed is False

    blocked_res3 = CommandPolicyEngine.evaluate("rm -rf /")
    assert blocked_res3.is_allowed is False

    # 3. Confirmation required
    conf_res = CommandPolicyEngine.evaluate("git push origin main --force")
    assert conf_res.is_allowed is True
    assert conf_res.safety_level == CommandSafetyLevel.REQUIRES_CONFIRMATION


def test_terminal_security_redaction() -> None:
    raw = "Connecting to git with token ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    redacted = TerminalSecurity.redact(raw)
    assert "[REDACTED]" in redacted
    assert "1234567890" not in redacted


@pytest.mark.asyncio
async def test_terminal_sessions_auto_provisioning(
    async_client: AsyncClient, sample_project: Project
) -> None:
    resp = await async_client.get(f"/api/v1/terminal/sessions?project_id={sample_project.id}")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 5
    names = [s["name"] for s in sessions]
    assert "Main Terminal" in names
    assert "Developer Agent" in names
    assert "QA Execution" in names
    assert "Security Scanner" in names
    assert "Git Operations" in names


@pytest.mark.asyncio
async def test_terminal_create_custom_session(
    async_client: AsyncClient, sample_project: Project
) -> None:
    payload = {
        "project_id": sample_project.id,
        "name": "Custom Build Tab",
        "shell_type": "powershell",
    }
    resp = await async_client.post("/api/v1/terminal/sessions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Custom Build Tab"
    assert data["project_id"] == sample_project.id
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_terminal_update_and_close_session(
    async_client: AsyncClient, sample_project: Project
) -> None:
    # 1. Create
    resp = await async_client.post(
        "/api/v1/terminal/sessions",
        json={"project_id": sample_project.id, "name": "Temporary Tab"},
    )
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    # 2. Update / Rename
    patch_resp = await async_client.patch(
        f"/api/v1/terminal/sessions/{session_id}",
        json={"name": "Renamed Tab"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed Tab"

    # 3. Get single
    get_resp = await async_client.get(f"/api/v1/terminal/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Renamed Tab"

    # 4. Close
    del_resp = await async_client.delete(f"/api/v1/terminal/sessions/{session_id}")
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_terminal_execute_command(async_client: AsyncClient, sample_project: Project) -> None:
    # Get active session
    sessions_resp = await async_client.get(
        f"/api/v1/terminal/sessions?project_id={sample_project.id}"
    )
    session_id = sessions_resp.json()[0]["id"]

    exec_payload = {
        "command": "python -c \"print('AgentForge Terminal Execution Succeeded')\"",
        "timeout_seconds": 15,
        "agent_id": "developer",
    }
    resp = await async_client.post(
        f"/api/v1/terminal/sessions/{session_id}/execute",
        json=exec_payload,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["exit_code"] == 0
    assert data["status"] == "completed"
    assert data["agent_id"] == "developer"
    assert "AgentForge Terminal Execution Succeeded" in (data["stdout_preview"] or "")


@pytest.mark.asyncio
async def test_terminal_execute_blocked_command(
    async_client: AsyncClient, sample_project: Project
) -> None:
    sessions_resp = await async_client.get(
        f"/api/v1/terminal/sessions?project_id={sample_project.id}"
    )
    session_id = sessions_resp.json()[0]["id"]

    exec_payload = {
        "command": "rmdir /s /q c:\\",
    }
    resp = await async_client.post(
        f"/api/v1/terminal/sessions/{session_id}/execute",
        json=exec_payload,
    )
    assert resp.status_code == 403
    assert "security rule" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_terminal_interrupt_and_clear(
    async_client: AsyncClient, sample_project: Project
) -> None:
    sessions_resp = await async_client.get(
        f"/api/v1/terminal/sessions?project_id={sample_project.id}"
    )
    session_id = sessions_resp.json()[0]["id"]

    # Interrupt
    int_resp = await async_client.post(f"/api/v1/terminal/sessions/{session_id}/interrupt")
    assert int_resp.status_code == 200

    # Clear
    clr_resp = await async_client.post(f"/api/v1/terminal/sessions/{session_id}/clear")
    assert clr_resp.status_code == 200
    assert clr_resp.json()["cleared"] is True


@pytest.mark.asyncio
async def test_terminal_history_and_details(
    async_client: AsyncClient, sample_project: Project
) -> None:
    sessions_resp = await async_client.get(
        f"/api/v1/terminal/sessions?project_id={sample_project.id}"
    )
    session_id = sessions_resp.json()[0]["id"]

    # Execute a command to produce history
    await async_client.post(
        f"/api/v1/terminal/sessions/{session_id}/execute",
        json={"command": "python -c \"print('History Test')\""},
    )

    hist_resp = await async_client.get(f"/api/v1/terminal/sessions/{session_id}/history")
    assert hist_resp.status_code == 200
    cmds = hist_resp.json()
    assert len(cmds) > 0

    cmd_id = cmds[0]["id"]
    det_resp = await async_client.get(f"/api/v1/terminal/commands/{cmd_id}")
    assert det_resp.status_code == 200
    assert det_resp.json()["id"] == cmd_id


@pytest.mark.asyncio
async def test_terminal_processes_and_consoles(
    async_client: AsyncClient, sample_project: Project
) -> None:
    proc_resp = await async_client.get(f"/api/v1/terminal/processes?project_id={sample_project.id}")
    assert proc_resp.status_code == 200
    assert isinstance(proc_resp.json(), list)

    cons_resp = await async_client.get(
        f"/api/v1/terminal/consoles/qa?project_id={sample_project.id}"
    )
    assert cons_resp.status_code == 200
    assert cons_resp.json()["console_type"] == "qa"


@pytest.mark.asyncio
async def test_terminal_export(async_client: AsyncClient, sample_project: Project) -> None:
    sessions_resp = await async_client.get(
        f"/api/v1/terminal/sessions?project_id={sample_project.id}"
    )
    session_id = sessions_resp.json()[0]["id"]

    # Text export
    txt_resp = await async_client.get(f"/api/v1/terminal/sessions/{session_id}/export?format=txt")
    assert txt_resp.status_code == 200

    # JSON export
    json_resp = await async_client.get(f"/api/v1/terminal/sessions/{session_id}/export?format=json")
    assert json_resp.status_code == 200

    # Markdown export
    md_resp = await async_client.get(
        f"/api/v1/terminal/sessions/{session_id}/export?format=markdown"
    )
    assert md_resp.status_code == 200


@pytest.mark.asyncio
async def test_terminal_stream_output(async_client: AsyncClient, sample_project: Project) -> None:
    sessions_resp = await async_client.get(
        f"/api/v1/terminal/sessions?project_id={sample_project.id}"
    )
    session_id = sessions_resp.json()[0]["id"]

    stream_resp = await async_client.get(
        f"/api/v1/terminal/sessions/{session_id}/stream?max_events=1"
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")


def test_terminal_cwd_boundary_enforcement(sample_project: Project) -> None:
    # Attempting to break out with path traversal should be rejected
    with pytest.raises(ValueError, match="outside project workspace root"):
        TerminalSecurity.resolve_and_verify_cwd(sample_project.id, "../../windows/system32")


@pytest.mark.asyncio
async def test_terminal_command_policy_categories() -> None:
    assert CommandPolicyEngine._detect_category("git status") == CommandCategory.GIT
    assert CommandPolicyEngine._detect_category("pip install fastapi") == CommandCategory.BUILD
    assert CommandPolicyEngine._detect_category("pytest -v") == CommandCategory.TEST
    assert CommandPolicyEngine._detect_category("bandit -r app/") == CommandCategory.SECURITY
    assert CommandPolicyEngine._detect_category("python script.py") == CommandCategory.GENERAL
