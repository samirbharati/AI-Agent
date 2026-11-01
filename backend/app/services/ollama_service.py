"""
Ollama connectivity service.

Provides health checks and model availability verification
without initiating full inference. This module does NOT
perform LLM inference — that is Phase 3.

All network calls include explicit timeouts. If Ollama is
unreachable, a clear status and instructions are returned.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_OLLAMA_INSTALL_INSTRUCTIONS = """
Ollama is not reachable. To install and start Ollama on Windows:

  1. Download the installer from https://ollama.com/download/windows
  2. Run the installer and start the Ollama service.
  3. Pull the required model:
       ollama pull qwen2.5-coder:7b
  4. Verify Ollama is running:
       ollama list
  5. Restart AgentForge.

If Ollama is already installed but not running, start it via:
  Start Menu → Ollama  OR  run 'ollama serve' in a terminal.
"""


@dataclass
class OllamaStatus:
    """Result of an Ollama availability check."""

    reachable: bool
    model_available: bool
    model_name: str
    base_url: str
    available_models: list[str] = field(default_factory=list)
    error: str | None = None
    install_instructions: str | None = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def fully_operational(self) -> bool:
        return self.reachable and self.model_available


async def check_ollama_status() -> OllamaStatus:
    """
    Check whether the configured Ollama instance is reachable and
    whether the required model is available.

    Returns an OllamaStatus regardless of connectivity — callers
    should inspect `reachable` and `model_available`.
    """
    settings = get_settings()
    base_url = settings.ollama_base_url.rstrip("/")
    model_name = settings.ollama_model

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Check if Ollama HTTP API is reachable
            try:
                root_resp = await client.get(f"{base_url}/")
                root_resp.raise_for_status()
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                logger.warning("Ollama is not reachable at %s: %s", base_url, exc)
                return OllamaStatus(
                    reachable=False,
                    model_available=False,
                    model_name=model_name,
                    base_url=base_url,
                    error=str(exc),
                    install_instructions=_OLLAMA_INSTALL_INSTRUCTIONS,
                )

            # 2. List available models
            tags_resp = await client.get(f"{base_url}/api/tags")
            tags_resp.raise_for_status()
            tags_data = tags_resp.json()

            available_models: list[str] = [m.get("name", "") for m in tags_data.get("models", [])]

            # Check if the configured model is available (match by prefix to handle tag variants)
            model_available = any(
                m == model_name or m.startswith(f"{model_name}:") for m in available_models
            )

            if not model_available:
                error_msg = (
                    f"Model '{model_name}' is not available in Ollama. "
                    f"Available models: {available_models}. "
                    f"Install with: ollama pull {model_name}"
                )
                logger.warning(error_msg)
                return OllamaStatus(
                    reachable=True,
                    model_available=False,
                    model_name=model_name,
                    base_url=base_url,
                    available_models=available_models,
                    error=error_msg,
                    install_instructions=(
                        f"Run the following command to install the required model:\n\n"
                        f"  ollama pull {model_name}\n\n"
                        f"Then restart AgentForge."
                    ),
                )

            logger.debug("Ollama health check passed. Model '%s' is available.", model_name)
            return OllamaStatus(
                reachable=True,
                model_available=True,
                model_name=model_name,
                base_url=base_url,
                available_models=available_models,
            )

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during Ollama health check: %s", exc)
        return OllamaStatus(
            reachable=False,
            model_available=False,
            model_name=model_name,
            base_url=base_url,
            error=f"Unexpected error: {exc}",
            install_instructions=_OLLAMA_INSTALL_INSTRUCTIONS,
        )


async def list_ollama_models() -> list[dict]:
    """
    Return a list of models installed in Ollama.

    Returns an empty list if Ollama is unreachable.
    """
    settings = get_settings()
    base_url = settings.ollama_base_url.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not list Ollama models: %s", exc)
        return []
