import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Pause, Play, Trash2, Maximize2 } from 'lucide-react';
import type { WorkflowEvent } from '../types';

interface LiveLogsProps {
  events: WorkflowEvent[];
  onClear: () => void;
  isConnected: boolean;
  onOpenMonitoringCenter?: () => void;
}

export const LiveLogs: React.FC<LiveLogsProps> = ({
  events,
  onClear,
  isConnected,
  onOpenMonitoringCenter,
}) => {
  const [autoScroll, setAutoScroll] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  const filteredEvents = events.filter((e) => {
    if (filterSeverity === 'all') return true;
    return e.severity === filterSeverity;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'error':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'warning':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'debug':
        return 'text-slate-400 bg-slate-800 border-slate-700';
      default:
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col h-[340px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-2">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 m-0">
            Live Agent Execution Stream
          </h3>
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-emerald-400 animate-ping' : 'bg-slate-600'
            }`}
            title={isConnected ? 'Stream Active' : 'Disconnected'}
          />
        </div>

        <div className="flex items-center gap-2">
          {/* Severity filter */}
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="text-[11px] bg-slate-800 border border-slate-700 rounded px-2 py-0.5 text-slate-300 focus:outline-none"
          >
            <option value="all">All Severities</option>
            <option value="info">Info only</option>
            <option value="warning">Warnings</option>
            <option value="error">Errors</option>
          </select>

          {/* Auto scroll toggle */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`p-1 rounded text-xs transition ${
              autoScroll ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
            title={autoScroll ? 'Auto-scroll ON' : 'Auto-scroll PAUSED'}
          >
            {autoScroll ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* Clear */}
          <button
            onClick={onClear}
            className="p-1 rounded bg-slate-800 text-slate-400 hover:text-rose-400 transition"
            title="Clear logs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>

          {/* Open Command Center */}
          {onOpenMonitoringCenter && (
            <button
              onClick={onOpenMonitoringCenter}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800 text-cyan-300 hover:bg-cyan-900/80 text-[11px] font-mono transition"
              title="Open full SOC Monitoring Center"
            >
              <Maximize2 className="w-3 h-3" />
              <span className="hidden sm:inline">Command Center</span>
            </button>
          )}
        </div>
      </div>

      {/* Log entries */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-1 font-mono text-[11px] pr-1 selection:bg-indigo-500/30"
      >
        {filteredEvents.length === 0 ? (
          <div className="h-full flex items-center justify-center text-slate-600">
            Awaiting agent execution events...
          </div>
        ) : (
          filteredEvents.map((evt, idx) => (
            <div
              key={`${evt.id}-${idx}`}
              className="py-1 px-2 rounded hover:bg-slate-800/40 flex items-start gap-2 leading-relaxed"
            >
              <span className="text-slate-500 text-[10px] shrink-0 mt-0.5">
                {new Date(evt.created_at).toLocaleTimeString()}
              </span>
              <span
                className={`text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.2 rounded border shrink-0 ${getSeverityBadge(
                  evt.severity
                )}`}
              >
                {evt.severity}
              </span>
              <span className="text-indigo-400 text-[10px] shrink-0">[{evt.event_type}]</span>
              <span className="text-slate-200 break-words flex-1">{evt.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
