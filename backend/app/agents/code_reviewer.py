"""
Code Reviewer Agent.

Performs an independent code review after implementation, QA, and security
passes. Produces a structured review with approve/request-changes decision.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMClientConfig, LLMMessage

_SYSTEM_PROMPT = """\
You are an independent Senior Code Reviewer. Your job is to perform a final \
review of implemented code before it is accepted into the project.

Review against:
1. Correctness — does the code do what the task requires?
2. Requirements compliance — are all acceptance criteria met?
3. Architecture adherence — does the code follow the approved design?
4. Code quality — clean, readable, maintainable, well-documented?
5. Test quality — are tests meaningful and sufficient?
6. Security — are security findings from the security review addressed?
7. Edge cases — are failure modes and edge cases handled?

Output a single valid JSON object:
{
  "decision": "approved|changes_requested|rejected",
  "summary": "One-paragraph summary of the review.",
  "comments": [
    {
      "id": "CR-001",
      "type": "blocker|major|minor|suggestion|praise",
      "file": "path/to/file.py",
      "line": 42,
      "comment": "Detailed review comment.",
      "suggested_fix": "Optional: specific fix suggestion."
    }
  ],
  "requirements_met": true,
  "architecture_compliant": true,
  "tests_adequate": true,
  "blockers_count": 0,
  "approval_notes": "Conditions under which this is approved (if any)."
}

Rules:
- decision is 'approved' only if there are ZERO blockers.
- decision is 'rejected' only if the implementation is fundamentally wrong.
- decision is 'changes_requested' for all other cases.
- Do not approve code that has unexecuted required tests.
- Do not approve code that ignores critical security findings.
- Do NOT output anything outside the JSON object.
"""


class CodeReviewerAgent(BaseAgent):
    agent_id = "code-reviewer"
    agent_name = "Code Reviewer"
    default_system_prompt = _SYSTEM_PROMPT

    def __init__(self) -> None:
        super().__init__(llm_config=LLMClientConfig(temperature=0.1, max_tokens=4000))

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        task_title = context.get("task_title", "Unnamed Task")
        acceptance_criteria = context.get("acceptance_criteria", "")
        implemented_files = context.get("implemented_files", {})
        qa_report = context.get("qa_report", {})
        security_report = context.get("security_report", {})
        architecture_summary = context.get("architecture_summary", "")

        files_text = ""
        if implemented_files:
            for path, content in implemented_files.items():
                files_text += f"\n--- {path} ---\n{content}\n"

        qa_summary = (
            f"QA Verdict: {qa_report.get('verdict', 'unknown')}\n"
            f"Bugs found: {qa_report.get('total_bugs', 0)}\n"
            f"Coverage: {qa_report.get('coverage_assessment', 'not provided')}"
        ) if qa_report else "No QA report available."

        sec_summary = (
            f"Security Risk: {security_report.get('overall_risk', 'unknown')}\n"
            f"Critical findings: {security_report.get('critical_finding_count', 0)}\n"
            f"High findings: {security_report.get('high_finding_count', 0)}\n"
            f"Approved for deployment: {security_report.get('approved_for_deployment', False)}"
        ) if security_report else "No security report available."

        user_content = f"""\
Task Title: {task_title}

Acceptance Criteria:
{acceptance_criteria}

Architecture Context:
{architecture_summary}

QA Report Summary:
{qa_summary}

Security Report Summary:
{sec_summary}

Implemented Files:
{files_text or "No files provided."}

Perform an independent code review. Output only valid JSON.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        json_str = _extract_json(raw_output)
        data = json.loads(json_str)

        decision = data.get("decision", "changes_requested")
        if decision not in ("approved", "changes_requested", "rejected"):
            decision = "changes_requested"

        comments = data.get("comments", [])
        blockers = [c for c in comments if c.get("type") == "blocker"]

        # Safety: if there are blockers, decision cannot be approved
        if blockers and decision == "approved":
            decision = "changes_requested"

        return {
            "decision": decision,
            "summary": data.get("summary", ""),
            "comments": comments,
            "blockers_count": len(blockers),
            "requirements_met": data.get("requirements_met", False),
            "architecture_compliant": data.get("architecture_compliant", False),
            "tests_adequate": data.get("tests_adequate", False),
            "approved": decision == "approved",
            "approval_notes": data.get("approval_notes", ""),
        }


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{"):
        return stripped
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    raise ValueError("No JSON object found in code reviewer output.")
