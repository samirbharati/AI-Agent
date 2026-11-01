"""
Schemas for Semgrep, Gitleaks, and Trivy security scanners.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SecurityScannerType(str, Enum):
    SEMGREP = "semgrep"
    GITLEAKS = "gitleaks"
    TRIVY = "trivy"


class IntegratedFindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IntegratedSecurityFinding(BaseModel):
    id: str
    scanner: SecurityScannerType
    rule_id: str
    severity: IntegratedFindingSeverity
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    column_number: int | None = None
    code_snippet: str | None = None
    remediation: str | None = None
    raw_details: dict[str, Any] = Field(default_factory=dict)


class SecurityScanReport(BaseModel):
    scanner: SecurityScannerType
    project_id: str
    scan_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: float
    findings: list[IntegratedSecurityFinding] = Field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_count: int = 0
    engine_type: str = "cli"  # "cli" or "fallback_analyzer"
    target_path: str = ""
