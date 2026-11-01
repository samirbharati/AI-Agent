"""
Requirements Analyst Agent.

Takes the user's project description and produces structured requirements:
  - Functional requirements
  - Non-functional requirements
  - User stories
  - Acceptance criteria
  - Assumptions, constraints, risks
  - Open questions (explicitly listed, not invented)
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMMessage

_SYSTEM_PROMPT = """\
You are a senior Requirements Analyst. Your job is to transform a project \
description into clear, complete, and structured requirements documentation.

You MUST produce your output using the following exact Markdown sections:

## Functional Requirements
List each as: FR-01, FR-02, … with a short title and one-sentence description.

## Non-Functional Requirements
List each as: NFR-01, NFR-02, … Include performance, security, scalability, etc.

## User Stories
Format: "As a [persona], I want to [action] so that [benefit]."
List at least 3 user stories.

## Acceptance Criteria
For each major functional requirement, list testable criteria.

## Assumptions
List explicit assumptions made.

## Constraints
List technical, business, or legal constraints.

## Risks
List identified risks with likelihood (Low/Medium/High) and impact.

## Open Questions
List unanswered questions that need clarification. Do NOT invent answers.

Rules:
- Be specific and measurable, not vague.
- Do NOT invent requirements not implied by the description.
- Record open questions explicitly rather than guessing.
- Use plain English, no jargon without definition.
"""


class RequirementsAnalystAgent(BaseAgent):
    agent_id = "requirements-analyst"
    agent_name = "Requirements Analyst"
    default_system_prompt = _SYSTEM_PROMPT

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        project_name = context.get("project_name", "Unnamed Project")
        project_description = context.get("project_description", "")
        preferred_language = context.get("preferred_language", "not specified")
        preferred_framework = context.get("preferred_framework", "not specified")
        preferred_database = context.get("preferred_database", "not specified")

        user_content = f"""\
Project Name: {project_name}

Project Description:
{project_description}

Technical Preferences:
- Programming Language: {preferred_language}
- Framework: {preferred_framework}
- Database: {preferred_database}

Please produce a complete requirements document following the specified format.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Extract structured sections from the requirements document.

        Returns a dict with keys for each section. Raises ValueError
        if the required sections are missing.
        """
        sections = _extract_markdown_sections(raw_output)

        required = {
            "Functional Requirements",
            "Non-Functional Requirements",
            "User Stories",
        }
        missing = required - set(sections.keys())
        if missing:
            raise ValueError(
                f"Requirements output is missing required sections: {sorted(missing)}"
            )

        # Count functional requirements
        fr_text = sections.get("Functional Requirements", "")
        fr_count = len(re.findall(r"^FR-\d+", fr_text, re.MULTILINE))

        return {
            "sections": sections,
            "functional_requirements_count": fr_count,
            "has_open_questions": bool(sections.get("Open Questions", "").strip()),
            "raw_document": raw_output,
        }


def _extract_markdown_sections(text: str) -> dict[str, str]:
    """Split a Markdown document into {section_title: content} pairs."""
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections
