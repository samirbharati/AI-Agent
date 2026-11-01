import React from 'react';
import { Search, X, Download, RotateCcw } from 'lucide-react';
import type { Project } from '../../types';

export interface FilterState {
  severity: string;
  source: string;
  category: string;
  project_id: string;
  time_range: string;
  status: string;
  search: string;
}

interface LogFilterPanelProps {
  filters: FilterState;
  onChange: (newFilters: FilterState) => void;
  onClear: () => void;
  onExport: () => void;
  projects: Project[];
}

export const LogFilterPanel: React.FC<LogFilterPanelProps> = ({
  filters,
  onChange,
  onClear,
  onExport,
  projects,
}) => {
  const update = (key: keyof FilterState, val: string) => {
    onChange({ ...filters, [key]: val });
  };

  const hasActiveFilters =
    filters.severity !== 'all' ||
    filters.source !== 'all' ||
    filters.category !== 'all' ||
    filters.project_id !== 'all' ||
    filters.time_range !== 'all' ||
    filters.status !== 'all' ||
    filters.search.trim() !== '';

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm space-y-3">
      {/* Top: Search bar & Export CTA */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Full-text search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => update('search', e.target.value)}
            placeholder="Search logs by message, task ID, trace ID, tool name, or error..."
            className="w-full bg-slate-950 border border-slate-700/80 rounded-lg pl-9 pr-9 py-1.5 text-xs text-white placeholder-slate-500 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500 transition"
          />
          {filters.search && (
            <button
              onClick={() => update('search', '')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          {hasActiveFilters && (
            <button
              onClick={onClear}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium transition"
              title="Reset all filters"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          )}

          <button
            onClick={onExport}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-cyan-600/90 hover:bg-cyan-500 text-xs text-white font-medium shadow-md shadow-cyan-600/20 transition active:scale-95"
            title="Export filtered logs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Logs</span>
          </button>
        </div>
      </div>

      {/* Filter Dropdown Matrix */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
        {/* Log Level */}
        <div>
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
            Log Level
          </label>
          <select
            value={filters.severity}
            onChange={(e) => update('severity', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Levels</option>
            <option value="debug">DEBUG</option>
            <option value="info">INFO</option>
            <option value="success">SUCCESS</option>
            <option value="warning">WARNING</option>
            <option value="error">ERROR</option>
            <option value="critical">CRITICAL</option>
          </select>
        </div>

        {/* Agent */}
        <div>
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
            Agent
          </label>
          <select
            value={filters.source}
            onChange={(e) => update('source', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Agents</option>
            <option value="orchestrator">Orchestrator</option>
            <option value="requirements-analyst">Requirements Analyst</option>
            <option value="system-architect">System Architect</option>
            <option value="task-planner">Task Planner</option>
            <option value="software-developer">Software Developer</option>
            <option value="qa-engineer">QA Engineer</option>
            <option value="security-engineer">Security Engineer</option>
            <option value="code-reviewer">Code Reviewer</option>
            <option value="system">System Core</option>
          </select>
        </div>

        {/* Category */}
        <div>
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
            Category
          </label>
          <select
            value={filters.category}
            onChange={(e) => update('category', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Categories</option>
            <option value="agent_lifecycle">Agent Lifecycle</option>
            <option value="llm_request">LLM Requests</option>
            <option value="tool_execution">Tool Execution</option>
            <option value="file_operation">File Operations</option>
            <option value="git_operation">Git Operations</option>
            <option value="test_execution">Test Execution</option>
            <option value="bug_detection">Bug Detection</option>
            <option value="security_scan">Security Scanning</option>
            <option value="workflow_transition">Workflow Stages</option>
            <option value="system">System Events</option>
          </select>
        </div>

        {/* Project Scope */}
        <div>
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
            Project Scope
          </label>
          <select
            value={filters.project_id}
            onChange={(e) => update('project_id', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500 truncate"
          >
            <option value="all">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Time Range */}
        <div>
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
            Time Range
          </label>
          <select
            value={filters.time_range}
            onChange={(e) => update('time_range', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Time</option>
            <option value="5m">Last 5 minutes</option>
            <option value="15m">Last 15 minutes</option>
            <option value="1h">Last 1 hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
          </select>
        </div>

        {/* Status */}
        <div>
          <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
            Status
          </label>
          <select
            value={filters.status}
            onChange={(e) => update('status', e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1 text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Statuses</option>
            <option value="success">Success</option>
            <option value="running">Running</option>
            <option value="failure">Failed</option>
            <option value="blocked">Blocked</option>
            <option value="warning">Warning</option>
          </select>
        </div>
      </div>
    </div>
  );
};

