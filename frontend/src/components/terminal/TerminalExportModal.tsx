import React, { useState } from 'react';
import { X, Download, FileText, Code2, FileCode } from 'lucide-react';
import { getTerminalExportUrl } from '../../services/api';

interface TerminalExportModalProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const TerminalExportModal: React.FC<TerminalExportModalProps> = ({
  sessionId,
  isOpen,
  onClose,
}) => {
  const [format, setFormat] = useState<'txt' | 'markdown' | 'json'>('txt');

  if (!isOpen) return null;

  const handleDownload = () => {
    const url = getTerminalExportUrl(sessionId, format);
    const link = document.createElement('a');
    link.href = url;
    link.download = `terminal_${sessionId.slice(0, 8)}.${format === 'markdown' ? 'md' : format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    onClose();
  };

  const options = [
    { id: 'txt', title: 'Plain Text (.txt)', desc: 'Raw terminal output stream and command buffers', icon: FileText },
    { id: 'markdown', title: 'Markdown (.md)', desc: 'Formatted markdown document with terminal code blocks', icon: FileCode },
    { id: 'json', title: 'JSON (.json)', desc: 'Complete structured event array with timestamps and exit codes', icon: Code2 },
  ] as const;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-[#0D1320] border border-[#1E293B] rounded-xl shadow-2xl p-6 font-mono space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#1E293B]">
          <div className="flex items-center gap-2">
            <Download className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Export Terminal Session
            </h3>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-2.5">
          {options.map((opt) => {
            const Icon = opt.icon;
            const isSelected = format === opt.id;
            return (
              <div
                key={opt.id}
                onClick={() => setFormat(opt.id)}
                className={`p-3 rounded-lg border cursor-pointer transition flex items-start gap-3 ${
                  isSelected
                    ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-300'
                    : 'bg-[#07090D] border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <Icon className={`w-4 h-4 mt-0.5 ${isSelected ? 'text-emerald-400' : 'text-slate-500'}`} />
                <div>
                  <h4 className="text-xs font-bold">{opt.title}</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">{opt.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#1E293B]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white shadow-lg shadow-emerald-600/20 transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Log</span>
          </button>
        </div>
      </div>
    </div>
  );
};

