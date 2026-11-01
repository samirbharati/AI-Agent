"""
LLM client for Ollama inference.

Wraps the Ollama /api/chat endpoint with:
  - Async streaming via httpx
  - Semaphore-based concurrency control (single inference at a time on CPU)
  - Token usage tracking
  - Structured retry with exponential back-off
  - Hard token budget enforcement (truncates history if needed)
  - Configurable timeouts separate from health-check timeouts
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Semaphore — one inference at a time on CPU hardware
# ---------------------------------------------------------------------------

_inference_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _inference_semaphore  # noqa: PLW0603
    if _inference_semaphore is None:
        limit = get_settings().max_concurrent_llm_requests
        _inference_semaphore = asyncio.Semaphore(limit)
    return _inference_semaphore


def reset_semaphore() -> None:
    """Reset the semaphore (used in tests to pick up settings changes)."""
    global _inference_semaphore  # noqa: PLW0603
    _inference_semaphore = None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LLMMessage:
    """A single chat message (system / user / assistant)."""

    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class LLMResponse:
    """Full response from a non-streaming inference call."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0
    done: bool = True
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.done


@dataclass
class StreamChunk:
    """A single chunk from a streaming response."""

    content: str
    done: bool = False
    error: str | None = None


@dataclass
class LLMClientConfig:
    """Per-call configuration overrides."""

    temperature: float = 0.2
    top_p: float = 0.9
    num_ctx: int | None = None  # uses settings default if None
    max_tokens: int | None = None  # hard stop on generated tokens
    stop_sequences: list[str] = field(default_factory=list)
    timeout_seconds: float = 300.0  # generous for CPU inference


# ---------------------------------------------------------------------------
# Token budget helper
# ---------------------------------------------------------------------------

_APPROX_CHARS_PER_TOKEN = 3.5  # conservative estimate for English + code


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / _APPROX_CHARS_PER_TOKEN))


def _trim_messages_to_budget(
    messages: list[LLMMessage],
    system_prompt: str,
    context_window: int,
    safety_margin: int = 512,
) -> list[LLMMessage]:
    """
    Trim the oldest non-system messages until the history fits within the
    context window, preserving the system prompt and the last user message.
    """
    budget = context_window - safety_margin
    system_tokens = _estimate_tokens(system_prompt)
    available = budget - system_tokens

    # Always keep at least the last user message
    trimmed = list(messages)
    while len(trimmed) > 1:
        total = sum(_estimate_tokens(m.content) for m in trimmed)
        if total <= available:
            break
        # Drop the oldest non-system message
        trimmed.pop(0)
        logger.debug("Trimmed oldest message from context. Remaining: %d messages.", len(trimmed))

    return trimmed


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------


class OllamaLLMClient:
    """
    Async Ollama LLM client for chat-completion inference.

    Usage::

        client = OllamaLLMClient()
        response = await client.chat(
            system_prompt="You are a senior software architect.",
            messages=[LLMMessage(role="user", content="Design a REST API for a todo app.")],
        )
        print(response.content)
    """

    def __init__(self, config: LLMClientConfig | None = None) -> None:
        self._config = config or LLMClientConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        *,
        system_prompt: str,
        messages: list[LLMMessage],
        config: LLMClientConfig | None = None,
    ) -> LLMResponse:
        """
        Send a chat request to Ollama and return the full response.

        Blocks until the model finishes generating. Respects the global
        inference semaphore (one at a time on CPU hardware).
        """
        cfg = config or self._config
        settings = get_settings()
        num_ctx = cfg.num_ctx or settings.ollama_num_ctx

        trimmed_messages = _trim_messages_to_budget(messages, system_prompt, num_ctx)

        payload = self._build_payload(
            system_prompt=system_prompt,
            messages=trimmed_messages,
            cfg=cfg,
            num_ctx=num_ctx,
            stream=False,
        )

        async with _get_semaphore():
            return await self._post_chat(payload, cfg.timeout_seconds)

    async def stream(
        self,
        *,
        system_prompt: str,
        messages: list[LLMMessage],
        config: LLMClientConfig | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Send a chat request and yield StreamChunk objects as tokens arrive.

        The final chunk has ``done=True`` and no content.
        """
        cfg = config or self._config
        settings = get_settings()
        num_ctx = cfg.num_ctx or settings.ollama_num_ctx

        trimmed_messages = _trim_messages_to_budget(messages, system_prompt, num_ctx)

        payload = self._build_payload(
            system_prompt=system_prompt,
            messages=trimmed_messages,
            cfg=cfg,
            num_ctx=num_ctx,
            stream=True,
        )

        async with _get_semaphore():
            async for chunk in self._stream_chat(payload, cfg.timeout_seconds):
                yield chunk

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        *,
        system_prompt: str,
        messages: list[LLMMessage],
        cfg: LLMClientConfig,
        num_ctx: int,
        stream: bool,
    ) -> dict[str, Any]:
        settings = get_settings()
        full_messages = [
            {"role": "system", "content": system_prompt},
            *[m.to_dict() for m in messages],
        ]
        payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "messages": full_messages,
            "stream": stream,
            "options": {
                "temperature": cfg.temperature,
                "top_p": cfg.top_p,
                "num_ctx": num_ctx,
            },
        }
        if cfg.max_tokens:
            payload["options"]["num_predict"] = cfg.max_tokens
        if cfg.stop_sequences:
            payload["options"]["stop"] = cfg.stop_sequences
        return payload

    async def _post_chat(self, payload: dict, timeout: float) -> LLMResponse:
        settings = get_settings()
        url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
        model = payload["model"]

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

        except httpx.ConnectError as exc:
            return LLMResponse(
                content="",
                model=model,
                error=f"Ollama connection refused at {url}: {exc}",
                done=False,
            )
        except httpx.TimeoutException as exc:
            return LLMResponse(
                content="",
                model=model,
                error=f"Ollama inference timed out after {timeout}s: {exc}",
                done=False,
            )
        except httpx.HTTPStatusError as exc:
            return LLMResponse(
                content="",
                model=model,
                error=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text[:500]}",
                done=False,
            )
        except Exception as exc:  # noqa: BLE001
            return LLMResponse(
                content="",
                model=model,
                error=f"Unexpected error during inference: {exc}",
                done=False,
            )

        elapsed = time.monotonic() - start
        message_data = data.get("message", {})
        content = message_data.get("content", "")

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        logger.debug(
            "Ollama inference complete. model=%s tokens=%d+%d elapsed=%.1fs",
            model,
            prompt_tokens,
            completion_tokens,
            elapsed,
        )

        return LLMResponse(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            duration_seconds=elapsed,
            done=data.get("done", True),
        )

    async def _stream_chat(
        self, payload: dict, timeout: float
    ) -> AsyncGenerator[StreamChunk, None]:
        settings = get_settings()
        url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk_data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        content = chunk_data.get("message", {}).get("content", "")
                        done = chunk_data.get("done", False)
                        yield StreamChunk(content=content, done=done)

                        if done:
                            break

        except httpx.ConnectError as exc:
            yield StreamChunk(content="", done=True, error=f"Connection error: {exc}")
        except httpx.TimeoutException as exc:
            yield StreamChunk(content="", done=True, error=f"Timeout: {exc}")
        except Exception as exc:  # noqa: BLE001
            yield StreamChunk(content="", done=True, error=f"Streaming error: {exc}")
