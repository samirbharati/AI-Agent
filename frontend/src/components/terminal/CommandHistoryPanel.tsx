import React, { useState, useMemo } from 'react';
import {
  X,
  Search,
  Play,
  RotateCw,
  CheckCircle2,
  XCircle,
  Clock,
  Eye,
  History,
} from 'lucide-react';
import type { TerminalCommand } from '../../types';

interface CommandHistoryPanelProps {
  history: TerminalCommand[];
  isOpen: boolean;
  onClose: () => void;
  onSelectCommand: (cmd: TerminalCommand) => void;
  onReExecuteCommand: (commandStr: string) => void;
  onRefreshHistory: () => void;
}

export const CommandHistoryPanel: React.FC<CommandHistoryPanelProps> = ({
  history,
  isOpen,
  onClose,
  onSelectCommand,
  onReExecuteCommand,
  onRefreshHistory,
}) => {
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterAgent, setFilterAgent] = useState<string>('all');

  const filteredHistory = useMemo(() => {
    return history.filter((c) => {
      if (filterStatus !== 'all' && c.status !== filterStatus) return false;
      if (filterAgent !== 'all') {
        if (filterAgent === 'user' && c.agent_id) return false;
        if (filterAgent !== 'user' && c.agent_id !== filterAgent) return false;
      }
      if (search && !c.command.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [history, filterStatus, filterAgent, search]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-md bg-[#0D1320] border-l border-[#1E293B] shadow-2xl flex flex-col font-mono animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-3.5 bg-[#0B0F19] border-b border-[#1E293B] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Command Execution History
          </h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300">
            {filteredHistory.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onRefreshHistory}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
            title="Refresh history"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-3 bg-[#07090D] border-b border-[#1E293B] space-y-2">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search commands..."
            className="w-full bg-[#0A0E17] border border-slate-800 rounded pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-purple-500/50"
          />
        </div>

        <div className="flex gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="flex-1 bg-[#0A0E17] border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed (Exit 0)</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
            <option value="timed_out">Timed Out</option>
          </select>

          <select
            value={filterAgent}
            onChange={(e) => setFilterAgent(e.target.value)}
            className="flex-1 bg-[#0A0E17] border border-slate-800 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none"
          >
            <option value="all">All Callers</option>
            <option value="user">User Interactive</option>
            <option value="developer">Developer Agent</option>
            <option value="qa-engineer">QA Engineer</option>
            <option value="security-engineer">Security Engineer</option>
          </select>
        </div>
      </div>

      {/* History Items List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin scrollbar-thumb-slate-800">
        {filteredHistory.length === 0 ? (
          <div className="text-center py-12 text-slate-600 text-xs">
            No matching command executions found.
          </div>
        ) : (
          filteredHistory.map((cmd) => {
            const isSuccess = cmd.status === 'completed' && cmd.exit_code === 0;

            return (
              <div
                key={cmd.id}
                className="group p-2.5 rounded bg-[#0A0E17] border border-slate-800/80 hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-1.5">
                    {isSuccess ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    )}
                    <span className="text-[11px] font-bold text-slate-300 truncate max-w-[200px]" title={cmd.command}>
                      {cmd.command}
                    </span>
                  </div>

                  <span className="text-[10px] text-slate-500 flex items-center gap-1 shrink-0">
                    <Clock className="w-3 h-3" />
                    {cmd.duration_ms ? `${(cmd.duration_ms / 1000).toFixed(1)}s` : '-'}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-900">
                  <span className="text-purple-400/90 truncate">
                    {cmd.agent_id ? `agent:${cmd.agent_id}` : 'user'}
                  </span>
                  <span>{new Date(cmd.started_at).toLocaleTimeString()}</span>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-1.5 mt-2 pt-1.5 border-t border-slate-900 opacity-90">
                  <button
                    onClick={() => onSelectCommand(cmd)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-300 hover:text-white transition"
                    title="Inspect details"
                  >
                    <Eye className="w-3 h-3 text-cyan-400" />
                    <span>Inspect</span>
                  </button>

                  <button
                    onClick={() => onReExecuteCommand(cmd.command)}
                    className="flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-[10px] text-emerald-300 hover:text-white transition"
                    title="Re-run command"
                  >
                    <Play className="w-3 h-3 text-emerald-400" />
                    <span>Run</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

