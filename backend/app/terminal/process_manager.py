"""
Asynchronous Process Execution and Lifecycle Manager.

Manages running child processes:
- Non-blocking asynchronous stdout and stderr streaming.
- Execution timeouts and graceful cancellation (SIGTERM / terminate then kill).
- Process tracking with PID, duration, and status.
- Orphan prevention with shutdown cleanup hooks.
- Bounded memory buffers per process to prevent exhaustion.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.terminal.terminal_security import TerminalSecurity

logger = logging.getLogger(__name__)


@dataclass
class RunningProcess:
    pid: int
    process: asyncio.subprocess.Process
    session_id: str
    project_id: str
    command_str: str
    agent_id: str | None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "running"
    stdout_buffer: deque[str] = field(default_factory=lambda: deque(maxlen=2000))
    stderr_buffer: deque[str] = field(default_factory=lambda: deque(maxlen=2000))
    is_cancelled: bool = False
    exit_code: int | None = None
    duration_ms: int | None = None


class ProcessManager:
    """Singleton process manager for all active terminal executions."""

    def __init__(self, max_concurrent_processes: int = 10) -> None:
        self.max_concurrent_processes = max_concurrent_processes
        self._processes: dict[int, RunningProcess] = {}
        self._lock = asyncio.Lock()

    async def execute_command(
        self,
        command_str: str,
        cwd: str,
        session_id: str,
        project_id: str,
        shell_type: str = "powershell",
        agent_id: str | None = None,
        timeout_seconds: int = 60,
        output_callback: Callable[[str, str, int], Any] | None = None,
    ) -> RunningProcess:
        """
        Launch a command subprocess asynchronously and stream output.

        Args:
            command_str: Command line string.
            cwd: Working directory (must be validated by caller).
            session_id: Target terminal session ID.
            project_id: Associated project ID.
            shell_type: Desired shell (powershell, cmd, bash, docker).
            agent_id: Initiating agent role, if any.
            timeout_seconds: Maximum allowed execution time.
            output_callback: Callback invoked with (stream, line, seq_number).

        Returns:
            RunningProcess record after execution completes or terminates.
        """
        async with self._lock:
            # Enforce concurrent running process limit
            running_count = sum(1 for p in self._processes.values() if p.status == "running")
            if running_count >= self.max_concurrent_processes:
                raise RuntimeError(
                    f"Process limit reached ({self.max_concurrent_processes} active). Stop an existing process first."
                )

        sanitized_env = TerminalSecurity.sanitize_env()
        args = self._build_shell_args(command_str, shell_type)
        start_mono = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                cwd=cwd,
                env=sanitized_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )
        except Exception as exc:
            logger.error("Failed to spawn process for command '%s': %s", command_str, exc)
            dummy_proc = RunningProcess(
                pid=0,
                process=None,  # type: ignore[arg-type]
                session_id=session_id,
                project_id=project_id,
                command_str=command_str,
                agent_id=agent_id,
                status="failed",
                exit_code=127,
                duration_ms=0,
            )
            dummy_proc.stderr_buffer.append(f"Process spawn error: {exc}\n")
            if output_callback:
                res = output_callback("stderr", f"Process spawn error: {exc}\n", 1)
                if asyncio.iscoroutine(res):
                    await res
            return dummy_proc

        run_proc = RunningProcess(
            pid=proc.pid,
            process=proc,
            session_id=session_id,
            project_id=project_id,
            command_str=command_str,
            agent_id=agent_id,
            status="running",
        )

        async with self._lock:
            self._processes[proc.pid] = run_proc

        seq = 0

        async def _read_stream(stream: asyncio.StreamReader, stream_name: str) -> None:
            nonlocal seq
            buffer = run_proc.stdout_buffer if stream_name == "stdout" else run_proc.stderr_buffer
            while True:
                line_bytes = await stream.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                redacted_line = TerminalSecurity.redact(line)
                buffer.append(redacted_line)
                seq += 1
                if output_callback:
                    try:
                        res = output_callback(stream_name, redacted_line, seq)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        logger.debug("Output callback error: %s", cb_err)

        try:
            # Concurrently read stdout and stderr with timeout
            await asyncio.wait_for(
                asyncio.gather(
                    _read_stream(proc.stdout, "stdout"),  # type: ignore[arg-type]
                    _read_stream(proc.stderr, "stderr"),  # type: ignore[arg-type]
                    proc.wait(),
                ),
                timeout=float(timeout_seconds),
            )
            run_proc.exit_code = proc.returncode
            run_proc.status = "completed" if proc.returncode == 0 else "failed"

        except TimeoutError:
            logger.warning("Process %d timed out after %ds", proc.pid, timeout_seconds)
            run_proc.status = "timed_out"
            run_proc.is_cancelled = True
            await self._kill_proc(proc)
            run_proc.exit_code = -1
            timeout_msg = f"\n[Process killed: timed out after {timeout_seconds} seconds]\n"
            run_proc.stderr_buffer.append(timeout_msg)
            seq += 1
            if output_callback:
                res = output_callback("stderr", timeout_msg, seq)
                if asyncio.iscoroutine(res):
                    await res

        except asyncio.CancelledError:
            run_proc.status = "cancelled"
            run_proc.is_cancelled = True
            await self._kill_proc(proc)
            run_proc.exit_code = -15
            cancel_msg = "\n[Process cancelled by user interrupt]\n"
            run_proc.stderr_buffer.append(cancel_msg)
            seq += 1
            if output_callback:
                res = output_callback("stderr", cancel_msg, seq)
                if asyncio.iscoroutine(res):
                    await res
            raise

        finally:
            elapsed_ms = int((time.monotonic() - start_mono) * 1000)
            run_proc.duration_ms = elapsed_ms
            # Keep process in registry for history, but mark non-running

        return run_proc

    def _build_shell_args(self, command_str: str, shell_type: str) -> list[str]:
        """Resolve executable and wrapper arguments according to shell type."""
        shell_lower = shell_type.lower()
        if sys.platform == "win32":
            if shell_lower in ("powershell", "pwsh"):
                ps_bin = shutil.which("pwsh") or shutil.which("powershell") or "powershell.exe"
                return [ps_bin, "-NoProfile", "-NonInteractive", "-Command", command_str]
            if shell_lower == "cmd":
                return ["cmd.exe", "/c", command_str]
            if shell_lower in ("bash", "wsl"):
                wsl_bin = shutil.which("wsl")
                if wsl_bin:
                    return [wsl_bin, "-e", "bash", "-c", command_str]
            # Default to PowerShell on Windows
            ps_bin = shutil.which("powershell") or "powershell.exe"
            return [ps_bin, "-NoProfile", "-NonInteractive", "-Command", command_str]
        else:
            # POSIX
            if shell_lower in ("bash", "sh"):
                sh_bin = shutil.which("bash") or "/bin/sh"
                return [sh_bin, "-c", command_str]
            return ["/bin/sh", "-c", command_str]

    async def stop_process(self, pid: int) -> bool:
        """
        Stop an active process gracefully with SIGTERM then SIGKILL.

        Returns:
            True if process was found and stopped, False otherwise.
        """
        async with self._lock:
            run_proc = self._processes.get(pid)
            if not run_proc or not run_proc.process or run_proc.status != "running":
                return False

            run_proc.status = "terminating"
            run_proc.is_cancelled = True

        proc = run_proc.process
        await self._kill_proc(proc)
        run_proc.status = "cancelled"
        run_proc.exit_code = -15
        return True

    async def _kill_proc(self, proc: asyncio.subprocess.Process) -> None:
        """Terminate and kill a subprocess safely."""
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.5)
            except TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.debug("Error while terminating process: %s", e)

    def get_process(self, pid: int) -> RunningProcess | None:
        return self._processes.get(pid)

    def list_processes(
        self,
        session_id: str | None = None,
        project_id: str | None = None,
        active_only: bool = False,
    ) -> list[RunningProcess]:
        procs = list(self._processes.values())
        if session_id:
            procs = [p for p in procs if p.session_id == session_id]
        if project_id:
            procs = [p for p in procs if p.project_id == project_id]
        if active_only:
            procs = [p for p in procs if p.status == "running"]
        return sorted(procs, key=lambda x: x.started_at, reverse=True)

    async def cleanup_all_processes(self) -> None:
        """Terminate all remaining child processes during application shutdown."""
        running = [p for p in self._processes.values() if p.status == "running" and p.process]
        for p in running:
            await self._kill_proc(p.process)
            p.status = "cancelled"


# Global singleton
_process_manager_instance: ProcessManager | None = None


def get_process_manager() -> ProcessManager:
    global _process_manager_instance
    if _process_manager_instance is None:
        _process_manager_instance = ProcessManager()
    return _process_manager_instance
