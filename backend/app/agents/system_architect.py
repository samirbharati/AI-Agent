"""
System Architect Agent.

Takes approved requirements and produces a system architecture document:
  - Component diagram (Mermaid)
  - API contract summary
  - Database schema
  - Technology decisions with rationale
  - Security boundaries
  - Deployment topology
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMMessage

_SYSTEM_PROMPT = """\
You are a senior System Architect. Given approved requirements, design the \
simplest architecture that satisfies them — no over-engineering.

Produce your output with the following exact Markdown sections:

## Architecture Overview
One paragraph summary of the chosen approach and key trade-offs.

## Component Diagram
A Mermaid diagram (```mermaid block) showing components and their relationships.

## Technology Stack
Table: | Layer | Technology | Reason |
List: frontend, backend, database, auth, testing, CI/CD.

## API Design
List the major API endpoints grouped by resource.
Format: METHOD /path — Description

## Database Schema
List each table/collection with its key fields and relationships.

## Security Boundaries
Describe: authentication mechanism, authorisation model, data validation, \
secrets management, and any sandboxing.

## Deployment Topology
Describe how the application runs locally and how it would deploy to production.

## Implementation Notes
Any important constraints, gotchas, or decisions the development team must follow.

Rules:
- Choose the simplest stack that meets the requirements.
- Prefer the user's stated language/framework/database preferences.
- All design decisions must trace back to a specific requirement.
- Flag any requirements that are ambiguous or in conflict.
"""


class SystemArchitectAgent(BaseAgent):
    agent_id = "system-architect"
    agent_name = "System Architect"
    default_system_prompt = _SYSTEM_PROMPT

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        project_name = context.get("project_name", "Unnamed Project")
        requirements_document = context.get("requirements_document", "")
        preferred_language = context.get("preferred_language", "python")
        preferred_framework = context.get("preferred_framework", "fastapi")
        preferred_database = context.get("preferred_database", "sqlite")

        user_content = f"""\
Project Name: {project_name}

Technology Preferences:
- Language: {preferred_language}
- Framework: {preferred_framework}
- Database: {preferred_database}

Approved Requirements Document:
{requirements_document}

Please design a complete system architecture for this project.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        sections = _extract_markdown_sections(raw_output)

        required = {
            "Architecture Overview",
            "Technology Stack",
            "API Design",
            "Database Schema",
        }
        missing = required - set(sections.keys())
        if missing:
            raise ValueError(f"Architecture output is missing required sections: {sorted(missing)}")

        has_mermaid = "```mermaid" in raw_output
        api_endpoints = _count_api_endpoints(sections.get("API Design", ""))

        return {
            "sections": sections,
            "has_component_diagram": has_mermaid,
            "api_endpoint_count": api_endpoints,
            "raw_document": raw_output,
        }


def _extract_markdown_sections(text: str) -> dict[str, str]:
    pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections


def _count_api_endpoints(api_text: str) -> int:
    methods = re.findall(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s", api_text, re.MULTILINE)
    return len(methods)
