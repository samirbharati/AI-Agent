import React, { useRef, useEffect, useState } from 'react';
import { Terminal, ArrowDown, Pause, Play, ChevronLeft, ChevronRight, Zap } from 'lucide-react';
import type { MonitoringEvent } from '../../types';

interface LiveTerminalProps {
  events: MonitoringEvent[];
  selectedEvent: MonitoringEvent | null;
  onSelectEvent: (event: MonitoringEvent) => void;
  page: number;
  totalPages: number;
  onPageChange: (newPage: number) => void;
  totalEvents: number;
  isStreaming: boolean;
}

export const LiveTerminal: React.FC<LiveTerminalProps> = ({
  events,
  selectedEvent,
  onSelectEvent,
  page,
  totalPages,
  onPageChange,
  totalEvents,
  isStreaming,
}) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [hasNewEvents, setHasNewEvents] = useState(false);
  const previousLengthRef = useRef(events.length);

  // Detect user scroll to pause auto-scroll
  const handleScroll = () => {
    if (!terminalRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = terminalRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    if (isAtBottom) {
      setAutoScroll(true);
      setHasNewEvents(false);
    } else {
      setAutoScroll(false);
    }
  };

  // Scroll to bottom when new events arrive if auto-scroll is enabled
  useEffect(() => {
    if (events.length > previousLengthRef.current) {
      if (autoScroll && terminalRef.current) {
        terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        setHasNewEvents(false);
      } else if (!autoScroll) {
        setHasNewEvents(true);
      }
    }
    previousLengthRef.current = events.length;
  }, [events, autoScroll]);

  const scrollToBottom = () => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
      setAutoScroll(true);
      setHasNewEvents(false);
    }
  };

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      const hours = String(d.getHours()).padStart(2, '0');
      const mins = String(d.getMinutes()).padStart(2, '0');
      const secs = String(d.getSeconds()).padStart(2, '0');
      const ms = String(d.getMilliseconds()).padStart(3, '0');
      return `${hours}:${mins}:${secs}.${ms}`;
    } catch {
      return iso;
    }
  };

  const getLevelBadge = (severity: string) => {
    const s = severity.toLowerCase();
    switch (s) {
      case 'success':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/80';
      case 'warning':
        return 'text-amber-400 bg-amber-950/40 border-amber-800/80';
      case 'error':
        return 'text-rose-400 bg-rose-950/40 border-rose-800/80';
      case 'critical':
        return 'text-red-400 bg-red-950/60 border-red-700 shadow-[0_0_8px_rgba(239,68,68,0.3)] animate-pulse';
      case 'debug':
        return 'text-slate-400 bg-slate-900 border-slate-700';
      default:
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-800/80';
    }
  };

  const getSourceBadge = (source: string) => {
    const src = source.toLowerCase();
    if (src.includes('dev') || src.includes('software')) return 'text-purple-300 bg-purple-950/30 border-purple-800/50';
    if (src.includes('qa') || src.includes('test')) return 'text-blue-300 bg-blue-950/30 border-blue-800/50';
    if (src.includes('sec')) return 'text-amber-300 bg-amber-950/30 border-amber-800/50';
    if (src.includes('arch') || src.includes('req')) return 'text-cyan-300 bg-cyan-950/30 border-cyan-800/50';
    return 'text-slate-300 bg-slate-900/60 border-slate-700/50';
  };

  return (
    <div className="bg-[#070A10] border border-[#243044] rounded-xl shadow-2xl flex flex-col font-mono text-xs overflow-hidden relative">
      {/* Terminal Title Bar */}
      <div className="bg-[#0D1320] px-4 py-2.5 border-b border-[#243044] flex items-center justify-between gap-3 select-none">
        <div className="flex items-center gap-2">
          {/* Mac-style traffic lights */}
          <div className="flex items-center gap-1.5 mr-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block" />
          </div>

          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-white font-bold text-xs tracking-wide">
            TERMINAL // LIVE EVENT STREAM
          </span>

          <span className="text-[11px] text-slate-400 ml-2 hidden sm:inline">
            ({totalEvents.toLocaleString()} total logged events)
          </span>
        </div>

        {/* Terminal Controls */}
        <div className="flex items-center gap-2">
          {/* Stream pulse */}
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[11px]">
            <span
              className={`w-2 h-2 rounded-full ${
                isStreaming ? 'bg-emerald-400 shadow-[0_0_6px_#22c55e]' : 'bg-slate-500'
              }`}
            />
            <span className="text-slate-300">{isStreaming ? 'STREAMING' : 'IDLE'}</span>
          </div>

          {/* Pause / Resume Auto-scroll */}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded border text-[11px] transition ${
              autoScroll
                ? 'bg-slate-900 text-cyan-300 border-cyan-800/60 hover:bg-slate-800'
                : 'bg-amber-950/40 text-amber-300 border-amber-800 hover:bg-amber-900/60'
            }`}
            title={autoScroll ? 'Pause auto-scroll' : 'Resume auto-scroll'}
          >
            {autoScroll ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            <span>{autoScroll ? 'Auto-scroll On' : 'Paused'}</span>
          </button>
        </div>
      </div>

      {/* Floating "New events available" pill */}
      {hasNewEvents && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-14 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-cyan-600 text-white text-[11px] font-bold shadow-lg shadow-cyan-600/30 hover:bg-cyan-500 transition animate-bounce"
        >
          <ArrowDown className="w-3.5 h-3.5" />
          <span>New events received — Jump to latest</span>
        </button>
      )}

      {/* Terminal Output Rows */}
      <div
        ref={terminalRef}
        onScroll={handleScroll}
        className="flex-1 max-h-[540px] overflow-y-auto p-3 space-y-1 divide-y divide-slate-900/40"
      >
        {events.length === 0 ? (
          <div className="py-16 text-center text-slate-500 space-y-2">
            <Zap className="w-8 h-8 mx-auto text-slate-600" />
            <p className="m-0 font-mono text-xs">No events match the active search or filter criteria.</p>
            <p className="m-0 text-[11px] text-slate-600">Events from agent workflows and tools appear here in real-time.</p>
          </div>
        ) : (
          events.map((e) => {
            const isSelected = selectedEvent?.id === e.id;
            return (
              <div
                key={e.id}
                onClick={() => onSelectEvent(e)}
                className={`py-1.5 px-2 rounded-lg cursor-pointer transition flex flex-col sm:flex-row sm:items-baseline gap-1.5 sm:gap-2.5 text-xs hover:bg-[#111827]/80 ${
                  isSelected ? 'bg-cyan-950/30 border border-cyan-800/80 shadow-[0_0_8px_rgba(34,211,238,0.15)]' : ''
                }`}
              >
                {/* Timestamp */}
                <span className="text-slate-500 font-mono text-[11px] shrink-0 select-none">
                  [{formatTimestamp(e.timestamp)}]
                </span>

                {/* Level Badge */}
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border shrink-0 select-none ${getLevelBadge(
                    e.severity
                  )}`}
                >
                  {e.severity}
                </span>

                {/* Source Badge */}
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold border shrink-0 select-none ${getSourceBadge(
                    e.source
                  )}`}
                >
                  [{e.source.replace('-agent', '').toUpperCase()}]
                </span>

                {/* Trace / Task pills if present */}
                {e.task_id && (
                  <span className="px-1.5 py-0.2 rounded text-[10px] bg-slate-800 text-amber-300 font-mono shrink-0">
                    {e.task_id}
                  </span>
                )}

                {/* Message */}
                <span className="text-slate-200 font-mono flex-1 break-words">
                  {e.message}
                </span>

                {/* Duration Badge if present */}
                {e.duration_ms !== null && e.duration_ms !== undefined && (
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded border border-emerald-900/40 shrink-0 self-start sm:self-auto">
                    {(e.duration_ms / 1000).toFixed(2)}s
                  </span>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Terminal Footer with Pagination */}
      <div className="bg-[#0D1320] px-4 py-2 border-t border-[#243044] flex items-center justify-between text-[11px] text-slate-400">
        <div>
          <span>
            Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-700/80 hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none text-slate-300 transition"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Prev</span>
          </button>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-700/80 hover:bg-slate-800 disabled:opacity-40 disabled:pointer-events-none text-slate-300 transition"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

