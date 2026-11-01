import React from 'react';
import { UserCheck, Layers, GitBranch, Code, Shield, CheckSquare, Eye, Bot, Activity } from 'lucide-react';
import type { AgentRun } from '../types';

interface AgentRosterProps {
  runs: AgentRun[];
}

interface AgentProfile {
  id: string;
  name: string;
  role: string;
  icon: React.ElementType;
  color: string;
  description: string;
}

const AGENTS: AgentProfile[] = [
  {
    id: 'requirements-analyst',
    name: 'Requirements Analyst',
    role: 'Product & Scope',
    icon: UserCheck,
    color: 'from-blue-500 to-cyan-500',
    description: 'Extracts functional, non-functional requirements and user stories',
  },
  {
    id: 'system-architect',
    name: 'System Architect',
    role: 'System Design',
    icon: Layers,
    color: 'from-purple-500 to-indigo-500',
    description: 'Designs interfaces, database schema, boundaries and contracts',
  },
  {
    id: 'task-planner',
    name: 'Task Planner',
    role: 'Work Decomposition',
    icon: GitBranch,
    color: 'from-amber-500 to-orange-500',
    description: 'Breaks architecture into atomic tasks with dependencies',
  },
  {
    id: 'software-developer',
    name: 'Software Developer',
    role: 'Implementation',
    icon: Code,
    color: 'from-emerald-500 to-teal-500',
    description: 'Writes modular production code and unit test fixtures',
  },
  {
    id: 'qa-engineer',
    name: 'QA & Test Engineer',
    role: 'Verification & E2E',
    icon: CheckSquare,
    color: 'from-rose-500 to-pink-500',
    description: 'Performs automated test verification and bug repro reports',
  },
  {
    id: 'security-engineer',
    name: 'Security Engineer',
    role: 'AppSec & Hardening',
    icon: Shield,
    color: 'from-red-500 to-rose-600',
    description: 'Audits secrets, OWASP risks, injections and access control',
  },
  {
    id: 'code-reviewer',
    name: 'Code Reviewer',
    role: 'Quality & Governance',
    icon: Eye,
    color: 'from-violet-500 to-purple-600',
    description: 'Independent review of code standards, style and acceptance criteria',
  },
];

export const AgentRoster: React.FC<AgentRosterProps> = ({ runs }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 m-0">
            Specialized Agent Team
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          Total Invocations: <strong className="text-white">{runs.length}</strong>
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {AGENTS.map((agent) => {
          const Icon = agent.icon;
          const agentRuns = runs.filter((r) => r.agent_definition_id === agent.id);
          const latestRun = agentRuns[0];
          const totalTokens = agentRuns.reduce((sum, r) => sum + (r.total_tokens || 0), 0);

          let statusBadge = (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              Idle
            </span>
          );

          if (latestRun?.status === 'running') {
            statusBadge = (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center gap-1 animate-pulse">
                <Activity className="w-2.5 h-2.5" /> Working
              </span>
            );
          } else if (latestRun?.status === 'success') {
            statusBadge = (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Done ({agentRuns.length})
              </span>
            );
          } else if (latestRun?.status === 'failure' || latestRun?.status === 'error') {
            statusBadge = (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
                Failed
              </span>
            );
          }

          return (
            <div
              key={agent.id}
              className="bg-slate-800/40 border border-slate-800 hover:border-slate-700/80 rounded-lg p-3 flex flex-col justify-between transition"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${agent.color} flex items-center justify-center text-white shadow-sm`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  {statusBadge}
                </div>
                <h4 className="text-xs font-semibold text-white m-0 leading-tight">{agent.name}</h4>
                <p className="text-[11px] text-indigo-400 font-mono m-0 mb-1">{agent.role}</p>
                <p className="text-[11px] text-slate-400 line-clamp-2 m-0 leading-tight">
                  {agent.description}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>Runs: {agentRuns.length}</span>
                <span>{totalTokens > 0 ? `${totalTokens.toLocaleString()} tok` : '0 tok'}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

