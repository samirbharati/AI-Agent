"""
Tests for Phase 5: Workspace management, Git branch isolation, and ExecutionRunner.

Covers:
  - Path traversal security bounds.
  - File read/write/list/delete operations.
  - Per-project Git initialization, branching, and commits.
  - Subprocess execution runner, environment sanitization, timeouts.
  - Python syntax validation.
  - Workspace REST API endpoints.
"""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from app.services.runner import ExecutionRunner
from app.services.workspace import PathTraversalError, WorkspaceService
from httpx import AsyncClient

VALID_PROJECT = {
    "name": "Workspace Test Project",
    "description": "Testing workspace filesystem and git operations.",
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
# WorkspaceService Unit Tests
# ---------------------------------------------------------------------------


class TestWorkspaceService:
    def test_safe_path_resolution(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-proj-123"

            safe_path = ws.resolve_safe_path(project_id, "app/main.py")
            expected = (Path(tmp_dir) / project_id / "app" / "main.py").resolve()
            assert safe_path == expected

    def test_path_traversal_attempts_blocked(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-proj-sec"

            traversal_payloads = [
                "../escape.py",
                "../../etc/passwd",
                "app/../../secret.txt",
                "C:/Windows/System32/calc.exe",
                "/root/file.txt",
            ]

            for payload in traversal_payloads:
                with pytest.raises(PathTraversalError):
                    ws.resolve_safe_path(project_id, payload)

    def test_write_and_read_file(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-io"

            file_info = ws.write_file(
                project_id,
                "src/utils/calc.py",
                "def add(a, b):\n    return a + b\n",
            )
            assert file_info.path == "src/utils/calc.py"
            assert file_info.size_bytes > 0

            # Read back
            content = ws.read_file(project_id, "src/utils/calc.py")
            assert "def add(a, b):" in content

    def test_read_file_not_found(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-missing"

            with pytest.raises(FileNotFoundError):
                ws.read_file(project_id, "nonexistent.py")

    def test_file_exists_and_delete(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-del"

            ws.write_file(project_id, "temp.txt", "to be deleted")
            assert ws.file_exists(project_id, "temp.txt") is True

            deleted = ws.delete_file(project_id, "temp.txt")
            assert deleted is True
            assert ws.file_exists(project_id, "temp.txt") is False

    def test_list_files_filters_ignored(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-list"

            ws.write_file(project_id, "main.py", "print('hello')")
            ws.write_file(project_id, "tests/test_main.py", "def test(): pass")
            ws.write_file(project_id, "__pycache__/main.cpython-311.pyc", "binary")

            files = ws.list_files(project_id)
            paths = [f.path for f in files]

            assert "main.py" in paths
            assert "tests/test_main.py" in paths
            assert not any("__pycache__" in p for p in paths)

    def test_git_init_branch_and_commit(self):
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "test-git"

            init_ok = ws.init_git_repo(project_id)
            assert init_ok is True

            # Create branch
            branch_ok = ws.create_or_checkout_branch(project_id, "feat/auth")
            assert branch_ok is True

            # Write file and commit
            ws.write_file(project_id, "auth.py", "def login(): pass\n")
            commit_hash = ws.commit_all(project_id, "feat: add login")
            assert commit_hash is not None
            assert len(commit_hash) >= 4

            # Status check
            status = ws.get_git_status(project_id)
            assert status["initialized"] is True
            assert status["branch"] == "feat/auth"
            assert len(status["modified"]) == 0
            assert len(status["untracked"]) == 0


# ---------------------------------------------------------------------------
# ExecutionRunner Unit Tests
# ---------------------------------------------------------------------------


class TestExecutionRunner:
    def test_run_command_success(self):
        runner = ExecutionRunner()
        with TemporaryDirectory() as tmp_dir:
            runner.workspace_service = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "runner-test"

            result = runner.run_command(
                project_id,
                [sys.executable, "-c", "print('AgentForge Runner OK')"],
                timeout=10,
            )
            assert result.success is True
            assert result.exit_code == 0
            assert "AgentForge Runner OK" in result.stdout
            assert result.timed_out is False

    def test_sanitize_env(self):
        runner = ExecutionRunner()
        clean = runner._sanitize_env()
        # Ensure standard PATH is present
        assert any(k.upper() == "PATH" for k in clean)
        # Ensure secrets are NOT leaked into runner environment
        for k in clean:
            upper = k.upper()
            assert "SECRET" not in upper
            assert "TOKEN" not in upper
            assert "PASSWORD" not in upper

    def test_run_command_timeout(self):
        runner = ExecutionRunner()
        with TemporaryDirectory() as tmp_dir:
            runner.workspace_service = WorkspaceService(base_dir=Path(tmp_dir))
            project_id = "runner-timeout"

            result = runner.run_command(
                project_id,
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout=1,
            )
            assert result.timed_out is True
            assert result.success is False
            assert "timed out" in result.stderr

    def test_python_syntax_check(self):
        runner = ExecutionRunner()
        with TemporaryDirectory() as tmp_dir:
            ws = WorkspaceService(base_dir=Path(tmp_dir))
            runner.workspace_service = ws
            project_id = "syntax-test"

            # 1. Valid file
            ws.write_file(project_id, "valid.py", "x = 10\ny = 20\nprint(x + y)\n")
            res_valid = runner.check_python_syntax(project_id, "valid.py")
            assert res_valid.success is True

            # 2. Syntax error file
            ws.write_file(project_id, "invalid.py", "def broken(\n  return\n")
            res_invalid = runner.check_python_syntax(project_id, "invalid.py")
            assert res_invalid.success is False
            assert res_invalid.exit_code != 0


# ---------------------------------------------------------------------------
# Workspace REST API Endpoints Tests
# ---------------------------------------------------------------------------


class TestWorkspaceEndpoints:
    async def test_list_files_empty(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Files Test Proj"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}/files")
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert body["total"] == 0
        assert body["files"] == []

    async def test_get_file_content_not_found(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "File 404 Proj"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/files/content",
            params={"path": "missing.py"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "file_not_found"

    async def test_path_traversal_api_rejected(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Traversal Reject Proj"})
        project_id = proj["id"]

        resp = await async_client.get(
            f"/api/v1/projects/{project_id}/files/content",
            params={"path": "../../etc/passwd"},
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "path_traversal"

    async def test_git_status_endpoint(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Git Status Proj"})
        project_id = proj["id"]

        resp = await async_client.get(f"/api/v1/projects/{project_id}/git/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert "initialized" in body

    async def test_execute_runner_endpoint(self, async_client: AsyncClient):
        proj = await _create_project(async_client, {"name": "Runner Exec Proj"})
        project_id = proj["id"]

        resp = await async_client.post(
            f"/api/v1/projects/{project_id}/runner/execute",
            json={
                "command": [sys.executable, "-c", "print('API Execution Test OK')"],
                "timeout": 15,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "API Execution Test OK" in body["stdout"]
