"""
Tests for project CRUD endpoints.

Covers:
  - Project creation with valid and invalid payloads.
  - Project retrieval (existing and non-existing).
  - Project listing with pagination.
  - Project status update.
  - Project cancellation.
  - Requirements approval gate (approve and reject).
  - Architecture approval gate.
  - Task creation and listing.
  - Task dependency validation.
  - Structured error responses.
  - Database persistence within a test.
"""

from __future__ import annotations

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
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
    """Helper to create a project and return the response JSON."""
    payload = {**VALID_PROJECT, **(overrides or {})}
    response = await client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Project creation
# ---------------------------------------------------------------------------


class TestProjectCreate:
    async def test_create_project_returns_201(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/projects", json=VALID_PROJECT)
        assert response.status_code == 201

    async def test_create_project_returns_id(self, async_client: AsyncClient):
        data = await _create_project(async_client)
        assert "id" in data
        assert len(data["id"]) == 36  # UUID4 format

    async def test_create_project_status_is_pending(self, async_client: AsyncClient):
        data = await _create_project(async_client)
        assert data["status"] == "pending"

    async def test_create_project_persists_fields(self, async_client: AsyncClient):
        data = await _create_project(async_client)
        assert data["name"] == VALID_PROJECT["name"]
        assert data["description"] == VALID_PROJECT["description"]
        assert data["preferred_language"] == "python"
        assert data["max_repair_attempts"] == 3

    async def test_create_project_missing_name_returns_422(self, async_client: AsyncClient):
        payload = {**VALID_PROJECT}
        del payload["name"]
        response = await async_client.post("/api/v1/projects", json=payload)
        assert response.status_code == 422

    async def test_create_project_empty_name_returns_422(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/projects", json={**VALID_PROJECT, "name": ""})
        assert response.status_code == 422

    async def test_create_project_short_description_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/projects", json={**VALID_PROJECT, "description": "short"}
        )
        assert response.status_code == 422

    async def test_create_project_invalid_language_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/projects",
            json={**VALID_PROJECT, "preferred_language": "brainfuck"},
        )
        assert response.status_code == 422

    async def test_create_project_invalid_repair_attempts_returns_422(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/api/v1/projects", json={**VALID_PROJECT, "max_repair_attempts": 0}
        )
        assert response.status_code == 422

    async def test_create_project_no_optional_fields(self, async_client: AsyncClient):
        """Minimal payload — only required fields."""
        response = await async_client.post(
            "/api/v1/projects",
            json={"name": "Minimal", "description": "A minimal project description here."},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["preferred_language"] is None


# ---------------------------------------------------------------------------
# Project retrieval
# ---------------------------------------------------------------------------


class TestProjectGet:
    async def test_get_existing_project(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.get(f"/api/v1/projects/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    async def test_get_nonexistent_project_returns_404(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/projects/does-not-exist")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_get_project_returns_full_detail(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.get(f"/api/v1/projects/{created['id']}")
        data = response.json()
        assert "description" in data
        assert "created_at" in data
        assert "updated_at" in data


# ---------------------------------------------------------------------------
# Project listing
# ---------------------------------------------------------------------------


class TestProjectList:
    async def test_list_projects_empty(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_projects_returns_created(self, async_client: AsyncClient):
        await _create_project(async_client)
        response = await async_client.get("/api/v1/projects")
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    async def test_list_projects_pagination(self, async_client: AsyncClient):
        for i in range(5):
            await _create_project(async_client, {"name": f"Project {i}"})

        response = await async_client.get("/api/v1/projects?page=1&page_size=3")
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["total_pages"] == 2

    async def test_list_projects_page_2(self, async_client: AsyncClient):
        for i in range(5):
            await _create_project(async_client, {"name": f"Project {i}"})

        response = await async_client.get("/api/v1/projects?page=2&page_size=3")
        data = response.json()
        assert len(data["items"]) == 2

    async def test_list_projects_status_filter(self, async_client: AsyncClient):
        project = await _create_project(async_client)
        # Cancel the project
        await async_client.delete(f"/api/v1/projects/{project['id']}")

        # Filter by cancelled
        response = await async_client.get("/api/v1/projects?status=cancelled")
        data = response.json()
        assert data["total"] == 1

        # Filter by pending — should be 0
        response = await async_client.get("/api/v1/projects?status=pending")
        data = response.json()
        assert data["total"] == 0

    async def test_list_pagination_fields_present(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/projects")
        data = response.json()
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data


# ---------------------------------------------------------------------------
# Project cancellation
# ---------------------------------------------------------------------------


class TestProjectCancel:
    async def test_cancel_project_returns_ok(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.delete(f"/api/v1/projects/{created['id']}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    async def test_cancel_sets_status_cancelled(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        await async_client.delete(f"/api/v1/projects/{created['id']}")

        response = await async_client.get(f"/api/v1/projects/{created['id']}")
        assert response.json()["status"] == "cancelled"

    async def test_cancel_nonexistent_returns_404(self, async_client: AsyncClient):
        response = await async_client.delete("/api/v1/projects/ghost-id")
        assert response.status_code == 404

    async def test_cancel_already_cancelled_returns_409(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        await async_client.delete(f"/api/v1/projects/{created['id']}")
        # Second cancellation
        response = await async_client.delete(f"/api/v1/projects/{created['id']}")
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Requirements approval gate
# ---------------------------------------------------------------------------


class TestRequirementsApproval:
    async def test_approve_requirements_updates_status(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        pid = created["id"]

        # Manually put project into requirements_review state
        patch_resp = await async_client.patch(
            f"/api/v1/projects/{pid}", json={"status": "requirements_review"}
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["status"] == "requirements_review"

        response = await async_client.post(
            f"/api/v1/projects/{pid}/requirements/approve",
            json={"approved": True, "reviewer_notes": "Looks good"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        detail = await async_client.get(f"/api/v1/projects/{pid}")
        assert detail.json()["status"] == "requirements_approved"

    async def test_reject_requirements_sets_revision_status(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        pid = created["id"]

        patch_resp = await async_client.patch(
            f"/api/v1/projects/{pid}", json={"status": "requirements_review"}
        )
        assert patch_resp.status_code == 200, patch_resp.text

        response = await async_client.post(
            f"/api/v1/projects/{pid}/requirements/approve",
            json={"approved": False, "reviewer_notes": "Needs more detail"},
        )
        assert response.status_code == 200

        detail = await async_client.get(f"/api/v1/projects/{pid}")
        assert detail.json()["status"] == "requirements_revision"

    async def test_approve_requirements_wrong_state_returns_409(self, async_client: AsyncClient):
        """Cannot approve requirements when project is in 'active' status."""
        created = await _create_project(async_client)
        pid = created["id"]
        patch_resp = await async_client.patch(f"/api/v1/projects/{pid}", json={"status": "active"})
        assert patch_resp.status_code == 200, patch_resp.text

        response = await async_client.post(
            f"/api/v1/projects/{pid}/requirements/approve",
            json={"approved": True},
        )
        assert response.status_code == 409

    async def test_approve_requirements_nonexistent_project_returns_404(
        self, async_client: AsyncClient
    ):
        response = await async_client.post(
            "/api/v1/projects/ghost/requirements/approve",
            json={"approved": True},
        )
        assert response.status_code == 404

    async def test_approve_from_pending_status(self, async_client: AsyncClient):
        """Approving from 'pending' status should also work."""
        created = await _create_project(async_client)
        pid = created["id"]

        response = await async_client.post(
            f"/api/v1/projects/{pid}/requirements/approve",
            json={"approved": True},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Architecture approval gate
# ---------------------------------------------------------------------------


class TestArchitectureApproval:
    async def test_approve_architecture_updates_status(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        pid = created["id"]

        patch_resp = await async_client.patch(
            f"/api/v1/projects/{pid}", json={"status": "architecture_review"}
        )
        assert patch_resp.status_code == 200, patch_resp.text
        assert patch_resp.json()["status"] == "architecture_review"

        response = await async_client.post(
            f"/api/v1/projects/{pid}/architecture/approve",
            json={"approved": True},
        )
        assert response.status_code == 200
        detail = await async_client.get(f"/api/v1/projects/{pid}")
        assert detail.json()["status"] == "architecture_approved"

    async def test_architecture_approval_wrong_state_returns_409(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.post(
            f"/api/v1/projects/{created['id']}/architecture/approve",
            json={"approved": True},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Task management
# ---------------------------------------------------------------------------


class TestTaskManagement:
    async def test_list_tasks_empty(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.get(f"/api/v1/projects/{created['id']}/tasks")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    async def test_create_task_returns_201(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.post(
            f"/api/v1/projects/{created['id']}/tasks",
            json={
                "title": "Implement login endpoint",
                "description": "Create POST /auth/login returning JWT tokens.",
                "priority": "high",
                "assigned_agent": "software-developer",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Implement login endpoint"
        assert data["status"] == "pending"

    async def test_create_task_invalid_priority_returns_422(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.post(
            f"/api/v1/projects/{created['id']}/tasks",
            json={
                "title": "Task",
                "description": "Task description.",
                "priority": "urgent",  # invalid
            },
        )
        assert response.status_code == 422

    async def test_create_task_invalid_agent_returns_422(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.post(
            f"/api/v1/projects/{created['id']}/tasks",
            json={
                "title": "Task",
                "description": "Task description.",
                "assigned_agent": "rogue-agent",  # invalid
            },
        )
        assert response.status_code == 422

    async def test_create_task_nonexistent_project_returns_404(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/projects/ghost/tasks",
            json={"title": "Task", "description": "Task description."},
        )
        assert response.status_code == 404

    async def test_task_dependency_invalid_id_returns_422(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        response = await async_client.post(
            f"/api/v1/projects/{created['id']}/tasks",
            json={
                "title": "Task B",
                "description": "Depends on nonexistent task.",
                "dependency_ids": ["nonexistent-task-id"],
            },
        )
        assert response.status_code == 422

    async def test_task_dependency_valid(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        pid = created["id"]

        # Create first task
        task_a = await async_client.post(
            f"/api/v1/projects/{pid}/tasks",
            json={"title": "Task A", "description": "First task."},
        )
        task_a_id = task_a.json()["id"]

        # Create second task depending on first
        task_b = await async_client.post(
            f"/api/v1/projects/{pid}/tasks",
            json={
                "title": "Task B",
                "description": "Second task.",
                "dependency_ids": [task_a_id],
            },
        )
        assert task_b.status_code == 201

    async def test_list_tasks_returns_created(self, async_client: AsyncClient):
        created = await _create_project(async_client)
        pid = created["id"]

        for i in range(3):
            await async_client.post(
                f"/api/v1/projects/{pid}/tasks",
                json={"title": f"Task {i}", "description": "Task description."},
            )

        response = await async_client.get(f"/api/v1/projects/{pid}/tasks")
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_tasks_for_nonexistent_project_returns_404(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/projects/ghost/tasks")
        assert response.status_code == 404
