"""
Terminal Security & Workspace Boundary Defense.

Guarantees that:
1. Terminal processes cannot escape their project workspace directory (path traversal defense).
2. Child processes are launched in a sanitized environment without sensitive API keys or credentials.
3. All command strings, standard output, and standard error streams are automatically redacted.
4. Docker container isolation availability is reliably probed and reported.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.logging.redaction import redact_string
from app.services.workspace import get_workspace_service

# Environment variables allowed for toolchain operation
_SAFE_ENVIRONMENT_KEYS = {
    "PATH",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "COMSPEC",
    "PATHEXT",
    "PYTHONPATH",
    "PYTHONHOME",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "TERM",
    "COLORTERM",
    "LANG",
    "LC_ALL",
}

_SENSITIVE_KEY_SUBSTRINGS = (
    "SECRET",
    "KEY",
    "TOKEN",
    "PASSWORD",
    "DATABASE",
    "CREDENTIAL",
    "AUTH",
    "API",
)


class TerminalSecurity:
    """Security verification and sanitization for terminal sessions."""

    @staticmethod
    def sanitize_env(overrides: dict[str, str] | None = None) -> dict[str, str]:
        """Strip credentials, secrets, and auth tokens from environment dictionary."""
        sanitized: dict[str, str] = {}
        for k, v in os.environ.items():
            k_upper = k.upper()
            if k_upper in _SAFE_ENVIRONMENT_KEYS:
                sanitized[k] = v
                continue
            if any(s in k_upper for s in _SENSITIVE_KEY_SUBSTRINGS):
                continue
            sanitized[k] = v

        if overrides:
            for ok, ov in overrides.items():
                if not any(s in ok.upper() for s in _SENSITIVE_KEY_SUBSTRINGS):
                    sanitized[ok] = ov

        return sanitized

    @staticmethod
    def resolve_and_verify_cwd(project_id: str, requested_cwd: str | None = None) -> Path:
        """
        Verify that requested working directory is strictly inside project workspace.

        Raises:
            ValueError: If the target path traverses outside the project directory.
        """
        ws_service = get_workspace_service()
        project_root = ws_service.get_project_dir(project_id).resolve()

        if not requested_cwd:
            return project_root

        target_path = Path(requested_cwd)
        if not target_path.is_absolute():
            target_path = (project_root / target_path).resolve()
        else:
            target_path = target_path.resolve()

        # Strict containment check
        try:
            target_path.relative_to(project_root)
        except ValueError:
            raise ValueError(
                f"Working directory traversal rejected: '{requested_cwd}' is outside project workspace root."
            ) from None

        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)

        return target_path

    @staticmethod
    def redact(text: str | None) -> str:
        """Redact secrets and sensitive tokens from command lines, stdout, and stderr."""
        if not text:
            return ""
        return redact_string(text)

    @classmethod
    def check_docker_availability(cls) -> dict[str, str | bool]:
        """
        Probe whether Docker daemon is active and accessible.

        Returns status dictionary indicating sandbox capability.
        """
        docker_bin = shutil.which("docker")
        if not docker_bin:
            return {
                "available": False,
                "reason": "Docker CLI not installed on host.",
                "isolation_mode": "subprocess_sandbox",
            }

        try:
            proc = subprocess.run(
                [docker_bin, "info"],
                capture_output=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                return {
                    "available": True,
                    "reason": "Docker daemon running.",
                    "isolation_mode": "docker_container",
                }
            return {
                "available": False,
                "reason": "Docker CLI found but daemon not responding.",
                "isolation_mode": "subprocess_sandbox",
            }
        except Exception as e:
            return {
                "available": False,
                "reason": f"Docker check failed: {e}",
                "isolation_mode": "subprocess_sandbox",
            }
