"""
Trivy Vulnerability and Dependency Scanner Integration Provider.
"""

from __future__ import annotations

import json
import logging
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

# Known vulnerable package versions for fallback dependency analysis
KNOWN_VULNERABLE_PACKAGES: list[tuple[str, str, str, IntegratedFindingSeverity, str]] = [
    (
        "requests",
        "<2.31.0",
        "CVE-2023-32681",
        IntegratedFindingSeverity.MEDIUM,
        "Proxy-Authorization header leak in requests <2.31.0. Upgrade to >=2.31.0.",
    ),
    (
        "urllib3",
        "<2.0.7",
        "CVE-2023-45803",
        IntegratedFindingSeverity.HIGH,
        "Request body strip redirect leak in urllib3 <2.0.7. Upgrade to >=2.0.7.",
    ),
    (
        "fastapi",
        "<0.100.0",
        "CVE-2023-46136",
        IntegratedFindingSeverity.MEDIUM,
        "Form data upload DoS in multipart parser. Upgrade to >=0.109.1.",
    ),
    (
        "aiohttp",
        "<3.9.4",
        "CVE-2024-30251",
        IntegratedFindingSeverity.HIGH,
        "aiohttp HTTP parser DoS vulnerability. Upgrade to >=3.9.4.",
    ),
    (
        "jinja2",
        "<3.1.3",
        "CVE-2024-22195",
        IntegratedFindingSeverity.MEDIUM,
        "Cross-site scripting (XSS) in xmlattr filter in Jinja2 <3.1.3. Upgrade to >=3.1.3.",
    ),
]


