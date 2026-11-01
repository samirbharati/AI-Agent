import React, { useState } from 'react';
import {
  FileText,
  ExternalLink,
} from 'lucide-react';

interface QualityReportsPanelProps {
  projectId: string;
  reports: any[];
}

export const QualityReportsPanel: React.FC<QualityReportsPanelProps> = ({
  projectId,
  reports,
}) => {
  const [selectedReport, setSelectedReport] = useState<any | null>(reports[0] || null);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">APPROVED</span>;
      case 'CONDITIONALLY_APPROVED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-amber-500/20 text-amber-400 border border-amber-500/30">CONDITIONALLY APPROVED</span>;
      case 'BLOCKED':
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-rose-500/20 text-rose-400 border border-rose-500/30">BLOCKED</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-slate-800 text-slate-400">NOT VERIFIED</span>;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Reports List */}
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6">
        <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <FileText className="w-4 h-4 text-cyan-400" />
          <span>Historical Audits</span>
        </h3>

        {reports.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-mono">
            No formal reports generated yet. Run a Quality Audit to create a certification.
          </div>
        ) : (
          <div className="space-y-2.5">
            {reports.map((r) => {
              const isSelected = selectedReport?.id === r.id;
              return (
                <div
                  key={r.id}
                  onClick={() => setSelectedReport(r)}
                  className={`p-3 rounded-xl border cursor-pointer transition ${
                    isSelected
                      ? 'border-cyan-500 bg-cyan-500/10'
                      : 'border-[#1E293B] bg-[#111827] hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="font-mono text-xs font-bold text-white truncate">
                      {r.build_id}
                    </span>
                    {getStatusBadge(r.overall_status)}
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>{r.passed_tests}/{r.total_tests} tests</span>
                    <span>{r.created_at ? new Date(r.created_at).toLocaleDateString() : ''}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Report Preview */}
      <div className="lg:col-span-2 bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6">
        {selectedReport ? (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#1E293B]">
              <div>
                <h3 className="text-lg font-bold text-white font-mono">
                  {selectedReport.build_id}
                </h3>
                <p className="text-xs text-slate-400">
                  Generated on {selectedReport.created_at ? new Date(selectedReport.created_at).toUTCString() : ''}
                </p>
              </div>

              <div className="flex items-center gap-3">
                {getStatusBadge(selectedReport.overall_status)}
                {selectedReport.html_report_path && (
                  <a
                    href={`/api/v1/quality/${projectId}/reports/${selectedReport.id}/html`}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 font-mono text-xs hover:bg-cyan-600/30 transition"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>View Standalone HTML</span>
                  </a>
                )}
              </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
              <div className="bg-[#111827] p-3 rounded-lg border border-[#1F2937]">
                <span className="text-slate-500 block">Tests Passed</span>
                <span className="text-base font-bold text-emerald-400">
                  {selectedReport.passed_tests}/{selectedReport.total_tests}
                </span>
              </div>
              <div className="bg-[#111827] p-3 rounded-lg border border-[#1F2937]">
                <span className="text-slate-500 block">Coverage</span>
                <span className="text-base font-bold text-cyan-400">
                  {selectedReport.coverage_percent ? `${selectedReport.coverage_percent.toFixed(1)}%` : '0%'}
                </span>
              </div>
              <div className="bg-[#111827] p-3 rounded-lg border border-[#1F2937]">
                <span className="text-slate-500 block">P95 Latency</span>
                <span className="text-base font-bold text-amber-400">
                  {selectedReport.p95_latency_ms ? `${selectedReport.p95_latency_ms} ms` : '--'}
                </span>
              </div>
              <div className="bg-[#111827] p-3 rounded-lg border border-[#1F2937]">
                <span className="text-slate-500 block">Max Concurrency</span>
                <span className="text-base font-bold text-purple-400">
                  {selectedReport.max_concurrency_tested ? `${selectedReport.max_concurrency_tested} users` : 'None'}
                </span>
              </div>
            </div>

            {/* Markdown Summary Viewer */}
            {selectedReport.summary_markdown ? (
              <div className="bg-[#111827] p-4 rounded-xl border border-[#1F2937] font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto">
                {selectedReport.summary_markdown}
              </div>
            ) : (
              <div className="text-slate-500 text-xs font-mono py-8 text-center">
                Detailed markdown summary not present for this build.
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-16 text-slate-500 text-xs font-mono">
            Select an audit from the left to view certification details.
          </div>
        )}
      </div>
    </div>
  );
};
