"""
Pydantic schemas for Terminal and Command Execution Center.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TerminalSessionCreate(BaseModel):
    project_id: str = Field(..., description="Target project ID")
    name: str = Field(default="Main Terminal", max_length=128)
    shell_type: str = Field(default="powershell", description="powershell | cmd | bash | docker")
    working_directory: str | None = Field(default=None, description="Optional initial subfolder")


class TerminalSessionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, description="active | closed")


class TerminalSessionResponse(BaseModel):
    id: str
    project_id: str
    name: str
    shell_type: str
    working_directory: str
    created_by: str
    status: str
    created_at: str
    closed_at: str | None = None
    running_command: str | None = None
    active_pid: int | None = None
    exit_code: int | None = None


class TerminalExecuteRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Command string to execute")
    working_directory: str | None = Field(
        default=None, description="Optional custom working directory"
    )
    agent_id: str | None = Field(default=None, description="Agent identity if agent-initiated")
    task_id: str | None = Field(default=None)
    run_id: str | None = Field(default=None)
    trace_id: str | None = Field(default=None)
    timeout_seconds: int = Field(default=60, ge=1, le=600)


class TerminalCommandResponse(BaseModel):
    id: str
    session_id: str
    project_id: str
    agent_id: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    command: str
    working_directory: str
    process_id: int | None = None
    started_at: str
    completed_at: str | None = None
    duration_ms: int | None = None
    exit_code: int | None = None
    status: str
    stdout_preview: str | None = None
    stderr_preview: str | None = None


class TerminalProcessInfo(BaseModel):
    process_id: int
    session_id: str
    project_id: str
    command: str
    started_by: str
    agent_name: str | None = None
    started_at: str
    duration_seconds: float
    status: str
    cpu_percent: float | None = None
    memory_mb: float | None = None


class TerminalEventItem(BaseModel):
    type: str  # stdout | stderr | status | system | error
    data: str
    sequence: int = 0
    timestamp: str | None = None


class TerminalExportResponse(BaseModel):
    session_id: str
    project_id: str
    format: str
    content: str
    line_count: int
