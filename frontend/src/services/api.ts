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
  const [baseRes, ollamaRes] = await Promise.allSettled([
    request<any>('/health'),
    request<any>('/health/ollama'),
  ]);

  const baseHealth: any =
    baseRes.status === 'fulfilled' ? baseRes.value : { status: 'ok', version: '0.1.0' };

  if (ollamaRes.status === 'fulfilled' && ollamaRes.value) {
    const o = ollamaRes.value;
    const isOnline = o.reachable && (o.model_available || o.status === 'ok');
    baseHealth.ollama = {
      status: isOnline ? 'available' : 'unavailable',
      base_url: o.base_url || 'http://localhost:11434',
      configured_model: o.model_name || 'qwen2.5-coder:7b',
      model_available: Boolean(o.model_available),
      available_models: o.available_models || [],
      error: o.error,
    };
  } else {
    baseHealth.ollama = {
      status: 'unavailable',
      base_url: 'http://localhost:11434',
      configured_model: 'qwen2.5-coder:7b',
      model_available: false,
      available_models: [],
    };
  }
  return baseHealth as SystemHealth;
}

export async function getOllamaHealth() {
  return request<any>('/health/ollama');
}

// Projects
export async function getProjects(page = 1, pageSize = 50): Promise<{ projects: Project[]; total: number }> {
  const data = await request<any>(`/projects?page=${page}&page_size=${pageSize}`);
  const list = data?.items || data?.projects || [];
  return { projects: list, total: data?.total ?? list.length };
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
  const data = await request<any>(`/projects/${projectId}/tasks`);
  const list = data?.items || data?.tasks || [];
  return { tasks: list, total: data?.total ?? list.length };
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



// ---------------------------------------------------------------------------
// Terminal & Execution Center API
// ---------------------------------------------------------------------------

export async function getTerminalSecurityStatus(): Promise<import('../types').TerminalSecurityStatus> {
  return request('/terminal/security/status');
}

export async function getTerminalSessions(projectId?: string): Promise<import('../types').TerminalSession[]> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/terminal/sessions${query}`);
}

export async function createTerminalSession(payload: {
  project_id: string;
  name?: string;
  shell_type?: string;
  working_directory?: string;
}): Promise<import('../types').TerminalSession> {
  return request('/terminal/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateTerminalSession(
  sessionId: string,
  payload: { name?: string; status?: string }
): Promise<import('../types').TerminalSession> {
  return request(`/terminal/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function closeTerminalSession(sessionId: string): Promise<void> {
  await request(`/terminal/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

export async function executeTerminalCommand(
  sessionId: string,
  payload: {
    command: string;
    working_directory?: string;
    agent_id?: string;
    timeout_seconds?: number;
  }
): Promise<import('../types').TerminalCommand> {
  return request(`/terminal/sessions/${sessionId}/execute`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function interruptTerminalSession(sessionId: string): Promise<{ interrupted: boolean }> {
  return request(`/terminal/sessions/${sessionId}/interrupt`, {
    method: 'POST',
  });
}

export async function clearTerminalSession(sessionId: string): Promise<{ cleared: boolean }> {
  return request(`/terminal/sessions/${sessionId}/clear`, {
    method: 'POST',
  });
}

export async function getTerminalHistory(
  sessionId: string,
  limit: number = 50,
  offset: number = 0
): Promise<import('../types').TerminalCommand[]> {
  return request(`/terminal/sessions/${sessionId}/history?limit=${limit}&offset=${offset}`);
}

export async function getTerminalCommandDetails(commandId: string): Promise<import('../types').TerminalCommand> {
  return request(`/terminal/commands/${commandId}`);
}

export async function getTerminalProcesses(projectId?: string): Promise<import('../types').TerminalProcess[]> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/terminal/processes${query}`);
}

export async function stopTerminalProcess(processId: number): Promise<{ stopped: boolean }> {
  return request(`/terminal/processes/${processId}/stop`, {
    method: 'POST',
  });
}

export async function getSpecializedConsole(
  consoleType: string,
  projectId?: string
): Promise<{ console_type: string; count: number; commands: import('../types').TerminalCommand[] }> {
  const query = projectId && projectId !== 'all' ? `?project_id=${projectId}` : '';
  return request(`/terminal/consoles/${consoleType}${query}`);
}

export function getTerminalExportUrl(sessionId: string, format: string): string {
  return `${API_BASE}/terminal/sessions/${sessionId}/export?format=${format}`;
}

export function connectTerminalStream(
  sessionId: string,
  onEvent: (item: import('../types').TerminalEventItem) => void,
  onError?: (err: any) => void
): () => void {
  const url = `${API_BASE}/terminal/sessions/${sessionId}/stream`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data && data.type !== 'ping') {
        onEvent(data);
      }
    } catch (err) {
      console.error('Failed to parse terminal stream event:', err);
    }
  };

  ['stdout', 'stderr', 'status', 'system', 'error'].forEach((type) => {
    eventSource.addEventListener(type, (e: any) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(data);
      } catch (err) {
        console.error(`Failed to parse event ${type}:`, err);
      }
    });
  });

  eventSource.onerror = (err) => {
    onError?.(err);
  };

  return () => {
    eventSource.close();
  };
}


