import React from 'react';
import { CheckCircle2, Clock, Play } from 'lucide-react';
import type { ProjectStatus } from '../../types';

interface WorkflowTimelineProps {
  currentStatus: ProjectStatus;
  onSelectStage?: (stageCategory: string) => void;
}

export const WorkflowTimeline: React.FC<WorkflowTimelineProps> = ({
  currentStatus,
  onSelectStage,
}) => {
  const stages = [
    {
      id: 'requirements',
      name: 'Requirements Analysis',
      agent: 'Requirements Analyst',
      category: 'agent_lifecycle',
      statuses: ['requirements_review', 'requirements_approved', 'requirements_revision'],
    },
    {
      id: 'architecture',
      name: 'Architecture Design',
      agent: 'System Architect',
      category: 'agent_lifecycle',
      statuses: ['architecture_review', 'architecture_approved', 'architecture_revision'],
    },
    {
      id: 'planning',
      name: 'Task Decomposition',
      agent: 'Task Planner',
      category: 'workflow_transition',
      statuses: ['planning'],
    },
    {
      id: 'implementation',
      name: 'Code Development',
      agent: 'Software Developer',
      category: 'tool_execution',
      statuses: ['implementing', 'in_progress', 'active', 'repair'],
    },
    {
      id: 'qa',
      name: 'QA & Automated Testing',
      agent: 'QA Engineer',
      category: 'test_execution',
      statuses: ['qa_review'],
    },
    {
      id: 'security',
      name: 'Security Audit',
      agent: 'Security Engineer',
      category: 'security_scan',
      statuses: ['security_review'],
    },
    {
      id: 'review',
      name: 'Code Review & Approval',
      agent: 'Code Reviewer',
      category: 'workflow_transition',
      statuses: ['code_review', 'completed'],
    },
  ];

  const getStageState = (stageStatuses: string[]) => {
    if (currentStatus === 'completed') return 'completed';
    if (stageStatuses.includes(currentStatus)) return 'active';
    // If currentStatus is ahead in the sequence
    const allKnown = stages.flatMap((s) => s.statuses);
    const currIdx = allKnown.indexOf(currentStatus);
    const stageFirstIdx = allKnown.indexOf(stageStatuses[0]);

    if (currIdx > stageFirstIdx) return 'completed';
    return 'pending';
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-1 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            Workflow Execution Lifecycle & Stages
          </h2>
          <p className="text-xs text-slate-400 m-0">
            Interactive multi-agent pipeline stages. Click any stage to filter related events.
          </p>
        </div>
      </div>

      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
          {stages.map((stage, idx) => {
            const state = getStageState(stage.statuses);

            return (
              <div
                key={stage.id}
                onClick={() => onSelectStage?.(stage.category)}
                className={`p-3 rounded-xl border flex flex-col justify-between cursor-pointer transition select-none ${
                  state === 'active'
                    ? 'bg-cyan-950/40 border-cyan-500 shadow-[0_0_12px_rgba(34,211,238,0.2)]'
                    : state === 'completed'
                    ? 'bg-slate-900 border-emerald-900/60 hover:border-emerald-700'
                    : 'bg-slate-950 border-slate-800 opacity-60 hover:opacity-100'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-2">
                    <span className="text-[10px] font-mono font-bold text-slate-500">
                      STEP {idx + 1}
                    </span>
                    {state === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                    {state === 'active' && <Play className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />}
                  </div>

                  <h3 className="text-xs font-bold text-white m-0 leading-tight">
                    {stage.name}
                  </h3>
                  <span className="text-[10px] font-mono text-purple-300 block mt-1">
                    {stage.agent}
                  </span>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                  <span
                    className={`font-bold uppercase ${
                      state === 'active'
                        ? 'text-cyan-400'
                        : state === 'completed'
                        ? 'text-emerald-400'
                        : 'text-slate-500'
                    }`}
                  >
                    {state}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

