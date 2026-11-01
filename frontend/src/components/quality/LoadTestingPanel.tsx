import React, { useState } from 'react';
import {
  Users,
  Play,
  RotateCw,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import type { LoadTestStageResult } from '../../types';

interface LoadTestingPanelProps {
  loadStages: LoadTestStageResult[];
  isRunning: boolean;
  onRunLoadTest: (testPath: string, maxStages: number) => Promise<void>;
}

export const LoadTestingPanel: React.FC<LoadTestingPanelProps> = ({
  loadStages,
  isRunning,
  onRunLoadTest,
}) => {
  const [testPath, setTestPath] = useState('/api/v1/health');
  const [maxStages, setMaxStages] = useState(7);

  const handleStart = async () => {
    await onRunLoadTest(testPath, maxStages);
  };

  return (
    <div className="space-y-6">
      {/* Simulation Controls */}
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-cyan-400" />
              <h3 className="text-lg font-bold text-white tracking-tight">
                Progressive Concurrency Simulator (Up to 1,000 Users)
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Evaluates system degradation through 7 stepped concurrency tiers: 10 → 50 → 100 → 250 → 500 → 750 → 1,000 concurrent requests.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-[#111827] px-3 py-1.5 rounded-lg border border-[#1F2937]">
              <span className="text-xs text-slate-400 font-mono">Endpoint:</span>
              <input
                type="text"
                value={testPath}
                onChange={(e) => setTestPath(e.target.value)}
                className="bg-transparent text-xs font-mono text-cyan-300 focus:outline-none w-36"
                placeholder="/api/v1/health"
              />
            </div>

            <div className="flex items-center gap-2 bg-[#111827] px-3 py-1.5 rounded-lg border border-[#1F2937]">
              <span className="text-xs text-slate-400 font-mono">Tiers:</span>
              <select
                value={maxStages}
                onChange={(e) => setMaxStages(Number(e.target.value))}
                className="bg-transparent text-xs font-mono text-slate-200 focus:outline-none"
              >
                <option value={3} className="bg-slate-900">3 (100 users)</option>
                <option value={5} className="bg-slate-900">5 (500 users)</option>
                <option value={7} className="bg-slate-900">7 (1,000 users)</option>
              </select>
            </div>

            <button
              onClick={handleStart}
              disabled={isRunning}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs transition shadow-lg ${
                isRunning
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-cyan-600/25 active:scale-95'
              }`}
            >
              {isRunning ? (
                <>
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                  <span>Stressing System...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-white" />
                  <span>Run Concurrency Test</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* 7-Stage Progression Bar */}
        <div className="grid grid-cols-7 gap-2">
          {[10, 50, 100, 250, 500, 750, 1000].map((users, idx) => {
            const stageNum = idx + 1;
            const stageData = loadStages.find((s) => s.stage === stageNum);
            const isPassed = stageData?.status === 'passed';
            const isFailed = stageData?.status === 'failed';

            let borderClass = 'border-slate-800 bg-[#111827]/40 text-slate-500';
            if (isPassed) borderClass = 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400';
            if (isFailed) borderClass = 'border-rose-500/40 bg-rose-500/10 text-rose-400';

            return (
              <div
                key={users}
                className={`border p-3 rounded-xl flex flex-col items-center justify-center text-center transition ${borderClass}`}
              >
                <span className="text-[10px] font-mono text-slate-400 uppercase">Stage {stageNum}</span>
                <span className="text-base font-bold font-mono my-0.5">{users}</span>
                <span className="text-[10px] font-mono">users</span>
                {isPassed && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-1" />}
                {isFailed && <XCircle className="w-3.5 h-3.5 text-rose-400 mt-1" />}
                {!isPassed && !isFailed && <div className="w-1.5 h-1.5 rounded-full bg-slate-700 mt-2" />}
              </div>
            );
          })}
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6">
        <h4 className="text-sm font-bold text-white mb-4">Stage Execution Telemetry</h4>

        {loadStages.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-mono">
            No concurrency data available. Run the simulator to stress-test throughput and latency.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-[#1E293B] text-slate-400 uppercase text-[11px]">
                  <th className="pb-3">Stage</th>
                  <th className="pb-3">Concurrency</th>
                  <th className="pb-3">Requests</th>
                  <th className="pb-3">RPS</th>
                  <th className="pb-3">P50</th>
                  <th className="pb-3">P95</th>
                  <th className="pb-3">P99</th>
                  <th className="pb-3">CPU / Mem</th>
                  <th className="pb-3">Status</th>
                  <th className="pb-3">Bottlenecks</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1E293B]/60">
                {loadStages.map((st) => (
                  <tr key={st.id || st.stage} className="hover:bg-[#111827]/40 transition">
                    <td className="py-3 font-bold text-slate-300">Stage {st.stage}</td>
                    <td className="py-3 text-cyan-400 font-bold">{st.target_concurrency} users</td>
                    <td className="py-3 text-slate-300">
                      {st.successful_requests}/{st.total_requests}
                    </td>
                    <td className="py-3 text-emerald-400 font-bold">{st.requests_per_second}</td>
                    <td className="py-3 text-slate-300">{st.p50_latency_ms ?? 0} ms</td>
                    <td className="py-3 text-amber-400 font-bold">{st.p95_latency_ms} ms</td>
                    <td className="py-3 text-rose-400">{st.p99_latency_ms} ms</td>
                    <td className="py-3 text-slate-400">
                      {st.cpu_percent ? `${st.cpu_percent}%` : '--'} / {st.memory_mb ? `${Math.round(st.memory_mb)}MB` : '--'}
                    </td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          st.status === 'passed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}
                      >
                        {st.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-400 max-w-xs truncate">
                      {st.bottlenecks && st.bottlenecks.length > 0
                        ? typeof st.bottlenecks[0] === 'string'
                          ? st.bottlenecks.join(', ')
                          : st.bottlenecks.map((b: any) => b.description).join(', ')
                        : 'None detected'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
