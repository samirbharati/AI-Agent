export type ProjectStatus =
  | 'pending'
  | 'requirements_review'
  | 'requirements_approved'
  | 'requirements_revision'
  | 'architecture_review'
  | 'architecture_approved'
  | 'architecture_revision'
  | 'planning'
  | 'in_progress'
  | 'active'
  | 'implementing'
  | 'qa_review'
  | 'security_review'
  | 'code_review'
  | 'repair'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  preferred_language?: string;
  preferred_framework?: string;
  preferred_database?: string;
  max_repair_attempts: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreatePayload {
  name: string;
  description: string;
  preferred_language?: string;
  preferred_framework?: string;
  preferred_database?: string;
  max_repair_attempts?: number;
}

export type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'blocked'
  | 'cancelled';

export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_agent_id?: string;
  acceptance_criteria?: string;
  complexity?: string;
  estimated_hours?: number;
  actual_hours?: number;
  order_index: number;
  dependencies?: string[];
  created_at: string;
  updated_at: string;
}

export interface Artifact {
  id: string;
  name: string;
  artifact_type: string;
  created_at: string;
  content_length?: number;
}

export interface ArtifactDetail extends Artifact {
  project_id: string;
  content: string;
}

export interface AgentRun {
  id: string;
  agent_definition_id: string;
  status: 'pending' | 'running' | 'success' | 'failure' | 'error';
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  duration_seconds?: number;
  model_used?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface WorkflowEvent {
  id: string;
  event_type: string;
  message: string;
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  project_status?: string;
  created_at: string;
}

export interface WorkflowStatusResponse {
  project_id: string;
  project_name: string;
  status: ProjectStatus;
  tasks: {
    total: number;
    by_status: Record<string, number>;
  };
  agent_runs: {
    total: number;
    total_tokens_used: number;
  };
  recent_events: Array<{
    event_type: string;
    message: string;
    severity: string;
    created_at: string;
  }>;
  updated_at: string;
}

export interface OllamaHealth {
  status: 'available' | 'unavailable' | 'error';
  base_url: string;
  configured_model: string;
  model_available: boolean;
  available_models: string[];
  error?: string;
}

export interface SystemHealth {
  status: string;
  version: string;
  environment: string;
  ollama?: OllamaHealth;
}

export interface WorkspaceFile {
  path: string;
  size_bytes: number;
  modified_at: string;
}

export interface WorkspaceFileContent {
  project_id: string;
  path: string;
  content: string;
  size_bytes: number;
}

export interface GitStatus {
  project_id: string;
  initialized: boolean;
  branch: string | null;
  modified: string[];
  untracked: string[];
}

export interface SecurityFinding {
  id: string;
  rule_id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  file_path: string;
  line_number?: number;
  evidence: string;
  description: string;
  remediation: string;
}

export interface SecurityScanReport {
  project_id: string;
  passed: boolean;
  approved_for_deployment: boolean;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  findings: SecurityFinding[];
  tools_detected: Record<string, { installed: boolean; path?: string; version?: string }>;
}

export interface BugReport {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  test_name?: string;
  steps_to_reproduce: string[];
  expected_result: string;
  actual_result: string;
  stacktrace?: string;
}

export interface QATestResult {
  project_id: string;
  passed: boolean;
  status: string;
  total_tests: number;
  passed_count: number;
  failed_count: number;
  blocked_count: number;
  not_executed_count: number;
  duration_seconds: number;
  bugs: BugReport[];
  raw_stdout: string;
  raw_stderr: string;
}

export interface MonitoringEvent {
  id: string;
  project_id: string;
  event_type: string;
  message: string;
  severity: 'debug' | 'info' | 'warning' | 'error' | 'critical' | 'success';
  source: string;
  category: string;
  status: string;
  task_id?: string | null;
  agent_run_id?: string | null;
  trace_id?: string | null;
  parent_event_id?: string | null;
  duration_ms?: number | null;
  payload?: Record<string, any>;
  timestamp: string;
}

export interface MonitoringStats {
  total_events: number;
  successful_operations: number;
  warnings: number;
  errors: number;
  critical_events: number;
  active_agents: number;
  active_workflows: number;
}

export interface AgentMonitoringState {
  agent_id: string;
  agent_name: string;
  role: string;
  status: 'IDLE' | 'INITIALIZING' | 'RUNNING' | 'WAITING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'AWAITING APPROVAL';
  current_task?: string | null;
  completed_tasks: number;
  failed_tasks: number;
  total_runs: number;
  model_used: string;
  last_active?: string | null;
  duration_seconds?: number | null;
  latest_summary?: string | null;
}

export interface LLMRequestRecord {
  id: string;
  model_name: string;
  agent_role: string;
  duration_seconds?: number | null;
  token_count_in?: number | null;
  token_count_out?: number | null;
  success: boolean;
  error_type?: string | null;
  timestamp: string;
}

export interface LLMIntelligenceReport {
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  average_response_time: number;
  slowest_request_time: number;
  records: LLMRequestRecord[];
}

export interface ToolExecutionRecord {
  id: string;
  project_id: string;
  tool_name: string;
  calling_agent: string;
  task_id?: string | null;
  duration_ms?: number | null;
  status: string;
  command?: string[] | string | null;
  exit_code?: number | null;
  message: string;
  timestamp: string;
}

export interface IncidentRecord {
  id: string;
  project_id: string;
  task_id?: string | null;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: string;
  affected_files: string[];
  created_at: string;
}

// ---------------------------------------------------------------------------
// Terminal & Execution Center Types
// ---------------------------------------------------------------------------

export interface TerminalSession {
  id: string;
  project_id: string;
  name: string;
  shell_type: 'powershell' | 'cmd' | 'bash' | 'docker';
  working_directory: string;
  created_by: string;
  status: 'active' | 'closed' | 'error';
  created_at: string;
  closed_at?: string | null;
  running_command?: string | null;
  active_pid?: number | null;
  exit_code?: number | null;
}

export interface TerminalCommand {
  id: string;
  session_id: string;
  project_id: string;
  agent_id?: string | null;
  task_id?: string | null;
  run_id?: string | null;
  trace_id?: string | null;
  command: string;
  working_directory: string;
  process_id?: number | null;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  exit_code?: number | null;
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'timed_out';
  stdout_preview?: string | null;
  stderr_preview?: string | null;
}

export interface TerminalProcess {
  process_id: number;
  session_id: string;
  project_id: string;
  command: string;
  started_by: string;
  agent_name?: string | null;
  started_at: string;
  duration_seconds: number;
  status: 'running' | 'completed' | 'failed' | 'cancelled' | 'timed_out' | 'terminating';
  cpu_percent?: number | null;
  memory_mb?: number | null;
}

export interface TerminalEventItem {
  type: 'stdout' | 'stderr' | 'status' | 'system' | 'error' | 'ping';
  data: string;
  sequence: number;
  timestamp?: string | null;
}

export interface TerminalSecurityStatus {
  docker: {
    available: boolean;
    reason: string;
    isolation_mode: 'docker_container' | 'subprocess_sandbox';
  };
  powershell_available: boolean;
  supported_shells: string[];
  isolation_tier: string;
}







// ─── Free Developer Services Integrations ────────────────────────────────────

export type IntegrationCategory =
  | 'vcs'
  | 'ci_cd'
  | 'security'
  | 'observability'
  | 'error_tracking'
  | 'monitoring'
  | 'deployment'
  | 'storage'
  | 'auth';

export type ProviderStatus =
  | 'connected'
  | 'disconnected'
  | 'not_configured'
  | 'disabled'
  | 'error';

export interface ProviderUsage {
  quota_used: number;
  quota_total?: number | null;
  quota_unit: string;
  percentage?: number | null;
  resets_at?: string | null;
  description?: string | null;
}

export interface IntegrationStatusResponse {
  provider_id: string;
  name: string;
  category: IntegrationCategory;
  description: string;
  free_tier_info: string;
  is_enabled: boolean;
  status: ProviderStatus;
  message: string;
  latency_ms?: number | null;
  last_checked: string;
  usage?: ProviderUsage | null;
  features: string[];
  has_credentials: boolean;
}

export interface IntegrationTestResult {
  success: boolean;
  status: ProviderStatus;
  message: string;
  latency_ms?: number | null;
  details?: Record<string, any>;
}

export interface GitHubRepoSummary {
  name: string;
  full_name: string;
  owner: string;
  description?: string | null;
  private: boolean;
  default_branch: string;
  html_url: string;
  stars_count: number;
  forks_count: number;
  open_issues_count: number;
}

export interface GitHubPullRequest {
  number: number;
  title: string;
  body?: string | null;
  state: string;
  html_url: string;
  head_branch: string;
  base_branch: string;
  author: string;
  created_at: string;
  updated_at?: string | null;
  merged: boolean;
  mergeable?: boolean | null;
  draft: boolean;
}

export interface SecurityAuditResult {
  project_id: string;
  passed: boolean;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  reports: any[];
  findings: any[];
}
