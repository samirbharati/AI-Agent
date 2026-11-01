"""
Tests for health check endpoints.

All tests use a mocked Ollama service — no live Ollama required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

from app.services.ollama_service import OllamaStatus
from httpx import AsyncClient


class TestAppHealth:
    """Tests for GET /api/v1/health."""

    async def test_health_returns_200(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_health_returns_ok_status(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_returns_required_fields(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        data = response.json()
        required = {"status", "version", "environment", "python_version", "platform", "timestamp"}
        assert required.issubset(data.keys())

    async def test_health_environment_is_test(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert data["environment"] == "test"

    async def test_health_version_is_string(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        data = response.json()
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0


class TestOllamaHealth:
    """Tests for GET /api/v1/health/ollama (with mocked Ollama service)."""

    async def test_ollama_health_ok_when_reachable(self, async_client: AsyncClient):
        mock_status = OllamaStatus(
            reachable=True,
            model_available=True,
            model_name="qwen2.5-coder:7b",
            base_url="http://localhost:11434",
            available_models=["qwen2.5-coder:7b"],
            checked_at=datetime.now(UTC),
        )
        with patch(
            "app.api.v1.health.check_ollama_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            response = await async_client.get("/api/v1/health/ollama")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["reachable"] is True
        assert data["model_available"] is True

    async def test_ollama_health_unavailable_when_unreachable(self, async_client: AsyncClient):
        mock_status = OllamaStatus(
            reachable=False,
            model_available=False,
            model_name="qwen2.5-coder:7b",
            base_url="http://localhost:11434",
            error="Connection refused",
            install_instructions="Install Ollama from https://ollama.com",
            checked_at=datetime.now(UTC),
        )
        with patch(
            "app.api.v1.health.check_ollama_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            response = await async_client.get("/api/v1/health/ollama")

        assert response.status_code == 200  # health endpoint always returns 200
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["reachable"] is False
        assert data["error"] is not None
        assert data["install_instructions"] is not None

    async def test_ollama_health_degraded_when_model_missing(self, async_client: AsyncClient):
        mock_status = OllamaStatus(
            reachable=True,
            model_available=False,
            model_name="qwen2.5-coder:7b",
            base_url="http://localhost:11434",
            available_models=["llama3:8b"],
            error="Model not found",
            checked_at=datetime.now(UTC),
        )
        with patch(
            "app.api.v1.health.check_ollama_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            response = await async_client.get("/api/v1/health/ollama")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["reachable"] is True
        assert data["model_available"] is False

    async def test_ollama_health_returns_model_name(self, async_client: AsyncClient):
        mock_status = OllamaStatus(
            reachable=True,
            model_available=True,
            model_name="qwen2.5-coder:7b",
            base_url="http://localhost:11434",
            available_models=["qwen2.5-coder:7b"],
            checked_at=datetime.now(UTC),
        )
        with patch(
            "app.api.v1.health.check_ollama_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            response = await async_client.get("/api/v1/health/ollama")

        data = response.json()
        assert data["model_name"] == "qwen2.5-coder:7b"


class TestModelsEndpoint:
    """Tests for GET /api/v1/models."""

    async def test_models_returns_list(self, async_client: AsyncClient):
        with patch(
            "app.api.v1.health.list_ollama_models",
            new_callable=AsyncMock,
            return_value=[{"name": "qwen2.5-coder:7b", "size": 4700000000}],
        ):
            response = await async_client.get("/api/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "configured_model" in data
        assert isinstance(data["models"], list)

    async def test_models_empty_when_ollama_unreachable(self, async_client: AsyncClient):
        with patch(
            "app.api.v1.health.list_ollama_models",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await async_client.get("/api/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert data["models"] == []
        assert data["configured_model_available"] is False
