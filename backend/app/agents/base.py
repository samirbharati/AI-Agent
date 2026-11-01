"""
Agent base class and result types.

All specialized agents inherit from BaseAgent. Each agent:
  - Has a fixed role and system prompt (from the DB seed data).
  - Accepts a well-defined input context dict.
  - Produces an AgentResult with structured output, token usage, and status.
  - Logs its run to the agent_runs table.
  - Is stateless between runs — all context is passed explicitly.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging.correlation import get_current_trace_id
from app.models.db_models import AgentRun, ModelUsageStat, WorkflowEvent
from app.services.llm_client import LLMClientConfig, LLMMessage, LLMResponse, OllamaLLMClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent result
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Structured output from any agent run."""

    agent_id: str
    status: str  # "success" | "failure" | "error"
    output: str  # Raw text output from the LLM
    parsed: dict[str, Any] = field(default_factory=dict)  # Structured data extracted from output
    error: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0
    model: str = ""

    @property
    def success(self) -> bool:
        return self.status == "success"

    @property
    def failure(self) -> bool:
        return self.status in ("failure", "error")


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------


class BaseAgent(ABC):
    """
    Abstract base class for all AgentForge agents.

    Subclasses implement ``build_messages()`` to construct the conversation
    and ``parse_output()`` to extract structured data from the LLM response.
    """

    # Override in subclasses
    agent_id: str = "base"
    agent_name: str = "Base Agent"
    default_system_prompt: str = "You are a helpful AI assistant."

    def __init__(
        self,
        llm_config: LLMClientConfig | None = None,
    ) -> None:
        self._client = OllamaLLMClient(config=llm_config)

    # ------------------------------------------------------------------
    # Abstract methods
    # ------------------------------------------------------------------

    @abstractmethod
    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        """
        Build the list of chat messages for this agent run.

        ``context`` contains all input data the agent needs (project details,
        prior agent outputs, task descriptions, etc.).
        """

    @abstractmethod
    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Parse the raw LLM output into structured data.

        May raise ValueError if the output is malformed. The runner will
        catch this and mark the result as a failure.
        """

    # ------------------------------------------------------------------
    # Public run method
    # ------------------------------------------------------------------

    async def run(
        self,
        context: dict[str, Any],
        *,
        db: AsyncSession | None = None,
        project_id: str | None = None,
        system_prompt_override: str | None = None,
    ) -> AgentResult:
        """
        Execute the agent: build messages → call LLM → parse output → log run.

        Args:
            context: Input data for this agent (agent-specific).
            db: Optional AsyncSession for persisting the run log.
            project_id: Optional project ID for the run log.
            system_prompt_override: Replace the default system prompt.

        Returns:
            AgentResult with output, parsed data, and usage stats.
        """
        run_id = str(uuid.uuid4())
        system_prompt = system_prompt_override or self.default_system_prompt
        start = time.monotonic()

        logger.info(
            "Agent '%s' starting run %s (project=%s)",
            self.agent_id,
            run_id,
            project_id or "—",
        )

        # Build messages
        try:
            messages = self.build_messages(context)
        except Exception as exc:  # noqa: BLE001
            elapsed = time.monotonic() - start
            result = AgentResult(
                agent_id=self.agent_id,
                status="error",
                output="",
                error=f"Failed to build messages: {exc}",
                duration_seconds=elapsed,
            )
            await self._log_run(db, project_id, run_id, result, system_prompt)
            return result

        # Call the LLM
        llm_response: LLMResponse = await self._client.chat(
            system_prompt=system_prompt,
            messages=messages,
        )
        elapsed = time.monotonic() - start

        if not llm_response.success:
            result = AgentResult(
                agent_id=self.agent_id,
                status="error",
                output="",
                error=llm_response.error,
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
                duration_seconds=elapsed,
                model=llm_response.model,
            )
            logger.error("Agent '%s' run %s failed: %s", self.agent_id, run_id, llm_response.error)
            await self._log_run(db, project_id, run_id, result, system_prompt)
            return result

        # Parse output
        try:
            parsed = self.parse_output(llm_response.content, context)
            status = "success"
            error = None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Agent '%s' run %s: output parse failed: %s", self.agent_id, run_id, exc)
            parsed = {}
            status = "failure"
            error = f"Output parse failed: {exc}"

        result = AgentResult(
            agent_id=self.agent_id,
            status=status,
            output=llm_response.content,
            parsed=parsed,
            error=error,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
            duration_seconds=elapsed,
            model=llm_response.model,
        )

        logger.info(
            "Agent '%s' run %s %s. tokens=%d elapsed=%.1fs",
            self.agent_id,
            run_id,
            status,
            result.total_tokens,
            elapsed,
        )

        await self._log_run(db, project_id, run_id, result, system_prompt)
        return result

    # ------------------------------------------------------------------
    # Run logging
    # ------------------------------------------------------------------

    async def _log_run(
        self,
        db: AsyncSession | None,
        project_id: str | None,
        run_id: str,
        result: AgentResult,
        system_prompt: str,
    ) -> None:
        if db is None:
            return
        try:
            run = AgentRun(
                id=run_id,
                project_id=project_id,
                agent_definition_id=self.agent_id,
                status=result.status,
                input_summary=f"context keys: {list(result.parsed.keys())}"
                if result.parsed
                else "",
                output_summary=result.output[:500] if result.output else "",
                error_message=result.error,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.total_tokens,
                duration_seconds=result.duration_seconds,
                model_used=result.model,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            )
            db.add(run)

            if result.model:
                stat = ModelUsageStat(
                    project_id=project_id,
                    agent_run_id=run_id,
                    model_name=result.model,
                    agent_role=self.agent_id,
                    duration_seconds=result.duration_seconds,
                    token_count_in=result.prompt_tokens,
                    token_count_out=result.completion_tokens,
                    success=result.success,
                    error_type=result.error if not result.success else None,
                    created_at=datetime.now(UTC),
                )
                db.add(stat)

            if project_id:
                event = WorkflowEvent(
                    project_id=project_id,
                    agent_run_id=run_id,
                    event_type=f"agent_{result.status}",
                    message=f"[{self.agent_name}] execution {result.status}. Tokens: {result.total_tokens}. Duration: {result.duration_seconds:.2f}s",
                    severity="success"
                    if result.success
                    else ("warning" if result.status == "failure" else "error"),
                    source=self.agent_id,
                    category="agent_lifecycle",
                    status=result.status,
                    trace_id=get_current_trace_id(),
                    duration_ms=int((result.duration_seconds or 0) * 1000),
                    payload={
                        "model": result.model,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "total_tokens": result.total_tokens,
                    },
                    created_at=datetime.now(UTC),
                )
                db.add(event)

            await db.flush()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to log agent run to DB: %s", exc)
