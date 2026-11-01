import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  ChevronDown,
  ArrowRight,
  Loader2,
  ZoomIn,
  ZoomOut,
  CornerDownLeft,
} from 'lucide-react';
import type { TerminalEventItem, TerminalSession } from '../../types';

interface TerminalConsoleProps {
  session: TerminalSession | null;
  events: TerminalEventItem[];
  onExecuteCommand: (command: string) => Promise<void>;
  onInterrupt: () => void;
  isRunning: boolean;
  fontSize?: 'sm' | 'base' | 'lg';
}

export const TerminalConsole: React.FC<TerminalConsoleProps> = ({
  session,
  events,
  onExecuteCommand,
  onInterrupt,
  isRunning,
}) => {
  const [commandInput, setCommandInput] = useState('');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [fontSize, setFontSize] = useState<'text-xs' | 'text-sm' | 'text-base'>('text-sm');
  const [hasUnread, setHasUnread] = useState(false);
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  const terminalEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll logic
  const scrollToBottom = useCallback((smooth = true) => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
      setHasUnread(false);
      setIsAutoScroll(true);
    }
  }, []);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAutoScroll(atBottom);
    if (atBottom) {
      setHasUnread(false);
    }
  };

  useEffect(() => {
    if (isAutoScroll) {
      scrollToBottom(false);
    } else {
      setHasUnread(true);
    }
  }, [events, isAutoScroll, scrollToBottom]);

  // Command submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cmd = commandInput.trim();
    if (!cmd || isRunning) return;

    setCommandHistory((prev) => [...prev, cmd]);
    setHistoryIndex(-1);
    setCommandInput('');

    await onExecuteCommand(cmd);
    setTimeout(() => scrollToBottom(true), 100);
  };

  // Keyboard navigation for history (Up/Down) & Ctrl+C
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.ctrlKey && e.key.toLowerCase() === 'c') {
      e.preventDefault();
      onInterrupt();
      return;
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length === 0) return;
      const nextIdx = historyIndex === -1 ? commandHistory.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(nextIdx);
      setCommandInput(commandHistory[nextIdx]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (commandHistory.length === 0) return;
      const nextIdx = historyIndex + 1;
      if (nextIdx >= commandHistory.length) {
        setHistoryIndex(-1);
        setCommandInput('');
      } else {
        setHistoryIndex(nextIdx);
        setCommandInput(commandHistory[nextIdx]);
      }
    }
  };

  // ANSI to HTML colored line parser
  const renderLine = (raw: string, index: number) => {
    // Basic ANSI color replacement
    let formatted = raw;
    const isAgent = formatted.includes('[AGENT:');
    const isPrompt = formatted.includes('PS ') || formatted.startsWith('>');
    const isError = formatted.includes('[ERROR]') || formatted.includes('exited with code') && !formatted.includes('code 0');
    const isSuccess = formatted.includes('[SUCCESS]') || formatted.includes('code 0');
    const isWarning = formatted.includes('[WARNING]') || formatted.includes('requires confirmation');

    // Clean ANSI escape sequences for text display while retaining key color classes
    const clean = formatted.replace(/\x1b\[[0-9;]*m/g, '');

    let colorClass = 'text-slate-300';
    if (isAgent) colorClass = 'text-purple-300 font-semibold bg-purple-950/20 px-1 py-0.5 rounded border border-purple-800/30';
    else if (isPrompt) colorClass = 'text-emerald-400 font-bold';
    else if (isSuccess) colorClass = 'text-emerald-400 font-semibold';
    else if (isError) colorClass = 'text-rose-400 font-semibold';
    else if (isWarning) colorClass = 'text-amber-400';

    return (
      <div key={index} className={`font-mono leading-relaxed whitespace-pre-wrap break-all ${colorClass}`}>
        {clean}
      </div>
    );
  };

  return (
    <div
      className="relative flex flex-col flex-1 bg-[#07090D] h-full overflow-hidden select-text border border-[#1E293B]"
      onClick={() => inputRef.current?.focus()}
    >
      {/* Console Top Bar Tools */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#0A0E17] border-b border-[#1E293B] text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span className="text-slate-300 font-bold">{session?.name || 'Active Terminal'}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">{session?.working_directory || '/workspace'}</span>
        </div>

        <div className="flex items-center gap-2">
          {isRunning && (
            <div className="flex items-center gap-1.5 text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 animate-pulse">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>RUNNING</span>
            </div>
          )}

          <div className="flex items-center gap-1 border-l border-slate-800 pl-2">
            <button
              onClick={() => setFontSize(fontSize === 'text-xs' ? 'text-sm' : 'text-base')}
              className="p-1 hover:text-white transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3 h-3" />
            </button>
            <button
              onClick={() => setFontSize(fontSize === 'text-base' ? 'text-sm' : 'text-xs')}
              className="p-1 hover:text-white transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>

      {/* Terminal Output Area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className={`flex-1 overflow-y-auto p-4 space-y-0.5 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent ${fontSize}`}
      >
        {events.length === 0 ? (
          <div className="text-slate-600 font-mono py-8 text-center select-none">
            <p className="text-slate-400 font-bold">AgentForge Terminal Connected.</p>
            <p className="text-xs text-slate-600 mt-1">Ready for PowerShell, development commands, agent automation, or test execution.</p>
          </div>
        ) : (
          events.map((evt, idx) => renderLine(evt.data, idx))
        )}
        <div ref={terminalEndRef} />
      </div>

      {/* Floating Unread Indicator */}
      {hasUnread && (
        <button
          onClick={() => scrollToBottom(true)}
          className="absolute bottom-16 right-6 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono font-semibold shadow-lg shadow-cyan-600/30 transition animate-bounce z-20"
        >
          <span>New Output Available</span>
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
      )}

      {/* Interactive Command Input Box */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-4 py-2.5 bg-[#0A0E17] border-t border-[#1E293B]"
      >
        <div className="flex items-center gap-1.5 text-emerald-400 font-mono font-bold text-xs select-none">
          <ArrowRight className="w-3.5 h-3.5 text-emerald-400" />
          <span>PS&gt;</span>
        </div>

        <input
          ref={inputRef}
          type="text"
          value={commandInput}
          onChange={(e) => setCommandInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isRunning}
          placeholder={isRunning ? "Process executing... press Ctrl+C or 'Stop Process' to interrupt" : "Enter command (e.g. pytest -v, git status, python main.py)..."}
          className="flex-1 bg-transparent text-slate-100 font-mono text-xs focus:outline-none placeholder-slate-600"
          autoFocus
        />

        <button
          type="submit"
          disabled={!commandInput.trim() || isRunning}
          className="p-1 rounded bg-slate-800 hover:bg-emerald-600 text-slate-300 hover:text-white disabled:opacity-40 disabled:hover:bg-slate-800 transition"
          title="Execute Command"
        >
          <CornerDownLeft className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};

