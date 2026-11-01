"""
Security Breaker Suite for Product Quality Validation.
Performs deterministic multi-vector penetration simulation and vulnerability scanning:
- Authentication & Authorization bypass
- Insecure Direct Object References (IDOR)
- Injection attacks (SQLi, Command Injection, Code Injection)
- Cross-Site Scripting (XSS)
- Server-Side Request Forgery (SSRF)
- Hardcoded secrets and credential leaks
- Insecure dependencies / CVEs
"""

from __future__ import annotations

import logging
import re
import uuid

from app.quality.schemas import SecurityBreakerFinding, SecurityBreakerSummary
from app.services.security_scanner import SecurityScannerService
from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)

# Specialized breaker patterns to catch subtle vulnerabilities
_ADDITIONAL_BREAKER_PATTERNS = [
    (
        "IDOR-001",
        "idor",
        "Missing Authorization Check on Resource ID",
        "high",
        re.compile(r"""def\s+[a-zA-Z0-9_]+\s*\([^)]*(?:user_id|account_id|id)\s*:[^)]*\):(?:\s*#[^\n]*\n|\s*\n)*(?!\s*if\s+.*current_user|\s*check_owner|\s*require_permission)"""),
        "Endpoint accepts object ID without verifying ownership against authenticated session.",
        "Ensure current_user or session token owns the requested entity before mutating or returning.",
    ),
    (
        "AUTH-001",
        "auth",
        "Hardcoded Admin / Token Bypass",
        "critical",
        re.compile(r"""(?:if\s+token\s*==\s*['"](?:admin|superuser|bypass|dev)['"]|debug_mode\s*=\s*True)"""),
        "Authentication logic contains a hardcoded bypass or insecure debug mode.",
        "Remove all authentication bypass backdoors and debug overrides.",
    ),
    (
        "SSRF-001",
        "ssrf",
        "Unvalidated URL Inbound for HTTP Client",
        "high",
        re.compile(r"""(?:requests\.(?:get|post|put)|httpx\.(?:get|post|put)|urllib\.request\.urlopen)\s*\(\s*(?:url|req_url|user_url|target)"""),
        "Network request constructed with unvalidated user-supplied URL allows SSRF to cloud metadata or internal network.",
        "Validate destination URL against an explicit domain allowlist and reject loopback/private IP ranges.",
    ),
    (
        "XSS-001",
        "xss",
        "Direct HTML / InnerHTML Markup Injection",
        "medium",
        re.compile(r"""(?:dangerouslySetInnerHTML|innerHTML\s*=|v-html\s*=)"""),
        "Unsanitized user data passed to innerHTML or dangerouslySetInnerHTML creates XSS vector.",
        "Sanitize HTML using DOMPurify or use standard text bindings.",
    ),
]


class SecurityBreakerSuite:
    """
    Simulates automated adversarial penetration attacks and static vulnerability audits
    against project code and configuration.
    """

    def __init__(self) -> None:
        self.workspace = get_workspace_service()
        self.scanner_service = SecurityScannerService()

    def run_security_break(self, project_id: str) -> SecurityBreakerSummary:
        """
        Execute comprehensive security breaker analysis on the project workspace.
        """
        findings: list[SecurityBreakerFinding] = []
        secrets_count = 0

        # 1. Run core deterministic scanner
        try:
            scan_result = self.scanner_service.scan_project(project_id)
            for raw_finding in scan_result.get("findings", []):
                rule_id = raw_finding.get("rule_id", "")
                sev = raw_finding.get("severity", "medium").lower()
                title = raw_finding.get("title", "")

                vector = "sqli"
                if "SEC-" in rule_id:
                    vector = "secrets"
                    secrets_count += 1
                elif "CMD-" in rule_id or "EXEC-" in rule_id or "VULN-003" in rule_id:
                    vector = "sqli"
                elif "VULN-004" in rule_id:
                    vector = "sqli"
                elif "VULN-001" in rule_id or "VULN-002" in rule_id:
                    vector = "sqli"
                elif "DEP-" in rule_id:
                    vector = "deps"

                findings.append(
                    SecurityBreakerFinding(
                        id=f"brk-{uuid.uuid4().hex[:8]}",
                        vector=vector,
                        severity=sev,
                        title=title,
                        description=raw_finding.get("description", ""),
                        reproduction_steps=f"Inspect file '{raw_finding.get('file_path')}' at line {raw_finding.get('line_number')}.",
                        affected_file=raw_finding.get("file_path"),
                        remediation=raw_finding.get("remediation"),
                    )
                )
        except Exception as exc:
            logger.warning("Error running base security scanner on project %s: %s", project_id, exc)

        # 2. Run advanced breaker rules
        try:
            files = self.workspace.list_files(project_id)
            for f in files:
                if not f.path.endswith((".py", ".js", ".ts", ".tsx", ".jsx")):
                    continue

                try:
                    content = self.workspace.read_file(project_id, f.path)
                except Exception as exc:
                    logger.debug("Skipping unreadable file %s: %s", f.path, exc)
                    continue

                for rule_id, vector, title, sev, pattern, desc, rem in _ADDITIONAL_BREAKER_PATTERNS:
                    if pattern.search(content):
                        findings.append(
                            SecurityBreakerFinding(
                                id=f"brk-{uuid.uuid4().hex[:8]}",
                                vector=vector,
                                severity=sev,
                                title=title,
                                description=f"Pattern {rule_id}: {desc}",
                                reproduction_steps=f"Trigger code path in {f.path} without credentials or with attacker payload.",
                                affected_file=f.path,
                                remediation=rem,
                            )
                        )
        except Exception as exc:
            logger.warning("Error checking additional breaker rules for project %s: %s", project_id, exc)

        # 3. Aggregate metrics
        crit_count = sum(1 for f in findings if f.severity == "critical")
        high_count = sum(1 for f in findings if f.severity == "high")
        med_count = sum(1 for f in findings if f.severity == "medium")
        low_count = sum(1 for f in findings if f.severity == "low")

        logger.info(
            "Security Breaker on %s finished: %d total (%d crit, %d high, %d med, %d low, %d secrets)",
            project_id,
            len(findings),
            crit_count,
            high_count,
            med_count,
            low_count,
            secrets_count,
        )

        return SecurityBreakerSummary(
            total_vulnerabilities=len(findings),
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            exposed_secrets_count=secrets_count,
            findings=findings,
        )
