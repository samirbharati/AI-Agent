import React, { useState } from 'react';
import {
  Users,
  Cpu,
  ChevronDown,
  ChevronUp,
  FileCode,
  ShieldAlert,
  TestTube,
  GitBranch,
} from 'lucide-react';
import type { AgentMonitoringState } from '../../types';

interface AgentActivityGridProps {
  agents: AgentMonitoringState[];
}

export const AgentActivityGrid: React.FC<AgentActivityGridProps> = ({ agents }) => {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'RUNNING':
        return {
          bg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/40',
          dot: 'bg-cyan-400 animate-ping',
          label: 'RUNNING',
        };
      case 'COMPLETED':
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40',
          dot: 'bg-emerald-400',
          label: 'COMPLETED',
        };
      case 'FAILED':
        return {
          bg: 'bg-rose-500/10 text-rose-400 border-rose-500/40',
          dot: 'bg-rose-400',
          label: 'FAILED',
        };
      case 'INITIALIZING':
        return {
          bg: 'bg-purple-500/10 text-purple-400 border-purple-500/40',
          dot: 'bg-purple-400 animate-pulse',
          label: 'INITIALIZING',
        };
      case 'BLOCKED':
        return {
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/40',
          dot: 'bg-amber-400',
          label: 'BLOCKED',
        };
      default:
        return {
          bg: 'bg-slate-800 text-slate-400 border-slate-700',
          dot: 'bg-slate-500',
          label: 'IDLE',
        };
    }
  };

  const getAgentIcon = (id: string) => {
    switch (id) {
      case 'requirements-analyst':
        return <FileCode className="w-4 h-4 text-cyan-400" />;
      case 'system-architect':
        return <Cpu className="w-4 h-4 text-purple-400" />;
      case 'task-planner':
        return <GitBranch className="w-4 h-4 text-indigo-400" />;
      case 'software-developer':
        return <FileCode className="w-4 h-4 text-emerald-400" />;
      case 'qa-engineer':
        return <TestTube className="w-4 h-4 text-blue-400" />;
      case 'security-engineer':
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case 'code-reviewer':
        return <Users className="w-4 h-4 text-purple-300" />;
      default:
        return <Users className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-1 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0">
            Agent Operations & Execution Roster
          </h2>
          <p className="text-xs text-slate-400 m-0">
            Autonomous multi-agent lifecycle telemetry, active tasks, and execution latencies.
          </p>
        </div>
      </div>

      {/* Grid of Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
        {agents.map((agent) => {
          const badge = getStatusBadge(agent.status);
          const isExpanded = expandedAgent === agent.agent_id;

          return (
            <div
              key={agent.agent_id}
              className={`bg-slate-900/90 border rounded-xl p-4 transition flex flex-col justify-between ${
                agent.status === 'RUNNING'
                  ? 'border-cyan-500/50 shadow-[0_0_12px_rgba(34,211,238,0.15)]'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                {/* Header: Icon, Name & Status Badge */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                      {getAgentIcon(agent.agent_id)}
                    </div>
                    <div>
                      <h3 className="text-xs font-bold text-white m-0 leading-tight">
                        {agent.agent_name}
                      </h3>
                      <span className="text-[10px] font-mono text-slate-400 block mt-0.5">
                        {agent.role}
                      </span>
                    </div>
                  </div>

                  {/* Status Pill */}
                  <span
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border uppercase shrink-0 ${badge.bg}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${badge.dot}`} />
                    {badge.label}
                  </span>
                </div>

                {/* Body Metrics */}
                <div className="mt-3.5 space-y-2 text-xs font-mono">
                  {/* Current Task */}
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Task:</span>
                    <span className="text-white font-medium truncate max-w-[150px]">
                      {agent.current_task || 'None (Idle)'}
                    </span>
                  </div>

                  {/* Model */}
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Model:</span>
                    <span className="text-purple-300 font-medium">{agent.model_used}</span>
                  </div>

                  {/* Tasks Summary */}
                  <div className="flex items-center justify-between text-slate-400">
                    <span>Tasks:</span>
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-bold">{agent.completed_tasks} done</span>
                      {agent.failed_tasks > 0 && (
                        <span className="text-rose-400 font-bold">{agent.failed_tasks} failed</span>
                      )}
                    </div>
                  </div>

                  {/* Duration */}
                  {agent.duration_seconds !== null && agent.duration_seconds !== undefined && (
                    <div className="flex items-center justify-between text-slate-400">
                      <span>Last Latency:</span>
                      <span className="text-cyan-400 font-bold">{agent.duration_seconds.toFixed(2)}s</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Expandable summary */}
              {agent.latest_summary && (
                <div className="mt-3 pt-2.5 border-t border-slate-800/80">
                  <button
                    onClick={() => setExpandedAgent(isExpanded ? null : agent.agent_id)}
                    className="w-full flex items-center justify-between text-[11px] text-slate-400 hover:text-white transition"
                  >
                    <span>Latest Output Summary</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {isExpanded && (
                    <p className="mt-2 text-[11px] font-mono text-slate-300 leading-relaxed bg-slate-950 p-2.5 rounded-lg border border-slate-800 m-0 break-words">
                      {agent.latest_summary}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

