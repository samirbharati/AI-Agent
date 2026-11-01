import React, { useState, useEffect, useCallback } from 'react';
import {
  Hammer,
  CheckCircle2,
  Shield,
  GitBranch,
  Play,
  RotateCw,
  Clock,
  Eye,
  XCircle,
} from 'lucide-react';
import { getSpecializedConsole } from '../../services/api';
import type { TerminalCommand } from '../../types';

interface SpecializedConsoleViewProps {
  projectId: string | null;
  onInspectCommand: (cmd: TerminalCommand) => void;
  onReExecute: (cmdStr: string) => void;
}

export const SpecializedConsoleView: React.FC<SpecializedConsoleViewProps> = ({
  projectId,
  onInspectCommand,
  onReExecute,
}) => {
  const [consoleType, setConsoleType] = useState<'build' | 'qa' | 'security' | 'git'>('build');
  const [commands, setCommands] = useState<TerminalCommand[]>([]);
  const [loading, setLoading] = useState(false);

  const loadConsoleCommands = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getSpecializedConsole(consoleType, projectId || undefined);
      setCommands(res.commands || []);
    } catch (e) {
      console.error('Failed to load specialized console:', e);
    } finally {
      setLoading(false);
    }
  }, [consoleType, projectId]);

  useEffect(() => {
    loadConsoleCommands();
  }, [loadConsoleCommands]);

  const consoles = [
    { id: 'build', label: 'Build Console', icon: Hammer, color: 'text-amber-400 border-amber-500/30' },
    { id: 'qa', label: 'QA Console', icon: CheckCircle2, color: 'text-cyan-400 border-cyan-500/30' },
    { id: 'security', label: 'Security Console', icon: Shield, color: 'text-red-400 border-red-500/30' },
    { id: 'git', label: 'Git Console', icon: GitBranch, color: 'text-emerald-400 border-emerald-500/30' },
  ] as const;

  return (
    <div className="flex flex-col h-full bg-[#080B12] border-t border-[#1E293B] font-mono">
      {/* Console Sub-header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#0D1320] border-b border-[#1E293B]">
        <div className="flex items-center gap-2">
          {consoles.map((c) => {
            const Icon = c.icon;
            const isActive = consoleType === c.id;
            return (
              <button
                key={c.id}
                onClick={() => setConsoleType(c.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition border ${
                  isActive
                    ? `bg-[#07090D] ${c.color} shadow-sm`
                    : 'bg-transparent text-slate-400 hover:text-white border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{c.label}</span>
              </button>
            );
          })}
        </div>

        <button
          onClick={loadConsoleCommands}
          disabled={loading}
          className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 transition"
        >
          <RotateCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Content List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-800">
        {loading ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            Loading specialized console telemetry...
          </div>
        ) : commands.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No executions recorded for the {consoleType.toUpperCase()} console yet.
          </div>
        ) : (
          commands.map((cmd) => {
            const isSuccess = cmd.exit_code === 0 && cmd.status === 'completed';
            return (
              <div
                key={cmd.id}
                className="p-3 rounded-lg bg-[#070A10] border border-slate-800 hover:border-slate-700 transition space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {isSuccess ? (
                      <span className="flex items-center gap-1 text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        EXIT 0
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[11px] font-bold text-rose-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
                        <XCircle className="w-3.5 h-3.5" />
                        EXIT {cmd.exit_code ?? 'ERR'}
                      </span>
                    )}

                    <span className="text-xs text-slate-200 font-semibold">{cmd.command}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {cmd.duration_ms ? `${(cmd.duration_ms / 1000).toFixed(2)}s` : '-'}
                    </span>

                    <button
                      onClick={() => onInspectCommand(cmd)}
                      className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
                      title="Inspect execution"
                    >
                      <Eye className="w-3.5 h-3.5 text-cyan-400" />
                    </button>

                    <button
                      onClick={() => onReExecute(cmd.command)}
                      className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
                      title="Re-run command"
                    >
                      <Play className="w-3.5 h-3.5 text-emerald-400" />
                    </button>
                  </div>
                </div>

                {cmd.stdout_preview && (
                  <pre className="text-[11px] text-slate-400 bg-black/40 p-2 rounded border border-slate-900 max-h-24 overflow-y-auto whitespace-pre-wrap break-all">
                    {cmd.stdout_preview.slice(0, 300)}
                    {cmd.stdout_preview.length > 300 && '...'}
                  </pre>
                )}

                {cmd.stderr_preview && (
                  <pre className="text-[11px] text-rose-400 bg-red-950/20 p-2 rounded border border-red-950/40 max-h-24 overflow-y-auto whitespace-pre-wrap break-all">
                    {cmd.stderr_preview.slice(0, 300)}
                    {cmd.stderr_preview.length > 300 && '...'}
                  </pre>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

