import type {
  Artifact,
  ArtifactDetail,
  AgentRun,
  GitStatus,
  Project,
  ProjectCreatePayload,
  SystemHealth,
  Task,
  WorkflowEvent,
  WorkflowStatusResponse,
  WorkspaceFile,
  WorkspaceFileContent,
} from '../types';

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await res.json();
      errorDetail =
        typeof errJson.detail === 'string'
          ? errJson.detail
          : errJson.detail?.message || JSON.stringify(errJson.detail);
    } catch {
      errorDetail = `HTTP ${res.status}: ${res.statusText}`;
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

// Health & telemetry
export async function getHealth(): Promise<SystemHealth> {
  return request<SystemHealth>('/health');
}

export async function getOllamaHealth() {
  return request<any>('/health/ollama');
}

// Projects
export async function getProjects(page = 1, pageSize = 50): Promise<{ projects: Project[]; total: number }> {
  return request<{ projects: Project[]; total: number }>(`/projects?page=${page}&page_size=${pageSize}`);
}

export async function getProject(projectId: string): Promise<Project> {
  return request<Project>(`/projects/${projectId}`);
}

export async function createProject(payload: ProjectCreatePayload): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// Approvals & gates
export async function approveRequirements(projectId: string, comments = ''): Promise<void> {
  await request(`/projects/${projectId}/requirements/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved: true, comments }),
  });
}

export async function approveArchitecture(projectId: string, comments = ''): Promise<void> {
  await request(`/projects/${projectId}/architecture/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved: true, comments }),
  });
}

// Workflow operations
export async function startWorkflow(projectId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/projects/${projectId}/workflow/start`, {
    method: 'POST',
  });
}

export async function resumeWorkflow(projectId: string): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/projects/${projectId}/workflow/resume`, {
    method: 'POST',
  });
}

export async function getWorkflowStatus(projectId: string): Promise<WorkflowStatusResponse> {
  return request<WorkflowStatusResponse>(`/projects/${projectId}/workflow/status`);
}

// Tasks
export async function getTasks(projectId: string): Promise<{ tasks: Task[]; total: number }> {
  return request<{ tasks: Task[]; total: number }>(`/projects/${projectId}/tasks`);
}

// Artifacts
export async function getArtifacts(projectId: string): Promise<{ artifacts: Artifact[]; total: number }> {
  return request<{ artifacts: Artifact[]; total: number }>(`/projects/${projectId}/artifacts`);
}

export async function getArtifactContent(projectId: string, artifactName: string): Promise<ArtifactDetail> {
  return request<ArtifactDetail>(`/projects/${projectId}/artifacts/${encodeURIComponent(artifactName)}`);
}

// Agent runs
export async function getAgentRuns(projectId: string): Promise<{ runs: AgentRun[]; total: number }> {
  return request<{ runs: AgentRun[]; total: number }>(`/projects/${projectId}/agent-runs`);
}

// Workspace & Git operations
export async function getWorkspaceFiles(
  projectId: string,
  subpath = ''
): Promise<{ project_id: string; total: number; files: WorkspaceFile[] }> {
  const query = subpath ? `?subpath=${encodeURIComponent(subpath)}` : '';
  return request<{ project_id: string; total: number; files: WorkspaceFile[] }>(
    `/projects/${projectId}/files${query}`
  );
}

export async function getWorkspaceFileContent(
  projectId: string,
  path: string
): Promise<WorkspaceFileContent> {
  return request<WorkspaceFileContent>(
    `/projects/${projectId}/files/content?path=${encodeURIComponent(path)}`
  );
}

export async function getGitStatus(projectId: string): Promise<GitStatus> {
  return request<GitStatus>(`/projects/${projectId}/git/status`);
}

export async function getGitDiff(
  projectId: string,
  baseBranch = 'main'
): Promise<{ project_id: string; base_branch: string; diff: string }> {
  return request<{ project_id: string; base_branch: string; diff: string }>(
    `/projects/${projectId}/git/diff?base_branch=${encodeURIComponent(baseBranch)}`
  );
}

// SSE Event Stream helper
export function connectWorkflowEvents(
  projectId: string,
  onEvent: (event: WorkflowEvent) => void,
  onHeartbeat?: () => void,
  onError?: (err: Event) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/projects/${projectId}/workflow/events`);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event_type === 'heartbeat') {
        onHeartbeat?.();
      } else {
        onEvent({
          id: event.lastEventId || String(Date.now()),
          event_type: data.event_type,
          message: data.message,
          severity: data.severity || 'info',
          project_status: data.project_status,
          created_at: data.created_at || new Date().toISOString(),
        });
      }
    } catch (e) {
      console.error('Failed to parse SSE event:', e);
    }
  };

  eventSource.onerror = (err) => {
    onError?.(err);
  };

  return () => {
    eventSource.close();
  };
}

