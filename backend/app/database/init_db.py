"""
Database initialisation — creates all tables and inserts seed data.

Call ``init_db()`` during application startup. It is idempotent:
tables are created only if they do not already exist.
"""

from __future__ import annotations

import logging

from app.database.base import Base, get_engine, get_session_factory
from app.models import db_models  # noqa: F401 — import models so metadata is populated

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables and insert seed data idempotently."""
    engine = get_engine()
    async with engine.begin() as conn:
        logger.info("Creating database tables…")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ready.")

    await _seed_agent_definitions()


async def _seed_agent_definitions() -> None:
    """
    Insert the canonical agent definitions if they are not already present.

    These are static reference records — they do not change at runtime.
    """
    from app.models.db_models import AgentDefinition  # local import avoids cycle

    agents = [
        AgentDefinition(
            id="requirements-analyst",
            name="Requirements Analyst",
            role="requirements_analyst",
            description=(
                "Accepts the user's project description, identifies requirements, "
                "stakeholders, constraints, and produces structured requirement artifacts."
            ),
            default_system_prompt=(
                "You are a senior Requirements Analyst. Your task is to analyse a project "
                "description and produce clear, structured requirements documentation. "
                "Identify functional requirements, non-functional requirements, user stories, "
                "acceptance criteria, assumptions, constraints, risks, and open questions. "
                "Do not invent answers to unanswered questions — record them explicitly."
            ),
        ),
        AgentDefinition(
            id="system-architect",
            name="System Architect",
            role="system_architect",
            description=(
                "Reads approved requirements and designs the system architecture, "
                "API contracts, database schema, and implementation plan."
            ),
            default_system_prompt=(
                "You are a senior System Architect. Given approved requirements, "
                "design the simplest architecture that satisfies them. Define components, "
                "interfaces, data flows, database entities, security boundaries, and "
                "document trade-offs. Output Mermaid diagrams where useful."
            ),
        ),
        AgentDefinition(
            id="task-planner",
            name="Task Planner",
            role="task_planner",
            description=(
                "Converts approved architecture into small, dependency-aware implementation tasks "
                "and assigns them to appropriate agents."
            ),
            default_system_prompt=(
                "You are a senior Technical Project Manager. Given an approved architecture, "
                "decompose the work into small, well-defined tasks with clear acceptance criteria, "
                "dependencies, priorities, and agent assignments. "
                "Avoid duplicate or conflicting tasks."
            ),
        ),
        AgentDefinition(
            id="software-developer",
            name="Software Developer",
            role="software_developer",
            description=(
                "Implements assigned tasks, writes unit tests, follows existing conventions, "
                "and records all file changes and commands executed."
            ),
            default_system_prompt=(
                "You are a senior Software Developer. Implement the assigned task precisely. "
                "Read existing files before modifying them. Write clean, maintainable code with "
                "unit tests. Follow the approved architecture. Record every file changed and "
                "command executed. Do not modify files outside your assigned workspace."
            ),
        ),
        AgentDefinition(
            id="qa-engineer",
            name="QA & Testing Engineer",
            role="qa_engineer",
            description=(
                "Creates and executes test plans, runs automated tests, "
                "reports structured bugs with reproduction steps."
            ),
            default_system_prompt=(
                "You are a senior QA Engineer. Given acceptance criteria, create a test plan "
                "covering unit, integration, API, and end-to-end scenarios. Execute tests and "
                "report results as Passed, Failed, Blocked, Not Executed, or Inconclusive. "
                "Never report a suite as passing if required tests were not executed."
            ),
        ),
        AgentDefinition(
            id="security-engineer",
            name="Security Engineer",
            role="security_engineer",
            description=(
                "Reviews source code, configuration, dependencies, and runs static analysis tools "
                "to identify and prioritise security findings."
            ),
            default_system_prompt=(
                "You are a senior Application Security Engineer. Review the provided code and "
                "configuration for security vulnerabilities: injection risks, hardcoded secrets, "
                "insecure dependencies, authentication flaws, unsafe filesystem operations, and "
                "misconfigured permissions. Prioritise findings by severity with evidence."
            ),
        ),
        AgentDefinition(
            id="code-reviewer",
            name="Independent Code Reviewer",
            role="code_reviewer",
            description=(
                "Reviews changes against requirements, architectural decisions, and QA/security "
                "evidence. Blocks incomplete or non-compliant implementations."
            ),
            default_system_prompt=(
                "You are an independent Senior Code Reviewer. Review the changes against the "
                "approved requirements and architecture. Check for logic errors, unhandled edge "
                "cases, test quality, and security compliance. Reject incomplete implementations "
                "and request specific corrections. Do not mark unexecuted tests as successful."
            ),
        ),
    ]

    factory = get_session_factory()
    async with factory() as session:
        for agent in agents:
            existing = await session.get(AgentDefinition, agent.id)
            if existing is None:
                session.add(agent)
                logger.debug("Seeded agent definition: %s", agent.id)
        await session.commit()

    logger.info("Agent definitions seeded (%d agents).", len(agents))
