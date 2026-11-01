import React from 'react';
import { CheckCircle2, Circle, Clock, AlertTriangle, ShieldCheck, FileCode, Layers, GitBranch } from 'lucide-react';
import type { ProjectStatus } from '../types';

interface StageProgressProps {
  status: ProjectStatus;
}

interface Stage {
  key: string;
  label: string;
  icon: React.ElementType;
  description: string;
}

const STAGES: Stage[] = [
  { key: 'requirements', label: 'Requirements', icon: FileCode, description: 'Analysis & user stories' },
  { key: 'gate_1', label: 'Human Gate 1', icon: ShieldCheck, description: 'Requirements sign-off' },
  { key: 'architecture', label: 'Architecture', icon: Layers, description: 'System design & schema' },
  { key: 'gate_2', label: 'Human Gate 2', icon: ShieldCheck, description: 'Architecture sign-off' },
  { key: 'planning', label: 'Task Planning', icon: GitBranch, description: 'Decomposition & deps' },
  { key: 'implementation', label: 'Development & QA', icon: CheckCircle2, description: 'Dev ↔ QA ↔ Security loop' },
];

export const StageProgress: React.FC<StageProgressProps> = ({ status }) => {
  const getStageState = (index: number): 'completed' | 'current' | 'pending' | 'gate' => {
    switch (status) {
      case 'pending':
        return index === 0 ? 'current' : 'pending';

      case 'requirements_review':
        if (index === 0) return 'completed';
        if (index === 1) return 'gate';
        return 'pending';

      case 'requirements_approved':
        if (index <= 1) return 'completed';
        if (index === 2) return 'current';
        return 'pending';

      case 'architecture_review':
        if (index <= 2) return 'completed';
        if (index === 3) return 'gate';
        return 'pending';

      case 'architecture_approved':
      case 'planning':
        if (index <= 3) return 'completed';
        if (index === 4) return 'current';
        return 'pending';

      case 'in_progress':
      case 'active':
      case 'implementing':
      case 'qa_review':
      case 'security_review':
      case 'code_review':
      case 'repair':
        if (index <= 4) return 'completed';
        if (index === 5) return 'current';
        return 'pending';

      case 'completed':
        return 'completed';

      case 'failed':
      case 'cancelled':
        return 'pending';

      default:
        return 'pending';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 m-0">
          Workflow Pipeline Stages
        </h3>
        <span className="text-xs px-2.5 py-0.5 rounded-full font-mono capitalize bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          {status.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        {STAGES.map((stage, idx) => {
          const state = getStageState(idx);
          const Icon = stage.icon;

          return (
            <div
              key={stage.key}
              className={`p-3 rounded-lg border flex flex-col justify-between transition-all ${
                state === 'completed'
                  ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-300'
                  : state === 'current'
                  ? 'bg-indigo-500/10 border-indigo-500/40 text-indigo-300 shadow-md shadow-indigo-500/5'
                  : state === 'gate'
                  ? 'bg-amber-500/10 border-amber-500/40 text-amber-300 animate-pulse'
                  : 'bg-slate-800/40 border-slate-800 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className="w-4 h-4" />
                {state === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                {state === 'current' && <Clock className="w-3.5 h-3.5 text-indigo-400 animate-spin" />}
                {state === 'gate' && <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />}
                {state === 'pending' && <Circle className="w-3.5 h-3.5 text-slate-600" />}
              </div>
              <div>
                <p className="text-xs font-semibold leading-tight text-white m-0 mb-0.5">{stage.label}</p>
                <p className="text-[11px] text-slate-400 leading-tight m-0">{stage.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
