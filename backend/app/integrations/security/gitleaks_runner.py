"""
Gitleaks Secret Detection Integration Provider.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from app.config import get_settings
from app.integrations.base import IntegrationProvider
from app.integrations.schemas import (
    IntegrationCategory,
    ProviderHealth,
    ProviderStatus,
    ProviderUsage,
)
from app.integrations.security.schemas import (
    IntegratedFindingSeverity,
    IntegratedSecurityFinding,
    SecurityScannerType,
    SecurityScanReport,
)

logger = logging.getLogger(__name__)

# High-fidelity regex rules matching Gitleaks patterns
GITLEAKS_PATTERNS = [
    (
        r"(?i)(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}",
        "github-pat",
        "GitHub Personal Access Token",
        IntegratedFindingSeverity.CRITICAL,
    ),
    (
        r"(?i)(?:AKIA|ABIA|ACCA)[0-9A-Z]{16}",
        "aws-access-key-id",
        "AWS Access Key ID",
        IntegratedFindingSeverity.HIGH,
    ),
    (
        r"(?i)ai_agent_secret_[0-9a-f]{32}",
        "generic-agent-key",
        "AgentForge API Secret Token",
        IntegratedFindingSeverity.CRITICAL,
    ),
    (
        r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "private-key",
        "Asymmetric Private Cryptographic Key",
        IntegratedFindingSeverity.CRITICAL,
    ),
    (
        r"(?i)(?:postgres|mysql|sqlite):\/\/[^\s:]+:[^\s@]+@[^\s\/]+",
        "db-connection-string",
        "Database Connection URL with Embedded Password",
        IntegratedFindingSeverity.HIGH,
    ),
    (
        r"(?i)(?:bearer|token)\s+[a-zA-Z0-9_\-\.]{30,}",
        "bearer-token",
        "Hardcoded Bearer Authentication Token",
        IntegratedFindingSeverity.HIGH,
    ),
]


class GitleaksRunner(IntegrationProvider):
    """
    Gitleaks secret and credential scanner.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def provider_id(self) -> str:
        return "gitleaks"

    @property
    def name(self) -> str:
        return "Gitleaks"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.SECURITY

    @property
    def description(self) -> str:
        return "High-performance secret scanner detecting hardcoded credentials, API keys, tokens, and private keys."

    @property
    def free_tier_info(self) -> str:
        return "100% Free Open-Source CLI & Pre-commit Hook (unlimited local scanning)."

    @property
    def features(self) -> list[str]:
        return [
            "Git Commit & Working Tree Scanning",
            "API Key & Token Pattern Detection",
            "Cloud Credentials (AWS, GCP, Azure)",
            "Private Key & Certificate Detection",
            "Entropy Analysis",
        ]

    def is_enabled(self) -> bool:
        return self._settings.gitleaks_enabled

    def has_credentials(self) -> bool:
        return True

    def is_cli_available(self) -> bool:
        return shutil.which("gitleaks") is not None

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED, message="Gitleaks integration disabled."
            )

        if self.is_cli_available():
            try:
                out = subprocess.check_output(["gitleaks", "version"], text=True, timeout=5).strip()
                return ProviderHealth(
                    status=ProviderStatus.CONNECTED,
                    message=f"Gitleaks CLI ready (v{out})",
                    details={"cli": True, "version": out},
                )
            except Exception as e:
                return ProviderHealth(
                    status=ProviderStatus.ERROR,
                    message=f"Gitleaks CLI error: {e}",
                    details={"error": str(e)},
                )

        return ProviderHealth(
            status=ProviderStatus.CONNECTED,
            message="Gitleaks CLI not installed; running in native high-fidelity regex pattern detection mode.",
            details={"cli": False, "mode": "pattern_engine"},
        )

    async def get_usage(self) -> ProviderUsage | None:
        return ProviderUsage(
            quota_used=0.0,
            quota_total=None,
            quota_unit="scans",
            description="Unlimited secret scans via Gitleaks pattern engine",
        )

    def scan_directory(self, target_dir: str | Path, project_id: str) -> SecurityScanReport:
        """Scan workspace for leaked secrets."""
        start = time.perf_counter()
        target_path = Path(target_dir)

        if not target_path.exists():
            return SecurityScanReport(
                scanner=SecurityScannerType.GITLEAKS,
                project_id=project_id,
                duration_ms=0.0,
                target_path=str(target_path),
            )

        findings: list[IntegratedSecurityFinding] = []
        engine = "cli" if self.is_cli_available() else "fallback_analyzer"

        if self.is_cli_available():
            findings = self._run_cli_scan(target_path)
        else:
            findings = self._run_pattern_scan(target_path)

        duration = (time.perf_counter() - start) * 1000.0
        crit = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.HIGH)

        return SecurityScanReport(
            scanner=SecurityScannerType.GITLEAKS,
            project_id=project_id,
            duration_ms=round(duration, 2),
            findings=findings,
            critical_count=crit,
            high_count=high,
            total_count=len(findings),
            engine_type=engine,
            target_path=str(target_path),
        )

    def _run_cli_scan(self, target_path: Path) -> list[IntegratedSecurityFinding]:
        report_file = target_path / ".gitleaks_tmp_report.json"
        cmd = [
            "gitleaks",
            "dir",
            str(target_path),
            "--report-format",
            "json",
            "--report-path",
            str(report_file),
            "--no-git",
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
            findings: list[IntegratedSecurityFinding] = []
            if report_file.exists():
                data = json.loads(report_file.read_text(encoding="utf-8"))
                report_file.unlink(missing_ok=True)
                for idx, r in enumerate(data):
                    findings.append(
                        IntegratedSecurityFinding(
                            id=f"gitleaks-{idx}-{r.get('RuleID', 'secret')}",
                            scanner=SecurityScannerType.GITLEAKS,
                            rule_id=r.get("RuleID", "gitleaks-secret"),
                            severity=IntegratedFindingSeverity.CRITICAL,
                            title=f"Exposed {r.get('Description', 'Secret')}",
                            description=f"Secret identified in {r.get('File')}: {r.get('Secret', '')[:4]}...[REDACTED]",
                            file_path=r.get("File"),
                            line_number=r.get("StartLine"),
                            remediation="Rotate this credential immediately and move it to environment variables.",
                        )
                    )
            return findings
        except Exception as e:
            logger.warning("Gitleaks CLI scan failed, using fallback pattern scan: %s", e)
            return self._run_pattern_scan(target_path)

    def _run_pattern_scan(self, target_path: Path) -> list[IntegratedSecurityFinding]:
        findings: list[IntegratedSecurityFinding] = []
        count = 0
        compiled = [
            (re.compile(pat), rule_id, title, sev) for pat, rule_id, title, sev in GITLEAKS_PATTERNS
        ]

        for root, _, files in os.walk(target_path):
            for file in files:
                if file.startswith(".git") or file.endswith((".pyc", ".png", ".jpg", ".db")):
                    continue
                file_path = Path(root) / file
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    for line_idx, line in enumerate(lines, 1):
                        for regex, rule_id, title, sev in compiled:
                            if regex.search(line):
                                count += 1
                                rel_path = str(file_path.relative_to(target_path))
                                findings.append(
                                    IntegratedSecurityFinding(
                                        id=f"gitleaks-pattern-{count}-{rule_id}",
                                        scanner=SecurityScannerType.GITLEAKS,
                                        rule_id=f"gitleaks.{rule_id}",
                                        severity=sev,
                                        title=title,
                                        description=f"Detected potentially exposed secret in {rel_path}:{line_idx}.",
                                        file_path=rel_path,
                                        line_number=line_idx,
                                        code_snippet=line[:40] + "...[REDACTED]",
                                        remediation="Revoke and rotate this credential immediately. Never commit secrets to source control.",
                                    )
                                )
                except Exception as exc:
                    logger.debug("Failed reading file %s: %s", file_path, exc)
        return findings


_gitleaks_runner_instance: GitleaksRunner | None = None


def get_gitleaks_runner() -> GitleaksRunner:
    global _gitleaks_runner_instance
    if _gitleaks_runner_instance is None:
        _gitleaks_runner_instance = GitleaksRunner()
    return _gitleaks_runner_instance
