import React from 'react';
import { Bug, CheckCircle2 } from 'lucide-react';
import type { IncidentRecord } from '../../types';

interface IncidentMonitorProps {
  incidents: IncidentRecord[];
}

export const IncidentMonitor: React.FC<IncidentMonitorProps> = ({ incidents }) => {
  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse';
      case 'high':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'medium':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/40';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'fixed':
      case 'verified':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-900';
      case 'in_progress':
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-900';
      default:
        return 'text-amber-400 bg-amber-950/40 border-amber-900';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-1 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center gap-2">
            <Bug className="w-4 h-4 text-rose-400" />
            Incident & Bug Intelligence
          </h2>
          <p className="text-xs text-slate-400 m-0">
            Detected software defects, test failures, and closed-loop repair status.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {incidents.length === 0 ? (
          <div className="col-span-2 py-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-xl space-y-1">
            <CheckCircle2 className="w-7 h-7 text-emerald-500/60 mx-auto" />
            <p className="font-mono text-xs text-slate-400 m-0">Zero Open Incidents</p>
            <p className="text-[11px] text-slate-600 m-0">All QA verification tests and runtime checks are passing.</p>
          </div>
        ) : (
          incidents.map((inc) => (
            <div
              key={inc.id}
              className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      <Bug className="w-4 h-4" />
                    </span>
                    <h3 className="text-xs font-bold text-white m-0 truncate">{inc.title}</h3>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0 font-mono text-[10px]">
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold uppercase border ${getSeverityBadge(
                        inc.severity
                      )}`}
                    >
                      {inc.severity}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold uppercase border ${getStatusBadge(
                        inc.status
                      )}`}
                    >
                      {inc.status}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-300 font-mono mt-3 mb-2 leading-relaxed break-words">
                  {inc.description}
                </p>

                {inc.affected_files && inc.affected_files.length > 0 && (
                  <div className="mt-2.5">
                    <span className="text-[10px] font-mono text-slate-500 uppercase block mb-1">
                      Affected Files:
                    </span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {inc.affected_files.map((file, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-300 font-mono text-[10px]"
                        >
                          {file}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span>ID: {inc.id.slice(0, 8)}...</span>
                <span>{new Date(inc.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

