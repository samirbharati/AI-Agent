"""
Semgrep Static Application Security Testing (SAST) Runner.
"""

from __future__ import annotations

import json
import logging
import os
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


class SemgrepRunner(IntegrationProvider):
    """
    Semgrep SAST Integration Provider.
    Invokes the local 'semgrep' CLI when installed; otherwise uses a native AST/pattern fallback.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def provider_id(self) -> str:
        return "semgrep"

    @property
    def name(self) -> str:
        return "Semgrep SAST"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.SECURITY

    @property
    def description(self) -> str:
        return "Fast, open-source static analysis engine for finding bugs and enforcing security guardrails."

    @property
    def free_tier_info(self) -> str:
        return "100% Free Open-Source CLI & Community Rules Registry (no limits on local scans)."

    @property
    def features(self) -> list[str]:
        return [
            "OWASP Top 10 SAST Scanning",
            "SQL Injection Detection",
            "Command Injection Checks",
            "Insecure Cryptography Rules",
            "Custom Rule Definitions",
        ]

    def is_enabled(self) -> bool:
        return self._settings.semgrep_enabled

    def has_credentials(self) -> bool:
        return True  # Semgrep OSS does not require credentials for local scans

    def is_cli_available(self) -> bool:
        return shutil.which("semgrep") is not None

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED, message="Semgrep integration is disabled."
            )

        if self.is_cli_available():
            try:
                out = subprocess.check_output(
                    ["semgrep", "--version"], text=True, timeout=5
                ).strip()
                return ProviderHealth(
                    status=ProviderStatus.CONNECTED,
                    message=f"Semgrep CLI ready (v{out})",
                    details={"cli": True, "version": out},
                )
            except Exception as e:
                return ProviderHealth(
                    status=ProviderStatus.ERROR,
                    message=f"Semgrep CLI error: {e}",
                    details={"error": str(e)},
                )

        return ProviderHealth(
            status=ProviderStatus.CONNECTED,
            message="Semgrep CLI not detected; running in native AST security analysis fallback mode.",
            details={"cli": False, "mode": "ast_pattern_fallback"},
        )

    async def get_usage(self) -> ProviderUsage | None:
        return ProviderUsage(
            quota_used=0.0,
            quota_total=None,
            quota_unit="scans",
            description="Unlimited local SAST scanning via Semgrep OSS",
        )

    def scan_directory(self, target_dir: str | Path, project_id: str) -> SecurityScanReport:
        """Scan target directory with Semgrep CLI or native AST fallback."""
        start_time = time.perf_counter()
        target_path = Path(target_dir)

        if not target_path.exists():
            return SecurityScanReport(
                scanner=SecurityScannerType.SEMGREP,
                project_id=project_id,
                duration_ms=0.0,
                target_path=str(target_path),
            )

        findings: list[IntegratedSecurityFinding] = []
        engine = "cli" if self.is_cli_available() else "fallback_analyzer"

        if self.is_cli_available():
            findings = self._run_cli_scan(target_path)
        else:
            findings = self._run_fallback_scan(target_path)

        duration = (time.perf_counter() - start_time) * 1000.0

        crit = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.HIGH)
        med = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.MEDIUM)
        low = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.LOW)

        return SecurityScanReport(
            scanner=SecurityScannerType.SEMGREP,
            project_id=project_id,
            duration_ms=round(duration, 2),
            findings=findings,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            total_count=len(findings),
            engine_type=engine,
            target_path=str(target_path),
        )

    def _run_cli_scan(self, target_path: Path) -> list[IntegratedSecurityFinding]:
        cmd = ["semgrep", "scan", "--json", "--quiet", "--config", "p/default", str(target_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
            data = json.loads(res.stdout) if res.stdout else {}
            results = data.get("results", [])
            findings: list[IntegratedSecurityFinding] = []
            for idx, r in enumerate(results):
                sev_map = {
                    "ERROR": IntegratedFindingSeverity.HIGH,
                    "WARNING": IntegratedFindingSeverity.MEDIUM,
                    "INFO": IntegratedFindingSeverity.LOW,
                }
                findings.append(
                    IntegratedSecurityFinding(
                        id=f"semgrep-{idx}-{r.get('check_id', 'rule')}",
                        scanner=SecurityScannerType.SEMGREP,
                        rule_id=r.get("check_id", "semgrep-rule"),
                        severity=sev_map.get(
                            r.get("extra", {}).get("severity", "WARNING"),
                            IntegratedFindingSeverity.MEDIUM,
                        ),
                        title=r.get("check_id", "Semgrep Finding")
                        .split(".")[-1]
                        .replace("-", " ")
                        .title(),
                        description=r.get("extra", {}).get("message", "Semgrep security finding"),
                        file_path=r.get("path"),
                        line_number=r.get("start", {}).get("line"),
                        code_snippet=r.get("extra", {}).get("lines"),
                        remediation=r.get("extra", {}).get("fix"),
                    )
                )
            return findings
        except Exception as e:
            logger.warning("Semgrep CLI scan failed, using fallback: %s", e)
            return self._run_fallback_scan(target_path)

    def _run_fallback_scan(self, target_path: Path) -> list[IntegratedSecurityFinding]:
        """Built-in static analysis scanner matching standard high-risk patterns."""
        findings: list[IntegratedSecurityFinding] = []
        patterns = [
            (
                "eval(",
                IntegratedFindingSeverity.CRITICAL,
                "arbitrary-code-execution",
                "Dangerous Use of eval()",
                "Using eval() allows execution of arbitrary code and may lead to remote code execution.",
                "Replace eval() with safe parsers such as ast.literal_eval() or json.loads().",
            ),
            (
                "shell=True",
                IntegratedFindingSeverity.HIGH,
                "subprocess-shell-true",
                "Subprocess Execution with shell=True",
                "Spawning processes with shell=True is susceptible to OS command injection.",
                "Pass command arguments as an array and set shell=False.",
            ),
            (
                'execute(f"',
                IntegratedFindingSeverity.CRITICAL,
                "sql-injection-fstring",
                "SQL Query via F-String Interpolation",
                "Constructing SQL queries using f-strings allows SQL injection attacks.",
                "Use parameterized SQL queries with bind variables (:param) instead of string interpolation.",
            ),
            (
                "verify=False",
                IntegratedFindingSeverity.HIGH,
                "tls-verification-disabled",
                "TLS Certificate Verification Disabled",
                "Disabling TLS certificate verification permits man-in-the-middle attacks.",
                "Enable SSL/TLS verification (verify=True).",
            ),
        ]

        count = 0
        for root, _, files in os.walk(target_path):
            for file in files:
                if file.endswith((".py", ".js", ".ts")):
                    file_path = Path(root) / file
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        for p_str, sev, rule, title, desc, rem in patterns:
                            if p_str in content:
                                lines = content.splitlines()
                                line_no = 1
                                snippet = ""
                                for i, line_content in enumerate(lines, 1):
                                    if p_str in line_content:
                                        line_no = i
                                        snippet = line_content.strip()
                                        break
                                count += 1
                                rel_path = str(file_path.relative_to(target_path))
                                findings.append(
                                    IntegratedSecurityFinding(
                                        id=f"semgrep-fallback-{count}-{rule}",
                                        scanner=SecurityScannerType.SEMGREP,
                                        rule_id=f"python.security.{rule}",
                                        severity=sev,
                                        title=title,
                                        description=desc,
                                        file_path=rel_path,
                                        line_number=line_no,
                                        code_snippet=snippet,
                                        remediation=rem,
                                    )
                                )
                    except Exception as exc:
                        logger.debug("Failed reading %s: %s", file_path, exc)
        return findings


_semgrep_runner_instance: SemgrepRunner | None = None


def get_semgrep_runner() -> SemgrepRunner:
    global _semgrep_runner_instance
    if _semgrep_runner_instance is None:
        _semgrep_runner_instance = SemgrepRunner()
    return _semgrep_runner_instance
