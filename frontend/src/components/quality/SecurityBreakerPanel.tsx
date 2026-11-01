import React from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Lock,
  Key,
  Flame,
  FileCode,
  CheckCircle2,
} from 'lucide-react';
import type { SecurityBreakerSummary } from '../../types';

interface SecurityBreakerPanelProps {
  securitySummary: SecurityBreakerSummary | null;
}

export const SecurityBreakerPanel: React.FC<SecurityBreakerPanelProps> = ({
  securitySummary,
}) => {
  const findings = securitySummary?.findings || [];
  const critCount = securitySummary?.critical_count || 0;
  const highCount = securitySummary?.high_count || 0;
  const medCount = securitySummary?.medium_count || 0;
  const lowCount = securitySummary?.low_count || 0;
  const secretsCount = securitySummary?.exposed_secrets_count || 0;

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-rose-500/20 text-rose-400 border border-rose-500/30">CRITICAL</span>;
      case 'high':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-amber-500/20 text-amber-400 border border-amber-500/30">HIGH</span>;
      case 'medium':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-blue-500/20 text-blue-400 border border-blue-500/30">LOW</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Security Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="bg-[#0D1320] border border-[#1E293B] p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
            <span>Critical</span>
            <Flame className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-500">{critCount}</div>
        </div>

        <div className="bg-[#0D1320] border border-[#1E293B] p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
            <span>High</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-500">{highCount}</div>
        </div>

        <div className="bg-[#0D1320] border border-[#1E293B] p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
            <span>Medium</span>
            <ShieldAlert className="w-4 h-4 text-yellow-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-yellow-500">{medCount}</div>
        </div>

        <div className="bg-[#0D1320] border border-[#1E293B] p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
            <span>Low</span>
            <Lock className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-blue-400">{lowCount}</div>
        </div>

        <div className="bg-[#0D1320] border border-[#1E293B] p-4 rounded-xl">
          <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
            <span>Secrets Found</span>
            <Key className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400">{secretsCount}</div>
        </div>
      </div>

      {/* Findings List */}
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6">
        <h3 className="text-base font-bold text-white mb-4">Adversarial Breaker Audit Findings</h3>

        {findings.length === 0 ? (
          <div className="text-center py-12 text-emerald-400 text-xs font-mono flex flex-col items-center gap-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500" />
            <span>Clean security audit. Zero vulnerabilities or exposed credentials discovered.</span>
          </div>
        ) : (
          <div className="space-y-4">
            {findings.map((f: any, idx: number) => (
              <div
                key={f.id || idx}
                className="bg-[#111827] border border-[#1F2937] p-4 rounded-xl space-y-3"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2.5">
                    {getSeverityBadge(f.severity)}
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {f.vector}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-200">{f.title}</h4>
                  </div>
                  {f.affected_file && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
                      <FileCode className="w-3.5 h-3.5 text-slate-500" />
                      <span>{f.affected_file}</span>
                    </div>
                  )}
                </div>

                <p className="text-xs text-slate-300">{f.description}</p>

                {f.reproduction_steps && (
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-900 font-mono text-xs text-amber-300">
                    <span className="text-slate-500 select-none mr-2">Reproduction:</span>
                    {f.reproduction_steps}
                  </div>
                )}

                {f.remediation && (
                  <div className="text-xs text-emerald-400 font-mono flex items-start gap-1.5">
                    <span className="text-slate-500 select-none">Remediation:</span>
                    <span>{f.remediation}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
