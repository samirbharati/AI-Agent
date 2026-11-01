"""
Task Planner Agent.

Decomposes the approved architecture into small, dependency-aware implementation
tasks. Each task is assigned to a specific agent with clear acceptance criteria.

Output is structured JSON that the workflow engine parses into Task DB records.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMClientConfig, LLMMessage

_SYSTEM_PROMPT = """\
You are a senior Technical Project Manager. Given an approved architecture \
document, decompose the work into small, well-defined implementation tasks.

Output a single valid JSON object with this exact structure:
{
  "tasks": [
    {
      "title": "Short, imperative task title",
      "description": "What to build, in 2-4 sentences with specific acceptance criteria.",
      "priority": "critical|high|medium|low",
      "assigned_agent": "software-developer|qa-engineer|security-engineer|code-reviewer",
      "order_index": 1,
      "complexity_estimate": "trivial|simple|moderate|complex|unknown",
      "dependency_titles": ["Title of task that must complete before this one"],
      "acceptance_criteria": "Specific, testable done criteria."
    }
  ],
  "total_tasks": <number>,
  "estimated_complexity": "low|medium|high",
  "planning_notes": "Any important notes about the decomposition."
}

Rules:
- Each task must be completable in a single agent invocation.
- Tasks must have clear, testable acceptance criteria.
- Dependencies must reference exact titles of other tasks in the list.
- No circular dependencies.
- Do NOT generate tasks for requirements analysis or architecture — those are done.
- Do NOT output anything outside the JSON object.
- Assigned agents must be exactly one of: software-developer, qa-engineer, \
  security-engineer, code-reviewer.
"""


class TaskPlannerAgent(BaseAgent):
    agent_id = "task-planner"
    agent_name = "Task Planner"
    default_system_prompt = _SYSTEM_PROMPT

    def __init__(self) -> None:
        # Lower temperature for structured JSON output
        super().__init__(llm_config=LLMClientConfig(temperature=0.1, max_tokens=4000))

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        project_name = context.get("project_name", "Unnamed Project")
        architecture_document = context.get("architecture_document", "")
        requirements_document = context.get("requirements_document", "")

        user_content = f"""\
Project Name: {project_name}

Approved Requirements (summary):
{requirements_document[:2000]}

Approved Architecture Document:
{architecture_document}

Decompose this into implementation tasks. Output only valid JSON.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        """Parse the JSON task plan from the LLM output."""
        json_str = _extract_json(raw_output)
        data = json.loads(json_str)

        tasks = data.get("tasks", [])
        if not tasks:
            raise ValueError("Task plan contains no tasks.")

        valid_agents = {
            "software-developer",
            "qa-engineer",
            "security-engineer",
            "code-reviewer",
        }
        valid_priorities = {"critical", "high", "medium", "low"}
        valid_complexities = {"trivial", "simple", "moderate", "complex", "unknown"}

        for i, task in enumerate(tasks):
            if not task.get("title"):
                raise ValueError(f"Task {i} is missing a title.")
            if task.get("assigned_agent") not in valid_agents:
                raise ValueError(
                    f"Task '{task['title']}' has invalid assigned_agent: "
                    f"'{task.get('assigned_agent')}'. Must be one of {sorted(valid_agents)}."
                )
            if task.get("priority") not in valid_priorities:
                task["priority"] = "medium"  # default, don't fail
            if task.get("complexity_estimate") not in valid_complexities:
                task["complexity_estimate"] = "unknown"

        return {
            "tasks": tasks,
            "total_tasks": data.get("total_tasks", len(tasks)),
            "estimated_complexity": data.get("estimated_complexity", "medium"),
            "planning_notes": data.get("planning_notes", ""),
        }


def _extract_json(text: str) -> str:
    """Extract a JSON object from text that may contain surrounding prose."""
    # First try: entire text is valid JSON
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped

    # Second try: find JSON block in markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Third try: find the first { ... } block
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)

    raise ValueError("No JSON object found in task planner output.")
