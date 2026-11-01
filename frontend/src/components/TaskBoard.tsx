import React from 'react';
import { GitBranch, CheckCircle2 } from 'lucide-react';
import type { Task } from '../types';

interface TaskBoardProps {
  tasks: Task[];
}

export const TaskBoard: React.FC<TaskBoardProps> = ({ tasks }) => {
  const columns: Array<{
    key: string;
    label: string;
    filter: (t: Task) => boolean;
    color: string;
  }> = [
    {
      key: 'pending',
      label: 'To Do / Pending',
      filter: (t) => t.status === 'pending',
      color: 'border-slate-700 bg-slate-800/40 text-slate-300',
    },
    {
      key: 'in_progress',
      label: 'In Progress',
      filter: (t) => t.status === 'in_progress',
      color: 'border-indigo-500/30 bg-indigo-500/5 text-indigo-300',
    },
    {
      key: 'completed',
      label: 'Completed & Verified',
      filter: (t) => t.status === 'completed',
      color: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300',
    },
    {
      key: 'blocked',
      label: 'Blocked / Needs Repair',
      filter: (t) => ['failed', 'blocked'].includes(t.status),
      color: 'border-rose-500/30 bg-rose-500/5 text-rose-300',
    },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 m-0">
            Task Decomposition Board
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          Total Tasks: <strong className="text-white">{tasks.length}</strong>
        </span>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-8 border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
          No tasks planned yet. The Task Planner agent generates tasks after architecture approval.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {columns.map((col) => {
            const colTasks = tasks.filter(col.filter);

            return (
              <div key={col.key} className="flex flex-col gap-2">
                <div className="flex items-center justify-between px-2 py-1 bg-slate-800/60 rounded-lg text-xs font-medium text-slate-300">
                  <span>{col.label}</span>
                  <span className="px-1.5 py-0.2 rounded-full bg-slate-700 font-mono text-[11px]">
                    {colTasks.length}
                  </span>
                </div>

                <div className="space-y-2 min-h-[140px]">
                  {colTasks.map((t) => (
                    <div
                      key={t.id}
                      className="p-3 rounded-lg border border-slate-800 bg-slate-800/60 hover:border-slate-700 transition space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="font-medium text-xs text-white leading-tight">
                          {t.title}
                        </span>
                        <span
                          className={`text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded ${
                            t.priority === 'critical'
                              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                              : t.priority === 'high'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-slate-700 text-slate-400'
                          }`}
                        >
                          {t.priority}
                        </span>
                      </div>

                      {t.description && (
                        <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed m-0">
                          {t.description}
                        </p>
                      )}

                      {t.acceptance_criteria && (
                        <div className="text-[10px] text-emerald-400 bg-emerald-500/5 px-2 py-1 rounded border border-emerald-500/10 flex items-start gap-1">
                          <CheckCircle2 className="w-3 h-3 shrink-0 mt-0.5" />
                          <span className="line-clamp-2">{t.acceptance_criteria}</span>
                        </div>
                      )}

                      <div className="flex items-center justify-between pt-1 border-t border-slate-800 text-[10px] text-slate-500 font-mono">
                        <span>Agent: {t.assigned_agent_id || 'software-developer'}</span>
                        {t.estimated_hours && <span>~{t.estimated_hours}h</span>}
                      </div>
                    </div>
                  ))}
                  {colTasks.length === 0 && (
                    <div className="h-full flex items-center justify-center p-4 border border-dashed border-slate-800/60 rounded-lg text-[11px] text-slate-600">
                      Empty
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
