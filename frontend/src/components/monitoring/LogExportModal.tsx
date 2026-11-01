import React, { useState } from 'react';
import { X, Download, FileText, Table, FileCode, ShieldCheck } from 'lucide-react';
import { getLogsExportUrl } from '../../services/api';
import type { FilterState } from './LogFilterPanel';

interface LogExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FilterState;
}

export const LogExportModal: React.FC<LogExportModalProps> = ({
  isOpen,
  onClose,
  filters,
}) => {
  const [selectedFormat, setSelectedFormat] = useState<'json' | 'csv' | 'markdown' | 'txt'>('json');

  if (!isOpen) return null;

  const handleDownload = () => {
    const url = getLogsExportUrl({
      format: selectedFormat,
      project_id: filters.project_id,
      severity: filters.severity,
      source: filters.source,
      category: filters.category,
      search: filters.search,
    });
    window.open(url, '_blank');
    onClose();
  };

  const formats = [
    {
      id: 'json',
      title: 'JSON Data Stream',
      ext: '.json',
      desc: 'Structured JSON array with full metadata, timestamps, and payload attributes.',
      icon: <FileCode className="w-5 h-5 text-cyan-400" />,
    },
    {
      id: 'csv',
      title: 'CSV Spreadsheet',
      ext: '.csv',
      desc: 'Comma-separated values ready for Excel, Google Sheets, or BI analytics.',
      icon: <Table className="w-5 h-5 text-emerald-400" />,
    },
    {
      id: 'markdown',
      title: 'Markdown Engineering Report',
      ext: '.md',
      desc: 'Formatted markdown table suitable for GitHub issues, PR summaries, or documentation.',
      icon: <FileText className="w-5 h-5 text-purple-400" />,
    },
    {
      id: 'txt',
      title: 'Standard Terminal Log',
      ext: '.txt',
      desc: 'Raw chronological monospace output matching developer terminal conventions.',
      icon: <FileText className="w-5 h-5 text-slate-400" />,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-5 space-y-4 font-sans text-xs">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Download className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-bold text-white m-0">Export Filtered Logs</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Security Notice */}
        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 flex items-center gap-2.5 text-slate-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-[11px] leading-tight font-mono">
            Security redaction active: AWS keys, tokens, and database passwords are automatically masked.
          </span>
        </div>

        {/* Format Options */}
        <div className="space-y-2">
          <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
            Select Export Format
          </label>
          <div className="grid grid-cols-1 gap-2">
            {formats.map((fmt) => (
              <div
                key={fmt.id}
                onClick={() => setSelectedFormat(fmt.id as any)}
                className={`p-3 rounded-xl border flex items-start gap-3 cursor-pointer transition ${
                  selectedFormat === fmt.id
                    ? 'bg-cyan-950/30 border-cyan-500 shadow-[0_0_8px_rgba(34,211,238,0.15)]'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 shrink-0">
                  {fmt.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-xs">{fmt.title}</span>
                    <span className="font-mono text-[10px] text-slate-500">{fmt.ext}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed m-0">
                    {fmt.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
          >
            Cancel
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-lg shadow-cyan-600/20 transition active:scale-95"
          >
            <Download className="w-4 h-4" />
            <span>Download Export</span>
          </button>
        </div>
      </div>
    </div>
  );
};

