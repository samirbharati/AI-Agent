import React, { useState } from 'react';
import {
  Terminal as TerminalIcon,
  Bot,
  CheckCircle2,
  Shield,
  GitBranch,
  Plus,
  X,
  Loader2,
  Box,
} from 'lucide-react';
import type { TerminalSession } from '../../types';

interface TerminalTabsProps {
  sessions: TerminalSession[];
  activeSessionId: string;
  onSelectSession: (id: string) => void;
  onCloseSession: (id: string) => void;
  onRenameSession: (id: string, name: string) => void;
  onNewSession: () => void;
}

export const TerminalTabs: React.FC<TerminalTabsProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCloseSession,
  onRenameSession,
  onNewSession,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [tempName, setTempName] = useState('');

  const getTabIcon = (name: string, shellType: string) => {
    const lower = name.toLowerCase();
    if (lower.includes('developer') || lower.includes('agent')) return <Bot className="w-3.5 h-3.5 text-purple-400" />;
    if (lower.includes('qa') || lower.includes('test')) return <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />;
    if (lower.includes('security') || lower.includes('scanner')) return <Shield className="w-3.5 h-3.5 text-red-400" />;
    if (lower.includes('git')) return <GitBranch className="w-3.5 h-3.5 text-emerald-400" />;
    if (shellType === 'docker') return <Box className="w-3.5 h-3.5 text-blue-400" />;
    return <TerminalIcon className="w-3.5 h-3.5 text-slate-400" />;
  };

  const startRename = (s: TerminalSession) => {
    setEditingId(s.id);
    setTempName(s.name);
  };

  const handleRenameSubmit = (id: string) => {
    if (tempName.trim()) {
      onRenameSession(id, tempName.trim());
    }
    setEditingId(null);
  };

  return (
    <div className="flex items-center bg-[#07090D] border-b border-[#1E293B] overflow-x-auto scrollbar-none px-2 select-none">
      <div className="flex items-center gap-1 py-1.5 flex-nowrap">
        {sessions.map((s) => {
          const isActive = s.id === activeSessionId;
          const isRunning = Boolean(s.running_command || s.active_pid);

          return (
            <div
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              onDoubleClick={() => startRename(s)}
              className={`group flex items-center gap-2 px-3 py-1.5 rounded-t-md cursor-pointer border-t-2 text-xs font-mono transition whitespace-nowrap ${
                isActive
                  ? 'bg-[#0D1320] text-slate-100 border-emerald-400 font-semibold shadow-inner'
                  : 'bg-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border-transparent'
              }`}
            >
              {isRunning ? (
                <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />
              ) : (
                getTabIcon(s.name, s.shell_type)
              )}

              {editingId === s.id ? (
                <input
                  type="text"
                  value={tempName}
                  onChange={(e) => setTempName(e.target.value)}
                  onBlur={() => handleRenameSubmit(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleRenameSubmit(s.id);
                    if (e.key === 'Escape') setEditingId(null);
                  }}
                  autoFocus
                  className="bg-slate-950 border border-slate-700 rounded px-1.5 py-0.5 text-xs text-white outline-none w-28"
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span>{s.name}</span>
              )}

              {isRunning && (
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse ml-0.5" />
              )}

              {sessions.length > 1 && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCloseSession(s.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-400 text-slate-500 rounded p-0.5 transition ml-1"
                  title="Close session"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}

        <button
          onClick={onNewSession}
          className="flex items-center justify-center p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-900 rounded transition ml-1"
          title="Add Session Tab"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

