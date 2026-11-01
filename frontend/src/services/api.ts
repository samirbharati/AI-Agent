import type {
  Artifact,
  ArtifactDetail,
  AgentRun,
  GitStatus,
  Project,
  ProjectCreatePayload,
  QATestResult,
  SecurityScanReport,
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

// Security & QA operations
export async function scanProjectSecurity(projectId: string): Promise<SecurityScanReport> {
  return request<SecurityScanReport>(`/projects/${projectId}/security/scan`);
}

export async function getDetectedSecurityTools(): Promise<{
  tools: Record<string, { installed: boolean; path?: string; version?: string }>;
}> {
  return request<{ tools: Record<string, { installed: boolean; path?: string; version?: string }> }>(
    '/security/tools'
  );
}

export async function runProjectTests(projectId: string, timeout = 60): Promise<QATestResult> {
  return request<QATestResult>(`/projects/${projectId}/qa/run-tests?timeout=${timeout}`, {
    method: 'POST',
  });
}

export async function getProjectTestFiles(
  projectId: string
): Promise<{ project_id: string; total: number; test_files: string[] }> {
  return request<{ project_id: string; total: number; test_files: string[] }>(
    `/projects/${projectId}/qa/test-files`
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

// ---------------------------------------------------------------------------
// Monitoring & Observability API
// ---------------------------------------------------------------------------

export async function getMonitoringEvents(params: {
  project_id?: string;
  severity?: string;
  source?: string;
  category?: string;
  status?: string;
  search?: string;
  time_range?: string;
  trace_id?: string;
  task_id?: string;
  page?: number;
  page_size?: number;
}): Promise<{ items: import('../types').MonitoringEvent[]; total: number; page: number; page_size: number; total_pages: number }> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== '' && val !== 'all') {
      query.set(key, String(val));
    }
  });
  return request(`/monitoring/events?${query.toString()}`);
}

export async function getMonitoringStats(projectId?: string): Promise<import('../types').MonitoringStats> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/monitoring/stats${query}`);
}

export async function getAgentMonitoringStates(projectId?: string): Promise<import('../types').AgentMonitoringState[]> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/monitoring/agents${query}`);
}

export async function getLLMRequests(projectId?: string): Promise<import('../types').LLMIntelligenceReport> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/monitoring/llm-requests${query}`);
}

export async function getToolExecutions(projectId?: string): Promise<import('../types').ToolExecutionRecord[]> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/monitoring/tools${query}`);
}

export async function getIncidents(projectId?: string): Promise<import('../types').IncidentRecord[]> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/monitoring/incidents${query}`);
}

export async function getMonitoringSecurityEvents(projectId?: string): Promise<import('../types').SecurityFinding[]> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/monitoring/security-events${query}`);
}

export function getLogsExportUrl(params: {
  format: string;
  project_id?: string;
  severity?: string;
  source?: string;
  category?: string;
  search?: string;
}): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '' && v !== 'all') {
      query.set(k, String(v));
    }
  });
  return `${API_BASE}/monitoring/export?${query.toString()}`;
}

export function connectMonitoringStream(
  onEvent: (event: import('../types').MonitoringEvent) => void,
  onError?: (err: any) => void,
  projectId?: string,
  lastEventId?: string,
): () => void {
  const query = new URLSearchParams();
  if (projectId && projectId !== 'all') query.set('project_id', projectId);
  if (lastEventId) query.set('last_event_id', lastEventId);

  const url = `${API_BASE}/monitoring/stream?${query.toString()}`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.id && data.message) {
        onEvent({
          id: data.id,
          project_id: data.project_id,
          event_type: data.event_type,
          message: data.message,
          severity: data.severity || 'info',
          source: data.source || 'system',
          category: data.category || 'system',
          status: data.status || data.severity || 'info',
          task_id: data.task_id,
          trace_id: data.trace_id,
          duration_ms: data.duration_ms,
          payload: data.payload || {},
          timestamp: data.timestamp || new Date().toISOString(),
        });
      }
    } catch (err) {
      console.error('Failed to parse monitoring stream event:', err);
    }
  };

  eventSource.onerror = (err) => {
    onError?.(err);
  };

  return () => {
    eventSource.close();
  };
}