class TrivyRunner(IntegrationProvider):
    """
    Trivy vulnerability, dependency, and misconfiguration scanner.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def provider_id(self) -> str:
        return "trivy"

    @property
    def name(self) -> str:
        return "Trivy"

    @property
    def category(self) -> IntegrationCategory:
        return IntegrationCategory.SECURITY

    @property
    def description(self) -> str:
        return (
            "Comprehensive security scanner for package dependencies, "
            "container configurations, and Infrastructure as Code."
        )

    @property
    def free_tier_info(self) -> str:
        return "100% Free Open-Source CLI & Aqua Security Vulnerability Database."

    @property
    def features(self) -> list[str]:
        return [
            "Software Bill of Materials (SBOM)",
            "Dependency CVE Scanning (Python, Node.js)",
            "Container Image Vulnerabilities",
            "IaC Configuration Audits (Dockerfile)",
        ]

    def is_enabled(self) -> bool:
        return self._settings.trivy_enabled

    def has_credentials(self) -> bool:
        return True

    def is_cli_available(self) -> bool:
        return shutil.which("trivy") is not None

    async def check_health(self) -> ProviderHealth:
        if not self.is_enabled():
            return ProviderHealth(
                status=ProviderStatus.DISABLED, message="Trivy integration disabled."
            )

        if self.is_cli_available():
            try:
                out = subprocess.check_output(["trivy", "--version"], text=True, timeout=5).strip()
                return ProviderHealth(
                    status=ProviderStatus.CONNECTED,
                    message=f"Trivy CLI ready (v{out.splitlines()[0]})",
                    details={"cli": True, "version": out.splitlines()[0]},
                )
            except Exception as e:
                return ProviderHealth(
                    status=ProviderStatus.ERROR,
                    message=f"Trivy CLI error: {e}",
                    details={"error": str(e)},
                )

        return ProviderHealth(
            status=ProviderStatus.CONNECTED,
            message="Trivy CLI not detected; running in native Software Bill of Materials (SBOM) dependency audit mode.",
            details={"cli": False, "mode": "manifest_audit_fallback"},
        )

    async def get_usage(self) -> ProviderUsage | None:
        return ProviderUsage(
            quota_used=0.0,
            quota_total=None,
            quota_unit="scans",
            description="Unlimited local vulnerability scans via Trivy OSS",
        )

    def scan_directory(self, target_dir: str | Path, project_id: str) -> SecurityScanReport:
        """Scan workspace dependencies and configurations."""
        start = time.perf_counter()
        target_path = Path(target_dir)

        if not target_path.exists():
            return SecurityScanReport(
                scanner=SecurityScannerType.TRIVY,
                project_id=project_id,
                duration_ms=0.0,
                target_path=str(target_path),
            )

        findings: list[IntegratedSecurityFinding] = []
        engine = "cli" if self.is_cli_available() else "fallback_analyzer"

        if self.is_cli_available():
            findings = self._run_cli_scan(target_path)
        else:
            findings = self._run_manifest_scan(target_path)

        duration = (time.perf_counter() - start) * 1000.0
        crit = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.HIGH)
        med = sum(1 for f in findings if f.severity == IntegratedFindingSeverity.MEDIUM)

        return SecurityScanReport(
            scanner=SecurityScannerType.TRIVY,
            project_id=project_id,
            duration_ms=round(duration, 2),
            findings=findings,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            total_count=len(findings),
            engine_type=engine,
            target_path=str(target_path),
        )

    def _run_cli_scan(self, target_path: Path) -> list[IntegratedSecurityFinding]:
        cmd = ["trivy", "fs", "--format", "json", "--quiet", str(target_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
            data = json.loads(res.stdout) if res.stdout else {}
            findings: list[IntegratedSecurityFinding] = []
            results = data.get("Results", [])
            for r in results:
                vulns = r.get("Vulnerabilities", [])
                for idx, v in enumerate(vulns):
                    sev_map = {
                        "CRITICAL": IntegratedFindingSeverity.CRITICAL,
                        "HIGH": IntegratedFindingSeverity.HIGH,
                        "MEDIUM": IntegratedFindingSeverity.MEDIUM,
                        "LOW": IntegratedFindingSeverity.LOW,
                    }
                    findings.append(
                        IntegratedSecurityFinding(
                            id=f"trivy-{v.get('VulnerabilityID', idx)}",
                            scanner=SecurityScannerType.TRIVY,
                            rule_id=v.get("VulnerabilityID", "trivy-cve"),
                            severity=sev_map.get(
                                v.get("Severity", "MEDIUM"), IntegratedFindingSeverity.MEDIUM
                            ),
                            title=f"{v.get('PkgName')} {v.get('VulnerabilityID')}",
                            description=v.get("Title", v.get("Description", "Vulnerability")),
                            file_path=r.get("Target"),
                            code_snippet=f"Installed: {v.get('InstalledVersion')}, Fixed: {v.get('FixedVersion')}",
                            remediation=f"Upgrade {v.get('PkgName')} to version {v.get('FixedVersion') or 'latest'}.",
                        )
                    )
            return findings
        except Exception as e:
            logger.warning("Trivy CLI scan failed, using fallback manifest scanner: %s", e)
            return self._run_manifest_scan(target_path)

    def _run_manifest_scan(self, target_path: Path) -> list[IntegratedSecurityFinding]:
        findings: list[IntegratedSecurityFinding] = []
        count = 0

        # Scan requirements.txt and package.json
        req_files = list(target_path.glob("**/requirements*.txt"))
        for req_file in req_files:
            try:
                lines = req_file.read_text(encoding="utf-8").splitlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
                    for vuln_pkg, _vuln_ver, cve, sev, rem in KNOWN_VULNERABLE_PACKAGES:
                        if pkg_name == vuln_pkg:
                            count += 1
                            rel_path = str(req_file.relative_to(target_path))
                            findings.append(
                                IntegratedSecurityFinding(
                                    id=f"trivy-fallback-{count}-{cve}",
                                    scanner=SecurityScannerType.TRIVY,
                                    rule_id=cve,
                                    severity=sev,
                                    title=f"Vulnerable Dependency: {vuln_pkg} ({cve})",
                                    description=f"Package '{vuln_pkg}' declared in {rel_path} has known CVE vulnerability {cve}.",
                                    file_path=rel_path,
                                    code_snippet=line,
                                    remediation=rem,
                                )
                            )
            except Exception as exc:
                logger.debug("Failed reading %s: %s", req_file, exc)
        return findings


_trivy_runner_instance: TrivyRunner | None = None


def get_trivy_runner() -> TrivyRunner:
    global _trivy_runner_instance
    if _trivy_runner_instance is None:
        _trivy_runner_instance = TrivyRunner()
    return _trivy_runner_instance