// ─── Free Developer Services Integrations API ────────────────────────────────

export async function getIntegrations(
  category?: string
): Promise<import('../types').IntegrationStatusResponse[]> {
  const q = category ? `?category=${category}` : '';
  const res = await fetch(`${API_BASE}/integrations/${q}`);
  if (!res.ok) throw new Error('Failed to load integrations');
  return res.json();
}

export async function toggleIntegration(
  providerId: string,
  enabled: boolean
): Promise<{ provider_id: string; enabled: boolean }> {
  const res = await fetch(`${API_BASE}/integrations/${providerId}/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error('Failed to toggle integration');
  return res.json();
}

export async function testIntegration(
  providerId: string
): Promise<import('../types').IntegrationTestResult> {
  const res = await fetch(`${API_BASE}/integrations/${providerId}/test`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to test integration');
  return res.json();
}

export async function runSecurityAudit(
  projectId: string
): Promise<import('../types').SecurityAuditResult> {
  const res = await fetch(`${API_BASE}/integrations/security/audit/${projectId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to run security audit');
  return res.json();
}

export async function getCloudflareStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/integrations/cloudflare/status`);
  if (!res.ok) throw new Error('Failed to fetch Cloudflare status');
  return res.json();
}

export async function getBackblazeArtifacts(projectId?: string): Promise<any[]> {
  const q = projectId ? `?project_id=${projectId}` : '';
  const res = await fetch(`${API_BASE}/integrations/backblaze/artifacts${q}`);
  if (!res.ok) throw new Error('Failed to fetch Backblaze artifacts');
  return res.json();
}

export async function triggerBetterStackHeartbeat(): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/integrations/betterstack/heartbeat`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to send heartbeat');
  return res.json();
}


// ─── Product Quality Engineering & Validation System API ─────────────────────

export async function runQualityAudit(
  projectId: string,
  options?: { build_id?: string; run_load_test?: boolean; max_load_stages?: number }
): Promise<import('../types').QualityCertificationReport> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options || {}),
  });
  if (!res.ok) throw new Error('Failed to run quality audit');
  return res.json();
}

export async function getQualityReports(
  projectId: string
): Promise<any[]> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/reports`);
  if (!res.ok) throw new Error('Failed to fetch quality reports');
  return res.json();
}

export async function getLatestQualityGates(
  projectId: string
): Promise<import('../types').QualityGateResult[]> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/gates`);
  if (!res.ok) throw new Error('Failed to fetch quality gates');
  return res.json();
}

export async function getLoadTestRuns(
  projectId: string
): Promise<import('../types').LoadTestStageResult[]> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/load-tests`);
  if (!res.ok) throw new Error('Failed to fetch load test runs');
  return res.json();
}

export async function runLoadTest(
  projectId: string,
  options?: { test_path?: string; max_stages?: number }
): Promise<import('../types').LoadTestStageResult[]> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/load-test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options || {}),
  });
  if (!res.ok) throw new Error('Failed to execute load test');
  return res.json();
}

export async function getQualityBugs(
  projectId: string
): Promise<import('../types').BugRecord[]> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/bugs`);
  if (!res.ok) throw new Error('Failed to fetch quality bugs');
  return res.json();
}

export async function recordBugRepair(
  projectId: string,
  bugId: string,
  payload: { fix_summary: string; retest_passed: boolean; verification_evidence: string }
): Promise<any> {
  const res = await fetch(`${API_BASE}/quality/${projectId}/bugs/${bugId}/repair`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to record bug repair');
  return res.json();
}
