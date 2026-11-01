import React from 'react';
import { ShieldCheck, Lock } from 'lucide-react';
import type { SecurityFinding } from '../../types';

interface SecurityEventPanelProps {
  findings: SecurityFinding[];
}

export const SecurityEventPanel: React.FC<SecurityEventPanelProps> = ({ findings }) => {
  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/40 animate-pulse';
      case 'high':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'medium':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Security Event & Vulnerability Monitor
          </h2>
          <p className="text-xs text-slate-400 m-0">
            Deterministic AST scans, OWASP Top 10 rule matching, and secret leak detection.
          </p>
        </div>

        {/* Coverage pill */}
        <div className="flex items-center gap-2 text-[11px] font-mono">
          <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            Engine: <strong className="text-cyan-400">AST/Regex Rules</strong>
          </span>
          <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            Coverage: <strong className="text-emerald-400">Deterministic</strong>
          </span>
        </div>
      </div>

      {/* Findings List */}
      <div className="space-y-3">
        {findings.length === 0 ? (
          <div className="py-12 text-center text-slate-500 bg-slate-900/40 border border-slate-800 rounded-xl space-y-1">
            <ShieldCheck className="w-8 h-8 text-emerald-500/80 mx-auto" />
            <p className="font-mono text-xs text-slate-300 m-0">Zero Vulnerabilities Detected</p>
            <p className="text-[11px] text-slate-500 m-0">
              Workspace complies with deterministic credential security & injection prevention policies.
            </p>
          </div>
        ) : (
          findings.map((f) => (
            <div
              key={f.id}
              className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition space-y-2.5"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    <Lock className="w-4 h-4" />
                  </span>
                  <div>
                    <h3 className="text-xs font-bold text-white m-0 truncate">{f.title}</h3>
                    <span className="text-[10px] font-mono text-slate-400">Rule ID: {f.rule_id}</span>
                  </div>
                </div>

                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border ${getSeverityBadge(
                    f.severity
                  )}`}
                >
                  {f.severity}
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-300 font-mono leading-relaxed m-0">{f.description}</p>

              {/* Evidence Snippet */}
              {f.evidence && (
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-amber-300">
                  <span className="text-[9px] uppercase text-slate-500 block mb-1">Evidence Snippet:</span>
                  <code>{f.evidence}</code>
                </div>
              )}

              {/* Remediation Advice */}
              {f.remediation && (
                <div className="text-[11px] font-mono text-emerald-400 bg-emerald-950/20 p-2 rounded border border-emerald-900/40">
                  <strong className="text-emerald-300">Remediation: </strong>
                  {f.remediation}
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1">
                <span>File: {f.file_path}{f.line_number ? `:${f.line_number}` : ''}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

