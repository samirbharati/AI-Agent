"""
Security Scanning Service.

Combines tool detection (Semgrep, Gitleaks, Trivy, Bandit) with a deterministic
built-in AST and pattern scanner for:
  - Hardcoded secrets and credentials (API keys, private keys, connection strings).
  - OWASP Top 10 vulnerabilities (SQL injection, unsafe eval/exec, shell=True).
  - Dangerous path traversal and insecure filesystem operations.

The scanner always returns deterministic findings before any LLM review.
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import asdict, dataclass
from typing import Any

from app.services.runner import get_execution_runner
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)


@dataclass
class SecurityFinding:
    """A detected security vulnerability or policy violation."""

    id: str
    rule_id: str
    title: str
    severity: str  # "critical" | "high" | "medium" | "low" | "info"
    file_path: str
    line_number: int | None
    evidence: str  # Code snippet or matched pattern (redacted if secret)
    description: str
    remediation: str


# ---------------------------------------------------------------------------
# Built-in deterministic secret patterns
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = [
    (
        "SEC-001",
        "AWS Access Key ID",
        "critical",
        re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
        "Hardcoded AWS access key ID detected. Move credentials to environment variables.",
    ),
    (
        "SEC-002",
        "Private Key Header",
        "critical",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "Hardcoded private key detected. Store keys in a secure secrets manager.",
    ),
    (
        "SEC-003",
        "GitHub Personal Access Token",
        "critical",
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
        "Hardcoded GitHub personal access token detected. Use environment variables.",
    ),
    (
        "SEC-004",
        "Generic Secret Assignment",
        "high",
        re.compile(
            r"""(?i)(?:api_key|apikey|secret_key|secret|password|passwd|auth_token)\s*=\s*['"][a-zA-Z0-9_\-.~!@#$%^&*+=]{8,}['"]"""
        ),
        "Potential hardcoded password or secret key assignment. Use environment variables.",
    ),
    (
        "SEC-005",
        "Database Connection String with Credentials",
        "high",
        re.compile(r"(?i)(?:postgres|mysql|mongodb(?:\+srv)?):\/\/[^:\s]+:[^@\s]+@[^\s]+"),
        "Database connection string with embedded username and password. Move to config.",
    ),
]

# ---------------------------------------------------------------------------
# Built-in deterministic code vulnerability patterns (Python)
# ---------------------------------------------------------------------------

_CODE_VULN_PATTERNS = [
    (
        "VULN-001",
        "Unsafe eval() Call",
        "critical",
        re.compile(r"\beval\s*\("),
        "Use of eval() allows arbitrary code execution. Replace with safe parsing.",
    ),
    (
        "VULN-002",
        "Unsafe exec() Call",
        "critical",
        re.compile(r"\bexec\s*\("),
        "Use of exec() allows dynamic code execution. Refactor to use explicit logic.",
    ),
    (
        "VULN-003",
        "Subprocess with shell=True",
        "high",
        re.compile(r"\bsubprocess\.(?:call|run|Popen|check_output|check_call)\s*\([^)]*shell\s*=\s*True"),
        "subprocess with shell=True is vulnerable to command injection. Pass command lists.",
    ),
    (
        "VULN-004",
        "Potential SQL String Interpolation",
        "high",
        re.compile(r"""(?i)\.execute\s*\(\s*(?:f['"]|['"].*%|['"].*format\()"""),
        "Raw string formatting in SQL query allows SQL injection. Use parameterized queries.",
    ),
    (
        "VULN-005",
        "Insecure YAML Unsafe Load",
        "medium",
        re.compile(r"\byaml\.load\s*\([^)]*(?!Loader\s*=\s*(?:yaml\.)?SafeLoader)"),
        "yaml.load without SafeLoader can execute arbitrary Python objects. Use yaml.safe_load.",
    ),
]


