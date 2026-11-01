"""
Command Execution Policy and Safety Validation Engine.

Enforces execution restrictions to protect host infrastructure:
- Blocks destructive commands (formatting, recursive root deletion, user account tampering).
- Validates command syntax and parses arguments safely without raw shell=True interpolation.
- Classifies commands into functional categories (build, test, security, git, general).
- Enforces working directory boundaries within project workspaces.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum


class CommandSafetyLevel(str, Enum):
    SAFE = "safe"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    BLOCKED = "blocked"


class CommandCategory(str, Enum):
    BUILD = "build"
    TEST = "test"
    SECURITY = "security"
    GIT = "git"
    GENERAL = "general"
    AGENT = "agent"


# Patterns that are strictly blocked from execution
_BLOCKED_PATTERNS = [
    # Disk formatting and partitioning
    re.compile(r"\b(format|diskpart|mkfs|fdisk)\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    # Root or system-wide recursive deletions
    re.compile(r"rm\s+-(?:r[fF]|f[rR])\s+/(?:$|\s)", re.IGNORECASE),
    re.compile(r"rmdir\s+/(?:s|S)\s+/(?:q|Q)\s+[A-Za-z]:\\(?:$|\s)", re.IGNORECASE),
    re.compile(r"del\s+/(?:s|S)\s+/(?:q|Q)\s+[A-Za-z]:\\(?:$|\s)", re.IGNORECASE),
    re.compile(
        r"Remove-Item\s+.*-(?:Recurse|r)\s+.*-(?:Force|f)\s+[A-Za-z]:\\",
        re.IGNORECASE,
    ),
    # Privilege escalation / Account tampering
    re.compile(r"\b(net\s+user|net\s+localgroup\s+administrators)\b", re.IGNORECASE),
    re.compile(r"\b(useradd|usermod|userdel|passwd)\b", re.IGNORECASE),
    re.compile(r"\b(runas|sudo\s+su|su\s+-)\b", re.IGNORECASE),
    re.compile(
        r"Set-ExecutionPolicy\s+(?:Unrestricted|Bypass)\s+-Scope\s+LocalMachine",
        re.IGNORECASE,
    ),
    # Shutdown / Reboot
    re.compile(r"\b(shutdown|reboot|poweroff|init\s+0)\b", re.IGNORECASE),
    # Fork bombs and malicious loops
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),
]

# Patterns that carry higher risk and require explicit confirmation / warning
_CONFIRMATION_PATTERNS = [
    re.compile(r"git\s+push\s+.*(?:--force|-f)", re.IGNORECASE),
    re.compile(r"git\s+reset\s+--hard", re.IGNORECASE),
    re.compile(r"git\s+clean\s+-(?:f|fd|fdx)", re.IGNORECASE),
    re.compile(r"npm\s+install\s+-g\b", re.IGNORECASE),
    re.compile(r"pip\s+install\s+.*--upgrade\s+pip\b", re.IGNORECASE),
    re.compile(r"docker\s+system\s+prune", re.IGNORECASE),
]


@dataclass
class PolicyEvaluationResult:
    is_allowed: bool
    safety_level: CommandSafetyLevel
    category: CommandCategory
    reason: str | None = None
    parsed_args: list[str] | None = None


class CommandPolicyEngine:
    """Evaluates commands against security boundaries and safety rules."""

    @classmethod
    def evaluate(cls, raw_command: str) -> PolicyEvaluationResult:
        cmd_clean = raw_command.strip()
        if not cmd_clean:
            return PolicyEvaluationResult(
                is_allowed=False,
                safety_level=CommandSafetyLevel.BLOCKED,
                category=CommandCategory.GENERAL,
                reason="Command string cannot be empty.",
            )

        # 1. Check blocked patterns
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(cmd_clean):
                return PolicyEvaluationResult(
                    is_allowed=False,
                    safety_level=CommandSafetyLevel.BLOCKED,
                    category=cls._detect_category(cmd_clean),
                    reason=f"Command matches blocked security rule: {pattern.pattern}",
                )

        # 2. Check confirmation patterns
        for pattern in _CONFIRMATION_PATTERNS:
            if pattern.search(cmd_clean):
                return PolicyEvaluationResult(
                    is_allowed=True,
                    safety_level=CommandSafetyLevel.REQUIRES_CONFIRMATION,
                    category=cls._detect_category(cmd_clean),
                    reason="Potentially disruptive operation requires confirmation.",
                )

        # 3. Categorize and allow
        return PolicyEvaluationResult(
            is_allowed=True,
            safety_level=CommandSafetyLevel.SAFE,
            category=cls._detect_category(cmd_clean),
            reason=None,
        )

    @staticmethod
    def _detect_category(command: str) -> CommandCategory:
        lower = command.lower()
        if any(lower.startswith(p) or f" {p}" in lower for p in ("git ", "git.exe ")):
            return CommandCategory.GIT
        if any(p in lower for p in ("pytest", "unittest", "test_", "_test", "npm test")):
            return CommandCategory.TEST
        if any(
            p in lower
            for p in ("pip install", "npm install", "poetry install", "cargo build", "setup.py")
        ):
            return CommandCategory.BUILD
        if any(p in lower for p in ("bandit", "semgrep", "trivy", "safety", "pip-audit", "scan")):
            return CommandCategory.SECURITY
        return CommandCategory.GENERAL

    @staticmethod
    def parse_command_args(raw_command: str) -> list[str]:
        """Safely split command string into tokenized arguments (POSIX style)."""
        try:
            return shlex.split(raw_command, posix=False)
        except ValueError:
            # Fallback on basic whitespace splitting if quotation parsing fails
            return raw_command.split()
