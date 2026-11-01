import React from 'react';
import { Play, Check, FastForward } from 'lucide-react';
import type { Project } from '../types';

interface WorkflowControlsProps {
  project: Project | null;
  onStart: () => Promise<void>;
  onResume: () => Promise<void>;
  onApproveRequirements: (comments?: string) => Promise<void>;
  onApproveArchitecture: (comments?: string) => Promise<void>;
  loading: boolean;
}

export const WorkflowControls: React.FC<WorkflowControlsProps> = ({
  project,
  onStart,
  onResume,
  onApproveRequirements,
  onApproveArchitecture,
  loading,
}) => {
  if (!project) return null;

  const isPending = project.status === 'pending';
  const isReqReview = project.status === 'requirements_review';
  const isArchReview = project.status === 'architecture_review';
  const isReqApproved = project.status === 'requirements_approved';
  const isArchApproved = project.status === 'architecture_approved';
  const isTerminal = ['completed', 'failed', 'cancelled'].includes(project.status);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
      <div>
        <h4 className="text-sm font-semibold text-white m-0">Workflow Orchestrator</h4>
        <p className="text-xs text-slate-400 m-0">
          {isPending && 'Project ready. Click "Start Workflow" to launch Requirements Analyst.'}
          {isReqReview && 'Human gate reached: Review requirements.md before proceeding.'}
          {isReqApproved && 'Requirements approved! Resume workflow to trigger System Architect.'}
          {isArchReview && 'Human gate reached: Review architecture.md and schema before planning.'}
          {isArchApproved && 'Architecture approved! Resume workflow to run task decomposition & coding.'}
          {isTerminal && `Project is currently in terminal state: ${project.status}`}
          {!isPending && !isReqReview && !isReqApproved && !isArchReview && !isArchApproved && !isTerminal &&
            'Multi-agent pipeline running autonomously in background...'}
        </p>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {/* Start workflow */}
        {isPending && (
          <button
            onClick={onStart}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow-md shadow-emerald-600/20 disabled:opacity-50 active:scale-95 cursor-pointer"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>Start Workflow</span>
          </button>
        )}

        {/* Requirements Gate Approval */}
        {isReqReview && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onApproveRequirements()}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow-md shadow-emerald-600/20 disabled:opacity-50 active:scale-95 cursor-pointer"
            >
              <Check className="w-4 h-4" />
              <span>Approve Requirements Gate</span>
            </button>
          </div>
        )}

        {/* Architecture Gate Approval */}
        {isArchReview && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onApproveArchitecture()}
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow-md shadow-emerald-600/20 disabled:opacity-50 active:scale-95 cursor-pointer"
            >
              <Check className="w-4 h-4" />
              <span>Approve Architecture Gate</span>
            </button>
          </div>
        )}

        {/* Resume after approval */}
        {(isReqApproved || isArchApproved) && (
          <button
            onClick={onResume}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition shadow-md shadow-indigo-600/20 disabled:opacity-50 active:scale-95 cursor-pointer"
          >
            <FastForward className="w-4 h-4" />
            <span>Resume Workflow</span>
          </button>
        )}
      </div>
    </div>
  );
};
