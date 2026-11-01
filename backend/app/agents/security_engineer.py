"""
Security Engineer Agent.

Reviews source code and configuration for security vulnerabilities,
producing a structured findings report with OWASP-aligned severity ratings.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMClientConfig, LLMMessage

_SYSTEM_PROMPT = """\
You are a senior Application Security Engineer. Review the provided code and \
configuration files for security vulnerabilities.

Check for (at minimum):
- Injection vulnerabilities (SQL, command, LDAP, XPath)
- Hardcoded secrets, API keys, passwords
- Insecure dependencies or import patterns
- Authentication and authorisation flaws
- Insecure direct object references
- Sensitive data exposure (logging, error messages, stack traces)
- Insecure file system operations
- Missing input validation and output encoding
- Unsafe cryptography (weak algorithms, hardcoded keys)
- Misconfigured CORS, headers, or permissions

Output a single valid JSON object:
{
  "overall_risk": "critical|high|medium|low|informational",
  "summary": "One-paragraph security assessment.",
  "findings": [
    {
      "id": "SEC-001",
      "title": "Short finding title",
      "description": "Detailed description of the vulnerability.",
      "affected_file": "path/to/file.py",
      "affected_line": 42,
      "severity": "critical|high|medium|low|informational",
      "owasp_category": "A01:2021 – Broken Access Control",
      "recommendation": "Specific fix recommendation.",
      "code_snippet": "The vulnerable code snippet."
    }
  ],
  "secure_practices_observed": ["List of good security practices found."],
  "recommendations": ["Overall improvement recommendations."],
  "approved_for_deployment": false
}

Rules:
- Report every finding, no matter how minor.
- approved_for_deployment is true ONLY if there are zero critical/high findings.
- Be specific — reference exact file paths and line numbers where possible.
- Do NOT output anything outside the JSON object.
"""


class SecurityEngineerAgent(BaseAgent):
    agent_id = "security-engineer"
    agent_name = "Security Engineer"
    default_system_prompt = _SYSTEM_PROMPT

    def __init__(self) -> None:
        super().__init__(llm_config=LLMClientConfig(temperature=0.1, max_tokens=4000))

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        task_title = context.get("task_title", "Unnamed Task")
        implemented_files = context.get("implemented_files", {})
        architecture_summary = context.get("architecture_summary", "")

        files_text = ""
        if implemented_files:
            for path, content in implemented_files.items():
                files_text += f"\n--- {path} ---\n{content}\n"

        scanner_text = ""
        scanner_findings = context.get("scanner_findings", [])
        if scanner_findings:
            scanner_text = "\nDeterministic Scanner Rule Violations Detected:\n"
            for f in scanner_findings:
                scanner_text += (
                    f"- [{f.get('severity', 'info').upper()}] {f.get('rule_id')}: {f.get('title')} "
                    f"in {f.get('file_path')}:{f.get('line_number')} | Evidence: {f.get('evidence')} "
                    f"| Remediation: {f.get('remediation')}\n"
                )

        user_content = f"""\
Task / Feature: {task_title}

Architecture Context:
{architecture_summary}

Files to Review:
{files_text or "No files provided."}
{scanner_text}
Perform a thorough security review. Output only valid JSON.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        json_str = _extract_json(raw_output)
        data = json.loads(json_str)

        overall_risk = data.get("overall_risk", "medium")
        findings = data.get("findings", [])

        critical_findings = [f for f in findings if f.get("severity") == "critical"]
        high_findings = [f for f in findings if f.get("severity") == "high"]

        # Safety override — if there are critical/high findings, never approve
        approved = data.get("approved_for_deployment", False)
        if critical_findings or high_findings:
            approved = False

        return {
            "overall_risk": overall_risk,
            "summary": data.get("summary", ""),
            "findings": findings,
            "critical_finding_count": len(critical_findings),
            "high_finding_count": len(high_findings),
            "total_findings": len(findings),
            "secure_practices_observed": data.get("secure_practices_observed", []),
            "recommendations": data.get("recommendations", []),
            "approved_for_deployment": approved,
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
    raise ValueError("No JSON object found in security engineer output.")
