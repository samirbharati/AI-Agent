import React from 'react';
import {
  Terminal as TerminalIcon,
  Plus,
  Columns2,
  Trash2,
  RotateCcw,
  Square,
  Copy,
  Download,
  Maximize2,
  Minimize2,
  History,
  Activity,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import type { Project, TerminalSecurityStatus, TerminalSession } from '../../types';

interface TerminalHeaderProps {
  project: Project | null;
  activeSession: TerminalSession | null;
  runningProcessCount: number;
  securityStatus: TerminalSecurityStatus | null;
  onNewTerminal: () => void;
  onSplitTerminal: () => void;
  isSplit: boolean;
  onClearTerminal: () => void;
  onRestartSession: () => void;
  onStopProcess: () => void;
  hasRunningProcess: boolean;
  onCopyOutput: () => void;
  onOpenExport: () => void;
  onToggleFullscreen: () => void;
  isFullscreen: boolean;
  onToggleHistory: () => void;
  isHistoryOpen: boolean;
  onToggleProcesses: () => void;
  isProcessesOpen: boolean;
}

export const TerminalHeader: React.FC<TerminalHeaderProps> = ({
  project,
  activeSession,
  runningProcessCount,
  securityStatus,
  onNewTerminal,
  onSplitTerminal,
  isSplit,
  onClearTerminal,
  onRestartSession,
  onStopProcess,
  hasRunningProcess,
  onCopyOutput,
  onOpenExport,
  onToggleFullscreen,
  isFullscreen,
  onToggleHistory,
  isHistoryOpen,
  onToggleProcesses,
  isProcessesOpen,
}) => {
  const isDocker = securityStatus?.docker?.available ?? false;
  const isolationLabel = isDocker ? 'DOCKER CONTAINER ISOLATION' : 'SUBPROCESS LOCAL SANDBOX';

  return (
    <div className="bg-[#0D1320] border-b border-[#1E293B] px-5 py-3 select-none">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Metadata Telemetry Banner */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <TerminalIcon className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-wider text-slate-100 uppercase font-mono">
                AgentForge Terminal
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                ONLINE
              </span>
              {isDocker ? (
                <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-cyan-400" />
                  DOCKER READY
                </span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                  <ShieldAlert className="w-3 h-3 text-amber-400" />
                  SUBPROCESS SANDBOX
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mt-0.5">
              <span>PROJECT: <strong className="text-cyan-400">{project ? project.name : 'ALL PROJECTS'}</strong></span>
              <span className="text-slate-600">|</span>
              <span>SHELL: <strong className="text-purple-400">{(activeSession?.shell_type || 'powershell').toUpperCase()}</strong></span>
              <span className="text-slate-600">|</span>
              <span>ENV: <strong className="text-slate-300">{isolationLabel}</strong></span>
              {runningProcessCount > 0 && (
                <>
                  <span className="text-slate-600">|</span>
                  <span className="text-amber-400 animate-pulse font-bold">
                    {runningProcessCount} ACTIVE PROCESS{runningProcessCount > 1 ? 'ES' : ''}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right: Terminal Action Toolbar */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={onNewTerminal}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 border border-slate-700/80 transition"
            title="Create new terminal session"
          >
            <Plus className="w-3.5 h-3.5 text-emerald-400" />
            <span>New</span>
          </button>

          <button
            onClick={onSplitTerminal}
            className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-mono border transition ${
              isSplit
                ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                : 'bg-slate-800/80 hover:bg-slate-700 text-slate-200 border-slate-700/80'
            }`}
            title="Split terminal side-by-side"
          >
            <Columns2 className="w-3.5 h-3.5" />
            <span>Split</span>
          </button>

          <button
            onClick={onClearTerminal}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 border border-slate-700/80 transition"
            title="Clear terminal buffer"
          >
            <Trash2 className="w-3.5 h-3.5 text-slate-400" />
            <span>Clear</span>
          </button>

          <button
            onClick={onRestartSession}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-xs font-mono text-slate-200 border border-slate-700/80 transition"
            title="Restart session buffer"
          >
            <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
            <span>Restart</span>
          </button>

          {hasRunningProcess && (
            <button
              onClick={onStopProcess}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-red-500/20 hover:bg-red-500/30 text-xs font-mono text-red-300 border border-red-500/40 animate-pulse transition"
              title="Stop running command (SIGINT / Kill)"
            >
              <Square className="w-3.5 h-3.5 fill-red-400 text-red-400" />
              <span>Stop Process</span>
            </button>
          )}

          <div className="w-px h-5 bg-slate-800 mx-1" />

          <button
            onClick={onCopyOutput}
            className="p-1.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition"
            title="Copy all output"
          >
            <Copy className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onOpenExport}
            className="p-1.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition"
            title="Export session"
          >
            <Download className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onToggleHistory}
            className={`p-1.5 rounded-md border transition ${
              isHistoryOpen
                ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border-slate-700/80'
            }`}
            title="Toggle Command History Drawer"
          >
            <History className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onToggleProcesses}
            className={`p-1.5 rounded-md border transition ${
              isProcessesOpen
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-slate-800/80 hover:bg-slate-700 text-slate-300 border-slate-700/80'
            }`}
            title="Toggle Process Monitor Panel"
          >
            <Activity className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onToggleFullscreen}
            className="p-1.5 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition"
            title={isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
};

