"""
Security redaction utilities for the logging and monitoring pipeline.

Ensures credentials, private keys, connection strings, and sensitive tokens
are never persisted in event logs or exported in cleartext.
"""

from __future__ import annotations

import re
from typing import Any

# Patterns matching secret and credential values
_SECRET_PATTERNS = [
    # AWS access keys
    re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    # Private key headers
    re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ),
    # GitHub personal access tokens
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
    # JWT tokens
    re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
    # Generic bearer tokens
    re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.=:_+/]{16,}"),
    # Basic auth / DB connection strings with passwords (postgres://user:pass@host)
    re.compile(r"(?i)(?:postgres(?:ql)?|mysql|sqlite|redis|mongodb):\/\/[^:\s\/]+:([^@\s]+)@"),
    # Generic secret assignments (e.g. api_key = "...", password = "...")
    re.compile(
        r"""(?i)(?:password|passwd|pwd|secret|api_key|apikey|access_token|auth_token|client_secret)\s*[:=]\s*['"]([^'"]+)['"]"""
    ),
]

_SENSITIVE_KEY_NAMES = {
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "token",
    "private_key",
    "client_secret",
    "authorization",
    "cookie",
}


def redact_string(text: str) -> str:
    """
    Redact secrets and sensitive substrings from a text string.
    """
    if not text:
        return text

    redacted = text
    for pattern in _SECRET_PATTERNS:

        def _repl(match: re.Match) -> str:
            val = match.group(0)
            if len(val) > 16:
                return f"{val[:4]}...[REDACTED]...{val[-2:]}"
            return "[REDACTED]"

        redacted = pattern.sub(_repl, redacted)

    return redacted


def redact_metadata(obj: Any, depth: int = 0) -> Any:
    """
    Recursively redact sensitive keys and values in nested dictionaries or lists.
    Prevents deep recursion beyond 10 levels.
    """
    if depth > 10:
        return "[MAX_DEPTH]"

    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for k, v in obj.items():
            key_lower = str(k).lower()
            if any(sensitive in key_lower for sensitive in _SENSITIVE_KEY_NAMES):
                result[k] = "[REDACTED]"
            else:
                result[k] = redact_metadata(v, depth + 1)
        return result

    if isinstance(obj, list):
        return [redact_metadata(item, depth + 1) for item in obj]

    if isinstance(obj, str):
        return redact_string(obj)

    return obj
