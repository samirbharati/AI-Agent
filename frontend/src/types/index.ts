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