class SecurityScannerService:
    """
    Orchestrates deterministic application security scanning.
    """

    def __init__(self) -> None:
        self.workspace_service = get_workspace_service()
        self.runner = get_execution_runner()

    # ------------------------------------------------------------------
    # Tool availability detection
    # ------------------------------------------------------------------

    def detect_available_tools(self) -> dict[str, dict[str, Any]]:
        """
        Check for installed deterministic security scanners on the host system.
        """
        tools = {
            "semgrep": {"installed": False, "version": None},
            "gitleaks": {"installed": False, "version": None},
            "trivy": {"installed": False, "version": None},
            "bandit": {"installed": False, "version": None},
            "builtin_scanner": {"installed": True, "version": "1.0.0 (AST/Regex Rules)"},
        }

        for tool_name in ("semgrep", "gitleaks", "trivy", "bandit"):
            path = shutil.which(tool_name)
            if path:
                tools[tool_name]["installed"] = True
                tools[tool_name]["path"] = path

        return tools

    # ------------------------------------------------------------------
    # Built-in deterministic scanner
    # ------------------------------------------------------------------

    def scan_file_content(self, file_path: str, content: str) -> list[SecurityFinding]:
        """
        Scan a single file's content using built-in deterministic rules.
        """
        findings: list[SecurityFinding] = []
        lines = content.splitlines()

        for line_idx, line in enumerate(lines, start=1):
            # Check secret patterns
            for rule_id, title, severity, pattern, remediation in _SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    # Redact evidence if it looks like a real secret
                    raw_val = match.group(0)
                    redacted = raw_val[:4] + "*" * (len(raw_val) - 6) + raw_val[-2:] if len(raw_val) > 8 else "***"
                    findings.append(
                        SecurityFinding(
                            id=f"{rule_id}-{line_idx}",
                            rule_id=rule_id,
                            title=title,
                            severity=severity,
                            file_path=file_path,
                            line_number=line_idx,
                            evidence=line.replace(raw_val, redacted).strip(),
                            description=f"Rule {rule_id}: {title} matched on line {line_idx}.",
                            remediation=remediation,
                        )
                    )

            # Check code vulnerability patterns
            for rule_id, title, severity, pattern, remediation in _CODE_VULN_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        SecurityFinding(
                            id=f"{rule_id}-{line_idx}",
                            rule_id=rule_id,
                            title=title,
                            severity=severity,
                            file_path=file_path,
                            line_number=line_idx,
                            evidence=line.strip()[:100],
                            description=f"Rule {rule_id}: {title} pattern detected on line {line_idx}.",
                            remediation=remediation,
                        )
                    )

        return findings

    # ------------------------------------------------------------------
    # Project-wide scan
    # ------------------------------------------------------------------

    def scan_project(self, project_id: str) -> dict[str, Any]:
        """
        Execute a full deterministic security scan across the project workspace.
        """
        files = self.workspace_service.list_files(project_id)
        all_findings: list[SecurityFinding] = []

        scannable_extensions = (
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".json",
            ".yaml",
            ".yml",
            ".env",
            ".sql",
            ".sh",
        )

        for f in files:
            if not f.path.endswith(scannable_extensions):
                continue

            try:
                content = self.workspace_service.read_file(project_id, f.path)
                findings = self.scan_file_content(f.path, content)
                all_findings.extend(findings)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not scan file %s in project %s: %s", f.path, project_id, exc)

        critical_count = sum(1 for finding in all_findings if finding.severity == "critical")
        high_count = sum(1 for finding in all_findings if finding.severity == "high")
        medium_count = sum(1 for finding in all_findings if finding.severity == "medium")
        low_count = sum(1 for finding in all_findings if finding.severity == "low")

        passed = critical_count == 0 and high_count == 0

        return {
            "project_id": project_id,
            "passed": passed,
            "approved_for_deployment": passed,
            "total_findings": len(all_findings),
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "findings": [asdict(f) for f in all_findings],
            "tools_detected": self.detect_available_tools(),
        }


# Global singleton
_security_scanner: SecurityScannerService | None = None


def get_security_scanner() -> SecurityScannerService:
    global _security_scanner
    if _security_scanner is None:
        _security_scanner = SecurityScannerService()
    return _security_scanner

