import React, { useState } from 'react';
import { Cpu, CheckCircle2, AlertCircle, RefreshCw, X } from 'lucide-react';
import type { LLMIntelligenceReport, LLMRequestRecord } from '../../types';

interface LLMMonitorPanelProps {
  report: LLMIntelligenceReport | null;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const LLMMonitorPanel: React.FC<LLMMonitorPanelProps> = ({
  report,
  onRefresh,
  isLoading,
}) => {
  const [selectedRequest, setSelectedRequest] = useState<LLMRequestRecord | null>(null);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-400" />
            LLM Intelligence & Inference Telemetry
          </h2>
          <p className="text-xs text-slate-400 m-0">
            Real-time tracking of local Ollama model requests, latency distribution, and token generation.
          </p>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:bg-slate-800 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-purple-400' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
        )}
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {/* Total Inferences */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Total Requests</span>
          <div className="text-xl font-bold font-mono text-white mt-1">
            {report?.total_requests ?? 0}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Inference invocations</span>
        </div>

        {/* Successful */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">Successful</span>
          <div className="text-xl font-bold font-mono text-emerald-300 mt-1">
            {report?.successful_requests ?? 0}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Completed parses</span>
        </div>

        {/* Failed */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] font-mono text-rose-400 uppercase tracking-wider">Failed / Timeouts</span>
          <div className="text-xl font-bold font-mono text-rose-300 mt-1">
            {report?.failed_requests ?? 0}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Errors or aborted</span>
        </div>

        {/* Average Latency */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider">Average Latency</span>
          <div className="text-xl font-bold font-mono text-cyan-300 mt-1">
            {report?.average_response_time ?? 0}s
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Mean turnaround</span>
        </div>

        {/* Slowest Latency */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5">
          <span className="text-[10px] font-mono text-amber-400 uppercase tracking-wider">Peak Latency</span>
          <div className="text-xl font-bold font-mono text-amber-300 mt-1">
            {report?.slowest_request_time ?? 0}s
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Max duration</span>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="px-4 py-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono m-0">
            Recent Model Inferences
          </h3>
          <span className="text-[11px] font-mono text-slate-400">
            {report?.records.length ?? 0} records logged
          </span>
        </div>

        <div className="overflow-x-auto max-h-[380px]">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/40 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800 sticky top-0">
              <tr>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Agent</th>
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Latency</th>
                <th className="py-2.5 px-3">Tokens (In / Out)</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {!report || report.records.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-10 text-slate-500">
                    No LLM inference records logged yet.
                  </td>
                </tr>
              ) : (
                report.records.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => setSelectedRequest(r)}
                    className="hover:bg-slate-800/50 cursor-pointer transition"
                  >
                    <td className="py-2 px-3 text-slate-400">
                      {new Date(r.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-2 px-3 text-purple-300 font-medium">
                      {r.agent_role.toUpperCase()}
                    </td>
                    <td className="py-2 px-3 text-slate-300">{r.model_name}</td>
                    <td className="py-2 px-3 text-cyan-400 font-bold">
                      {r.duration_seconds !== null && r.duration_seconds !== undefined
                        ? `${r.duration_seconds.toFixed(2)}s`
                        : '—'}
                    </td>
                    <td className="py-2 px-3 text-slate-300">
                      {r.token_count_in ?? 0} / {r.token_count_out ?? 0}
                    </td>
                    <td className="py-2 px-3">
                      {r.success ? (
                        <span className="inline-flex items-center gap-1 text-emerald-400 font-bold text-[10px] px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-900/60">
                          <CheckCircle2 className="w-3 h-3" /> SUCCESS
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-400 font-bold text-[10px] px-2 py-0.5 rounded bg-rose-950/40 border border-rose-900/60">
                          <AlertCircle className="w-3 h-3" /> FAILED
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Request Detail Modal */}
      {selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-5 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="font-bold text-white text-sm m-0">Inference Request Inspector</h3>
              <button
                onClick={() => setSelectedRequest(null)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-500">Model:</span>
                <span className="text-purple-300 font-bold">{selectedRequest.model_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Agent Role:</span>
                <span className="text-white">{selectedRequest.agent_role}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Duration:</span>
                <span className="text-cyan-400 font-bold">{selectedRequest.duration_seconds}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Tokens In / Out:</span>
                <span>{selectedRequest.token_count_in} / {selectedRequest.token_count_out}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Status:</span>
                <span className={selectedRequest.success ? 'text-emerald-400' : 'text-rose-400'}>
                  {selectedRequest.success ? 'SUCCESS' : `FAILED (${selectedRequest.error_type || 'Unknown'})`}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

