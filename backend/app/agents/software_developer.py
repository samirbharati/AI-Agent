"""
Software Developer Agent.

Implements an assigned task by generating source code, configuration files,
and CLI commands. All output is structured as a JSON artifact manifest that
the workspace manager uses to write files to disk.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm_client import LLMClientConfig, LLMMessage

_SYSTEM_PROMPT = """\
You are a senior Software Developer implementing a specific task in an AI-assisted \
development workflow. You must produce production-quality code.

Output a single valid JSON object with this exact structure:
{
  "files": [
    {
      "path": "relative/path/to/file.py",
      "content": "full file content as a string",
      "action": "create|modify|delete",
      "description": "What this file does and why it was created/modified."
    }
  ],
  "commands": [
    {
      "command": "pip install some-package",
      "reason": "Required for the new feature.",
      "working_directory": ".",
      "safe_to_run": true
    }
  ],
  "implementation_notes": "Any important notes about the implementation.",
  "tests_included": true,
  "estimated_loc": 150
}

Rules:
- Read the existing architecture and follow it strictly.
- Write complete file contents — never truncate with "# ... rest of file".
- Include unit tests in a separate test file for every new module.
- Follow the project's language and framework conventions.
- Never hardcode secrets, API keys, or passwords.
- All paths are relative to the project root.
- Only set safe_to_run=true for commands that are safe to execute in any env.
- Do NOT output anything outside the JSON object.
"""


class SoftwareDeveloperAgent(BaseAgent):
    agent_id = "software-developer"
    agent_name = "Software Developer"
    default_system_prompt = _SYSTEM_PROMPT

    def __init__(self) -> None:
        super().__init__(llm_config=LLMClientConfig(temperature=0.15, max_tokens=6000))

    def build_messages(self, context: dict[str, Any]) -> list[LLMMessage]:
        task_title = context.get("task_title", "Unnamed Task")
        task_description = context.get("task_description", "")
        acceptance_criteria = context.get("acceptance_criteria", "")
        architecture_summary = context.get("architecture_summary", "")
        existing_files = context.get("existing_files", {})  # {path: content}
        prior_attempts = context.get("prior_attempts", [])  # list of {output, error}

        existing_files_text = ""
        if existing_files:
            existing_files_text = "\n\nExisting Files:\n"
            for path, content in existing_files.items():
                existing_files_text += f"\n--- {path} ---\n{content}\n"

        repair_context = ""
        if prior_attempts:
            last = prior_attempts[-1]
            repair_context = (
                f"\n\nPrevious Attempt Failed:\n"
                f"Error: {last.get('error', 'Unknown error')}\n"
                f"Please fix the issue in your new implementation."
            )

        user_content = f"""\
Task Title: {task_title}

Task Description:
{task_description}

Acceptance Criteria:
{acceptance_criteria}

Architecture Summary:
{architecture_summary}
{existing_files_text}{repair_context}

Implement this task. Output only valid JSON.
"""
        return [LLMMessage(role="user", content=user_content)]

    def parse_output(self, raw_output: str, context: dict[str, Any]) -> dict[str, Any]:
        json_str = _extract_json(raw_output)
        data = json.loads(json_str)

        files = data.get("files", [])
        if not files:
            raise ValueError("Developer output contains no files.")

        valid_actions = {"create", "modify", "delete"}
        for f in files:
            if not f.get("path"):
                raise ValueError("A file entry is missing its path.")
            if f.get("action") not in valid_actions:
                f["action"] = "create"
            # Sanitise path — no absolute paths or path traversal
            path = f["path"].replace("\\", "/").lstrip("/")
            if ".." in path.split("/"):
                raise ValueError(f"Unsafe file path detected: {f['path']}")
            f["path"] = path

        # Validate commands
        commands = data.get("commands", [])
        safe_commands = [c for c in commands if c.get("safe_to_run", False)]

        return {
            "files": files,
            "commands": commands,
            "safe_commands": safe_commands,
            "implementation_notes": data.get("implementation_notes", ""),
            "tests_included": data.get("tests_included", False),
            "estimated_loc": data.get("estimated_loc", 0),
            "file_count": len(files),
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
    raise ValueError("No JSON object found in developer output.")
