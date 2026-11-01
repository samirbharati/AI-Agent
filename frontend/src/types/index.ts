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


