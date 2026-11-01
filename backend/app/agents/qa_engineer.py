"""
QA Engineer Agent.

Reviews implemented code against acceptance criteria and produces a structured
test report with pass/fail results and any bug reports.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMClientConfig, LLMMessage

_SYSTEM_PROMPT = """\
You are a senior QA Engineer reviewing implemented code. Your job is to \
assess whether the implementation meets the acceptance criteria and identify \
any defects, edge cases, or gaps.

Output a single valid JSON object:
{
  "verdict": "pass|fail|blocked",
  "summary": "One-sentence verdict summary.",
  "test_cases": [
    {
      "id": "TC-001",
      "name": "Test case name",
      "description": "What is being tested.",
      "expected": "Expected behaviour.",
      "actual": "Observed behaviour (from code review, not execution).",
      "status": "passed|failed|blocked|not_executed",
      "severity": "critical|high|medium|low|info"
    }
  ],
  "bugs": [
    {
      "id": "BUG-001",
      "title": "Short bug title",
      "description": "Detailed description of the defect.",
      "steps_to_reproduce": "1. ... 2. ...",
      "expected": "Expected behaviour.",
      "actual": "Actual behaviour.",
      "severity": "critical|high|medium|low",
      "affected_file": "path/to/file.py"
    }
  ],
  "coverage_assessment": "Assessment of test coverage quality.",
  "recommendations": ["List of specific improvement suggestions."]
}

Rules:
- Review the code carefully — this is a static review, not execution.
- Only mark a test as 'passed' if you can confirm it from the code.
- Never mark tests as passed if the relevant code is missing.
- Report ALL defects, no matter how small.
- verdict is 'pass' only if ALL critical and high severity tests pass.
- Do NOT output anything outside the JSON object.
"""


class QAEngineerAgent(BaseAgent):
    agent_id = "qa-engineer"
    agent_name = "QA Engineer"
    default_system_prompt = _SYSTEM_PROMPT

    def __init__(self) -> None:
        super().__init__(llm_config=LLMClientConfig(temperature=0.1, max_tokens=4000))

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        task_title = context.get("task_title", "Unnamed Task")
        acceptance_criteria = context.get("acceptance_criteria", "")
        implemented_files = context.get("implemented_files", {})  # {path: content}
        architecture_summary = context.get("architecture_summary", "")

        files_text = ""
        if implemented_files:
            for path, content in implemented_files.items():
                files_text += f"\n--- {path} ---\n{content}\n"

        test_results_text = ""
        test_results = context.get("test_results")
        if test_results:
            test_results_text = f"""
Automated Test Execution Results:
Status: {test_results.get('status')}
Passed: {test_results.get('passed_count', 0)} / {test_results.get('total_tests', 0)}
Failed: {test_results.get('failed_count', 0)}
Stdout/Stderr Diagnostic Output:
{test_results.get('raw_stderr') or test_results.get('raw_stdout') or 'None'}
"""

        user_content = f"""\
Task Title: {task_title}

Acceptance Criteria:
{acceptance_criteria}

Architecture Context:
{architecture_summary}

Implemented Files to Review:
{files_text or "No files provided."}
{test_results_text}
Review the implementation and produce a QA report. Output only valid JSON.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        json_str = _extract_json(raw_output)
        data = json.loads(json_str)

        verdict = data.get("verdict", "blocked")
        if verdict not in ("pass", "fail", "blocked"):
            verdict = "blocked"

        test_cases = data.get("test_cases", [])
        bugs = data.get("bugs", [])

        critical_bugs = [b for b in bugs if b.get("severity") == "critical"]
        high_bugs = [b for b in bugs if b.get("severity") == "high"]

        return {
            "verdict": verdict,
            "summary": data.get("summary", ""),
            "test_cases": test_cases,
            "bugs": bugs,
            "critical_bug_count": len(critical_bugs),
            "high_bug_count": len(high_bugs),
            "total_bugs": len(bugs),
            "coverage_assessment": data.get("coverage_assessment", ""),
            "recommendations": data.get("recommendations", []),
            "passed": verdict == "pass",
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
    raise ValueError("No JSON object found in QA output.")
