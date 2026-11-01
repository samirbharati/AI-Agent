import React, { useState } from 'react';
import { X, Copy, Check, Terminal, ExternalLink } from 'lucide-react';
import type { MonitoringEvent } from '../../types';

interface EventDetailDrawerProps {
  event: MonitoringEvent | null;
  onClose: () => void;
  onFilterByTrace?: (traceId: string) => void;
}

export const EventDetailDrawer: React.FC<EventDetailDrawerProps> = ({
  event,
  onClose,
  onFilterByTrace,
}) => {
  const [copiedId, setCopiedId] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);

  if (!event) return null;

  const handleCopyId = () => {
    navigator.clipboard.writeText(event.id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const severityColors: Record<string, { bg: string; text: string; border: string }> = {
    info: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/30' },
    success: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
    warning: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
    error: { bg: 'bg-rose-500/10', text: 'text-rose-400', border: 'border-rose-500/30' },
    critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/50' },
    debug: { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
  };

  const currentTheme = severityColors[event.severity.toLowerCase()] || severityColors.info;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col font-sans animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Terminal className="w-5 h-5 text-cyan-400 shrink-0" />
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-white m-0 truncate">Event Inspector</h2>
            <p className="text-[10px] font-mono text-slate-400 m-0 truncate">ID: {event.id}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold uppercase border ${currentTheme.bg} ${currentTheme.text} ${currentTheme.border}`}
          >
            {event.severity}
          </span>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-xs">
        {/* Event Message Banner */}
        <div className="bg-slate-900 border border-slate-800/80 rounded-xl p-3.5 space-y-1.5">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
            Log Message
          </span>
          <p className="font-mono text-xs text-white leading-relaxed m-0 break-words">
            {event.message}
          </p>
        </div>

        {/* General Telemetry Metadata */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono m-0">
            Telemetry Metadata
          </h3>
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl divide-y divide-slate-800/60 text-xs font-mono">
            <div className="flex items-center justify-between p-2.5">
              <span className="text-slate-400">Timestamp:</span>
              <span className="text-slate-200">{event.timestamp}</span>
            </div>

            <div className="flex items-center justify-between p-2.5">
              <span className="text-slate-400">Source Agent:</span>
              <span className="text-purple-300 font-medium">{event.source.toUpperCase()}</span>
            </div>

            <div className="flex items-center justify-between p-2.5">
              <span className="text-slate-400">Category:</span>
              <span className="text-cyan-300 font-medium">{event.category}</span>
            </div>

            <div className="flex items-center justify-between p-2.5">
              <span className="text-slate-400">Project ID:</span>
              <span className="text-slate-300 truncate max-w-[220px]">{event.project_id}</span>
            </div>

            {event.task_id && (
              <div className="flex items-center justify-between p-2.5">
                <span className="text-slate-400">Task ID:</span>
                <span className="text-amber-300 font-medium">{event.task_id}</span>
              </div>
            )}

            {event.trace_id && (
              <div className="flex items-center justify-between p-2.5">
                <span className="text-slate-400">Trace ID:</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-cyan-300">{event.trace_id}</span>
                  {onFilterByTrace && (
                    <button
                      onClick={() => onFilterByTrace(event.trace_id!)}
                      className="text-cyan-400 hover:text-cyan-300 underline text-[11px]"
                      title="Filter events by this trace"
                    >
                      Filter
                    </button>
                  )}
                </div>
              </div>
            )}

            {event.duration_ms !== null && event.duration_ms !== undefined && (
              <div className="flex items-center justify-between p-2.5">
                <span className="text-slate-400">Execution Duration:</span>
                <span className="text-emerald-400 font-bold">
                  {(event.duration_ms / 1000).toFixed(3)}s ({event.duration_ms} ms)
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Structured JSON Payload */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider font-mono m-0">
              Structured Payload & Attributes
            </h3>
            <button
              onClick={handleCopyJson}
              className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition"
            >
              {copiedJson ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copiedJson ? 'Copied' : 'Copy JSON'}</span>
            </button>
          </div>

          <div className="bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-[11px] overflow-x-auto max-h-64 text-slate-300">
            <pre className="m-0 whitespace-pre-wrap break-words">
              {JSON.stringify(event.payload || {}, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-3 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between gap-2">
        <button
          onClick={handleCopyId}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 font-medium transition"
        >
          {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copiedId ? 'ID Copied' : 'Copy Event ID'}</span>
        </button>

        {event.trace_id && onFilterByTrace && (
          <button
            onClick={() => onFilterByTrace(event.trace_id!)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs text-white font-medium shadow-md shadow-cyan-600/20 transition"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Trace All Related Events</span>
          </button>
        )}
      </div>
    </div>
  );
};

