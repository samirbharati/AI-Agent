import React from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCw,
  BarChart3,
  Zap,
  Lock,
} from 'lucide-react';
import type { QualityGateResult, QualityCertificationReport } from '../../types';

interface QualityOverviewProps {
  report: QualityCertificationReport | null;
  gates: QualityGateResult[];
  isRunning: boolean;
  onRunAudit: () => void;
}

export const QualityOverviewPanel: React.FC<QualityOverviewProps> = ({
  report,
  gates,
  isRunning,
  onRunAudit,
}) => {
  const overallStatus = report?.overall_status || 'NOT_VERIFIED';
  const score = report?.quality_score ?? 0;

  const passedGates = gates.filter((g) => g.status === 'passed').length;
  const blockedGates = gates.filter((g) => g.status === 'blocked').length;
  const failedGates = gates.filter((g) => g.status === 'failed').length;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return (
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold text-sm tracking-wide">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>RELEASE APPROVED</span>
          </div>
        );
      case 'CONDITIONALLY_APPROVED':
        return (
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 font-bold text-sm tracking-wide">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>CONDITIONALLY APPROVED</span>
          </div>
        );
      case 'BLOCKED':
        return (
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 font-bold text-sm tracking-wide">
            <XCircle className="w-4 h-4 text-rose-400" />
            <span>RELEASE BLOCKED</span>
          </div>
        );
      default:
        return (
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-slate-400 font-medium text-sm tracking-wide">
            <ShieldAlert className="w-4 h-4 text-slate-400" />
            <span>NOT VERIFIED</span>
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Audit Trigger */}
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-white tracking-tight">
                Product Quality & Reliability Engineering
              </h2>
              {getStatusBadge(overallStatus)}
            </div>
            <p className="text-sm text-slate-400">
              Strict 10-gate evidence verification: Build, Unit, Integration, API, Security, Performance, Concurrency, Regression, Architecture, and Sign-off.
            </p>
          </div>

          <button
            onClick={onRunAudit}
            disabled={isRunning}
            className={`flex items-center gap-2.5 px-6 py-3 rounded-xl font-bold text-sm transition shadow-lg ${
              isRunning
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/25 active:scale-95'
            }`}
          >
            {isRunning ? (
              <>
                <RotateCw className="w-4 h-4 animate-spin text-emerald-400" />
                <span>Validating Quality Gates...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Run Quality Audit</span>
              </>
            )}
          </button>
        </div>

        {/* High-Level Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#1E293B]">
          <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
              <span>Quality Score</span>
              <BarChart3 className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-cyan-400">
              {score}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </div>
          </div>

          <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
              <span>Gates Cleared</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-400">
              {passedGates}
              <span className="text-xs text-slate-500 font-normal"> / 10</span>
            </div>
          </div>

          <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
              <span>P95 Latency</span>
              <Zap className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-amber-400">
              {report?.performance_metrics?.p95_latency_ms ?? 0}
              <span className="text-xs text-slate-500 font-normal"> ms</span>
            </div>
          </div>

          <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs uppercase font-medium mb-1">
              <span>Critical Deficits</span>
              <Lock className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-rose-400">
              {(report?.open_critical_bugs ?? 0) + (report?.security_summary?.critical_count ?? 0)}
              <span className="text-xs text-slate-500 font-normal"> blockers</span>
            </div>
          </div>
        </div>
      </div>

      {/* 10 Evidence-Based Quality Gates Grid */}
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-white">10 Evidence-Based Quality Gates</h3>
            <p className="text-xs text-slate-400">Every gate requires concrete execution logs and strict criterion satisfaction.</p>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-emerald-400 font-bold">{passedGates} Passed</span>
            <span className="text-slate-600">|</span>
            <span className="text-amber-400 font-bold">{blockedGates} Blocked</span>
            <span className="text-slate-600">|</span>
            <span className="text-rose-400 font-bold">{failedGates} Failed</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {gates.map((g) => {
            const isPass = g.status === 'passed';
            const isBlock = g.status === 'blocked';
            const isFail = g.status === 'failed';

            return (
              <div
                key={g.gate_number}
                className="bg-[#111827]/70 border border-[#1F2937] hover:border-slate-700 transition p-4 rounded-xl flex items-start justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-md bg-slate-800 text-slate-300 font-mono text-xs flex items-center justify-center font-bold">
                      {g.gate_number}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-200 truncate">{g.gate_name}</h4>
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-1">{g.criterion}</p>
                  <div className="font-mono text-xs text-cyan-400 truncate bg-slate-900/60 px-2 py-1 rounded border border-slate-800/80">
                    {g.evaluated_value || 'Pending evaluation'}
                  </div>
                </div>

                <div>
                  {isPass && (
                    <span className="px-2.5 py-1 rounded text-[11px] font-bold font-mono bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                      PASSED
                    </span>
                  )}
                  {isBlock && (
                    <span className="px-2.5 py-1 rounded text-[11px] font-bold font-mono bg-amber-500/10 border border-amber-500/20 text-amber-400">
                      BLOCKED
                    </span>
                  )}
                  {isFail && (
                    <span className="px-2.5 py-1 rounded text-[11px] font-bold font-mono bg-rose-500/10 border border-rose-500/20 text-rose-400">
                      FAILED
                    </span>
                  )}
                  {!isPass && !isBlock && !isFail && (
                    <span className="px-2.5 py-1 rounded text-[11px] font-bold font-mono bg-slate-800 text-slate-500">
                      PENDING
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
