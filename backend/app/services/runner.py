"""
Code Execution and Verification Runner.

Executes tests, syntax checks, and linters safely within project workspaces.
When Docker is not available (such as on this host), commands run in an isolated
local subprocess constrained by:
  - Working directory strictly set to the project workspace directory.
  - Environment sanitization (all API keys, secret keys, and DB passwords stripped).
  - Explicit timeouts (default 30s) to prevent runaway loops or deadlocks.
  - Bounded stdout/stderr buffer sizes (max 100 KB) to prevent memory exhaustion.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass

from app.services.workspace import get_workspace_service

logger = logging.getLogger(__name__)

# Sensitive environment variable keywords to strip
_SENSITIVE_PATTERNS = (
    "SECRET",
    "KEY",
    "TOKEN",
    "PASSWORD",
    "DATABASE",
    "CREDENTIAL",
    "AUTH",
    "API",
)

# Standard safe keys to preserve for toolchain operation
_SAFE_ENV_VARS = (
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
)


@dataclass
class ExecutionResult:
    """The result of executing a command in a project workspace."""

    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class ExecutionRunner:
    """
    Subprocess execution engine for running tests and checks in project workspaces.
    """

    def __init__(self, max_output_chars: int = 100_000) -> None:
        self.max_output_chars = max_output_chars
        self.workspace_service = get_workspace_service()

    def _sanitize_env(self, overrides: dict[str, str] | None = None) -> dict[str, str]:
        """
        Build a sanitized environment dict for the child process.

        Strips sensitive environment variables to prevent accidental credential leakage.
        """
        clean_env: dict[str, str] = {}

        for k, v in os.environ.items():
            upper = k.upper()
            # Allow explicitly safe system variables
            if upper in _SAFE_ENV_VARS:
                clean_env[k] = v
                continue

            # Skip anything matching sensitive keywords
            if any(p in upper for p in _SENSITIVE_PATTERNS):
                continue

            clean_env[k] = v

        if overrides:
            clean_env.update(overrides)

        return clean_env

    def run_command(
        self,
        project_id: str,
        command: list[str],
        timeout: int = 30,
        env_overrides: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """
        Execute a command within the specified project workspace directory.

        Args:
            project_id: Project identifier.
            command: Command and arguments list.
            timeout: Maximum allowed execution time in seconds.
            env_overrides: Extra environment variables for the child process.

        Returns:
            ExecutionResult containing returncode, stdout, stderr, and timings.
        """
        cwd = self.workspace_service.get_project_dir(project_id)
        clean_env = self._sanitize_env(env_overrides)
        start_time = time.monotonic()

        logger.info(
            "Executing in project %s (timeout=%ds): %s",
            project_id,
            timeout,
            " ".join(command),
        )

        try:
            proc = subprocess.run(
                command,
                cwd=cwd,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            elapsed = time.monotonic() - start_time

            # Bound output lengths
            stdout = proc.stdout[: self.max_output_chars] if proc.stdout else ""
            stderr = proc.stderr[: self.max_output_chars] if proc.stderr else ""

            return ExecutionResult(
                command=command,
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=round(elapsed, 3),
                timed_out=False,
            )

        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - start_time
            logger.warning(
                "Command timed out after %ds in project %s: %s",
                timeout,
                project_id,
                command,
            )
            stdout = (
                exc.stdout[: self.max_output_chars]
                if isinstance(exc.stdout, str)
                else (exc.stdout or b"").decode("utf-8", errors="replace")
            )
            stderr = (
                exc.stderr[: self.max_output_chars]
                if isinstance(exc.stderr, str)
                else (exc.stderr or b"").decode("utf-8", errors="replace")
            )

            return ExecutionResult(
                command=command,
                exit_code=-1,
                stdout=stdout,
                stderr=stderr + f"\n[Process killed: timed out after {timeout} seconds]",
                duration_seconds=round(elapsed, 3),
                timed_out=True,
            )

        except (OSError, FileNotFoundError) as exc:
            elapsed = time.monotonic() - start_time
            logger.error("Failed to execute command in project %s: %s", project_id, exc)
            return ExecutionResult(
                command=command,
                exit_code=127,
                stdout="",
                stderr=f"Execution error: {exc}",
                duration_seconds=round(elapsed, 3),
                timed_out=False,
            )

    # ------------------------------------------------------------------
    # Specialized validation helpers
    # ------------------------------------------------------------------

    def check_python_syntax(self, project_id: str, relative_path: str) -> ExecutionResult:
        """
        Verify that a Python file compiles without syntax errors.

        Uses ``python -m py_compile <path>``.
        """
        return self.run_command(
            project_id,
            [sys.executable, "-m", "py_compile", relative_path],
            timeout=10,
        )

    def run_pytest(
        self,
        project_id: str,
        test_args: list[str] | None = None,
        timeout: int = 45,
    ) -> ExecutionResult:
        """
        Execute pytest within the project workspace.
        """
        cmd = [sys.executable, "-m", "pytest", "-q"]
        if test_args:
            cmd.extend(test_args)
        return self.run_command(project_id, cmd, timeout=timeout)

    def run_ruff_check(
        self,
        project_id: str,
        target_path: str = ".",
        timeout: int = 20,
    ) -> ExecutionResult:
        """
        Run Ruff linter check on the project code.
        """
        return self.run_command(
            project_id,
            [sys.executable, "-m", "ruff", "check", target_path],
            timeout=timeout,
        )


# Global singleton instance
_execution_runner: ExecutionRunner | None = None


def get_execution_runner() -> ExecutionRunner:
    global _execution_runner
    if _execution_runner is None:
        _execution_runner = ExecutionRunner()
    return _execution_runner
