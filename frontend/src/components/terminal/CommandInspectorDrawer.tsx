import React, { useState } from 'react';
import {
  X,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  Clock,
  Terminal,
  Cpu,
  Layers,
  ExternalLink,
} from 'lucide-react';
import type { TerminalCommand } from '../../types';

interface CommandInspectorDrawerProps {
  command: TerminalCommand | null;
  isOpen: boolean;
  onClose: () => void;
  onOpenTraceLogs?: (traceId: string) => void;
}

export const CommandInspectorDrawer: React.FC<CommandInspectorDrawerProps> = ({
  command,
  isOpen,
  onClose,
  onOpenTraceLogs,
}) => {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'stdout' | 'stderr' | 'metadata'>('stdout');

  if (!isOpen || !command) return null;

  const copyText = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const isSuccess = command.exit_code === 0 && command.status === 'completed';
  const durationSec = command.duration_ms ? (command.duration_ms / 1000).toFixed(2) : '-';

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-[#0B0F19] border-l border-[#1E293B] shadow-2xl flex flex-col font-mono animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 bg-[#0D1320] border-b border-[#1E293B] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Command Execution Inspector
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Meta Bar */}
      <div className="p-4 border-b border-[#1E293B] bg-[#07090D] space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            {isSuccess ? (
              <span className="flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                EXIT 0 (SUCCESS)
              </span>
            ) : (
              <span className="flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                <XCircle className="w-3.5 h-3.5" />
                EXIT {command.exit_code ?? 'ERR'} ({command.status.toUpperCase()})
              </span>
            )}

            <span className="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20">
              {command.agent_id ? `AGENT: ${command.agent_id.toUpperCase()}` : 'USER INTERACTIVE'}
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>{durationSec}s</span>
            {command.process_id && (
              <>
                <span className="text-slate-600">•</span>
                <span className="flex items-center gap-1 text-slate-400">
                  <Cpu className="w-3 h-3" /> PID {command.process_id}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Command Box */}
        <div className="relative group bg-[#0A0E17] border border-slate-800 rounded p-2.5">
          <p className="text-[11px] text-slate-500 mb-1">COMMAND:</p>
          <p className="text-xs text-emerald-300 break-all">{command.command}</p>
          <button
            onClick={() => copyText('cmd', command.command)}
            className="absolute top-2 right-2 p-1 text-slate-500 hover:text-white rounded hover:bg-slate-800 transition"
            title="Copy command"
          >
            {copiedKey === 'cmd' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
          <div>
            <span className="text-slate-500">Working Directory:</span>
            <p className="text-slate-300 truncate" title={command.working_directory}>
              {command.working_directory}
            </p>
          </div>
          <div>
            <span className="text-slate-500">Started At:</span>
            <p className="text-slate-300">
              {new Date(command.started_at).toLocaleTimeString()}
            </p>
          </div>
          {command.trace_id && (
            <div className="col-span-2 flex items-center justify-between pt-1 border-t border-slate-800">
              <span className="text-slate-500 flex items-center gap-1">
                <Layers className="w-3 h-3 text-cyan-400" />
                Trace ID: <strong className="text-cyan-300">{command.trace_id}</strong>
              </span>
              {onOpenTraceLogs && (
                <button
                  onClick={() => onOpenTraceLogs(command.trace_id!)}
                  className="flex items-center gap-1 text-xs text-cyan-400 hover:underline"
                >
                  <span>View in Logs Center</span>
                  <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[#1E293B] bg-[#0A0E17] text-xs">
        <button
          onClick={() => setActiveTab('stdout')}
          className={`flex-1 py-2 text-center border-b-2 font-semibold transition ${
            activeTab === 'stdout'
              ? 'border-emerald-400 text-emerald-300 bg-[#0D1320]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Stdout ({command.stdout_preview ? command.stdout_preview.length : 0} B)
        </button>
        <button
          onClick={() => setActiveTab('stderr')}
          className={`flex-1 py-2 text-center border-b-2 font-semibold transition ${
            activeTab === 'stderr'
              ? 'border-red-400 text-red-300 bg-[#0D1320]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Stderr ({command.stderr_preview ? command.stderr_preview.length : 0} B)
        </button>
        <button
          onClick={() => setActiveTab('metadata')}
          className={`flex-1 py-2 text-center border-b-2 font-semibold transition ${
            activeTab === 'metadata'
              ? 'border-cyan-400 text-cyan-300 bg-[#0D1320]'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          JSON Metadata
        </button>
      </div>

      {/* Output Content */}
      <div className="flex-1 overflow-y-auto p-4 bg-[#07090D] text-xs leading-relaxed">
        {activeTab === 'stdout' && (
          <div className="relative">
            <button
              onClick={() => copyText('stdout', command.stdout_preview || '')}
              className="absolute top-1 right-1 p-1 text-slate-500 hover:text-white rounded hover:bg-slate-800 transition"
              title="Copy stdout"
            >
              {copiedKey === 'stdout' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <pre className="text-slate-300 whitespace-pre-wrap break-all font-mono">
              {command.stdout_preview || '<No standard output captured>'}
            </pre>
          </div>
        )}

        {activeTab === 'stderr' && (
          <div className="relative">
            <button
              onClick={() => copyText('stderr', command.stderr_preview || '')}
              className="absolute top-1 right-1 p-1 text-slate-500 hover:text-white rounded hover:bg-slate-800 transition"
              title="Copy stderr"
            >
              {copiedKey === 'stderr' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <pre className="text-rose-400 whitespace-pre-wrap break-all font-mono">
              {command.stderr_preview || '<No standard error output captured>'}
            </pre>
          </div>
        )}

        {activeTab === 'metadata' && (
          <pre className="text-cyan-300 whitespace-pre font-mono text-[11px] bg-slate-950 p-3 rounded border border-slate-800 overflow-x-auto">
            {JSON.stringify(command, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};

