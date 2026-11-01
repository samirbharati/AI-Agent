import React from 'react';
import {
  X,
  Activity,
  Square,
  RotateCw,
  Cpu,
  Clock,
} from 'lucide-react';
import type { TerminalProcess } from '../../types';

interface ProcessMonitorPanelProps {
  processes: TerminalProcess[];
  isOpen: boolean;
  onClose: () => void;
  onStopProcess: (pid: number) => void;
  onRefresh: () => void;
}

export const ProcessMonitorPanel: React.FC<ProcessMonitorPanelProps> = ({
  processes,
  isOpen,
  onClose,
  onStopProcess,
  onRefresh,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-lg bg-[#0D1320] border-l border-[#1E293B] shadow-2xl flex flex-col font-mono animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-3.5 bg-[#0B0F19] border-b border-[#1E293B] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Active Process Monitor
          </h3>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
            {processes.length} running
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onRefresh}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
            title="Refresh processes"
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

      {/* Process Table */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-slate-800">
        {processes.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">
            <Cpu className="w-8 h-8 text-slate-600 mx-auto mb-2 opacity-50" />
            <p>No active processes running.</p>
            <p className="text-[11px] text-slate-600 mt-1">Commands executed in the terminal will appear here in real-time.</p>
          </div>
        ) : (
          processes.map((proc) => {
            const isRunning = proc.status === 'running';

            return (
              <div
                key={proc.process_id}
                className="p-3 rounded-lg bg-[#07090D] border border-slate-800/80 hover:border-slate-700 transition space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      PID {proc.process_id}
                    </span>
                    <span className="text-xs text-slate-300 font-semibold truncate max-w-[220px]" title={proc.command}>
                      {proc.command}
                    </span>
                  </div>

                  {isRunning && (
                    <button
                      onClick={() => onStopProcess(proc.process_id)}
                      className="flex items-center gap-1 px-2 py-1 rounded bg-red-500/20 hover:bg-red-500/30 text-xs text-red-300 border border-red-500/30 transition"
                      title="Terminate process"
                    >
                      <Square className="w-3 h-3 fill-red-400 text-red-400" />
                      <span>Stop</span>
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-400 pt-1 border-t border-slate-900">
                  <div>
                    <span className="text-slate-600 block text-[10px]">STARTED BY</span>
                    <span className="text-purple-400">{proc.started_by}</span>
                  </div>

                  <div>
                    <span className="text-slate-600 block text-[10px]">DURATION</span>
                    <span className="flex items-center gap-1 text-slate-300">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {proc.duration_seconds.toFixed(1)}s
                    </span>
                  </div>

                  <div>
                    <span className="text-slate-600 block text-[10px]">STATUS</span>
                    <span className={isRunning ? 'text-amber-400 font-bold animate-pulse' : 'text-slate-500'}>
                      {proc.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

