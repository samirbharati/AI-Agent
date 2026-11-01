"""
Health check endpoints.

  GET /api/v1/health           — Application health (always returns 200)
  GET /api/v1/health/ollama    — Ollama connectivity and model availability
  GET /api/v1/models           — List models installed in Ollama
"""

from __future__ import annotations

import platform
import sys
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.services.ollama_service import OllamaStatus, check_ollama_status, list_ollama_models

router = APIRouter(tags=["health"])


# ---------------------------------------------------------------------------
# Response schemas (local — only used by health endpoints)
# ---------------------------------------------------------------------------


class AppHealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    python_version: str
    platform: str
    timestamp: datetime


class OllamaHealthResponse(BaseModel):
    status: str  # "ok" | "degraded" | "unavailable"
    reachable: bool
    model_available: bool
    model_name: str
    base_url: str
    available_models: list[str]
    error: str | None = None
    install_instructions: str | None = None
    checked_at: datetime


class ModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None
    digest: str | None = None


class ModelsResponse(BaseModel):
    ollama_reachable: bool
    models: list[ModelInfo]
    configured_model: str
    configured_model_available: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=AppHealthResponse,
    summary="Application health check",
    description=(
        "Returns 200 OK when the AgentForge backend is running. "
        "Does not check external dependencies. Use /health/ollama for LLM status."
    ),
)
async def app_health() -> AppHealthResponse:
    settings = get_settings()
    return AppHealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.app_env,
        python_version=sys.version,
        platform=platform.platform(),
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/health/ollama",
    response_model=OllamaHealthResponse,
    summary="Ollama LLM health check",
    description=(
        "Checks whether the configured Ollama instance is reachable and "
        "whether the required model is installed. Returns actionable instructions "
        "if the model is missing or Ollama is not running."
    ),
)
async def ollama_health() -> OllamaHealthResponse:
    status: OllamaStatus = await check_ollama_status()

    if status.fully_operational:
        health_status = "ok"
    elif status.reachable:
        health_status = "degraded"
    else:
        health_status = "unavailable"

    return OllamaHealthResponse(
        status=health_status,
        reachable=status.reachable,
        model_available=status.model_available,
        model_name=status.model_name,
        base_url=status.base_url,
        available_models=status.available_models,
        error=status.error,
        install_instructions=status.install_instructions,
        checked_at=status.checked_at,
    )


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available Ollama models",
    description="Returns all models installed in the local Ollama instance.",
)
async def list_models() -> ModelsResponse:
    settings = get_settings()
    raw_models = await list_ollama_models()

    model_infos = [
        ModelInfo(
            name=m.get("name", ""),
            size=m.get("size"),
            modified_at=m.get("modified_at"),
            digest=m.get("digest"),
        )
        for m in raw_models
    ]

    configured_model = settings.ollama_model
    configured_available = any(
        m.name == configured_model or m.name.startswith(f"{configured_model}:") for m in model_infos
    )

    return ModelsResponse(
        ollama_reachable=bool(raw_models) or len(raw_models) >= 0,
        models=model_infos,
        configured_model=configured_model,
        configured_model_available=configured_available,
    )
