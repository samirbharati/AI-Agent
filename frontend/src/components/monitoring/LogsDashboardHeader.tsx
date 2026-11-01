import React from 'react';
import { Activity, CheckCircle2, AlertTriangle, AlertCircle, ShieldAlert, Users, Layers, Cpu, Database, Server } from 'lucide-react';
import type { MonitoringStats, SystemHealth } from '../../types';

interface LogsDashboardHeaderProps {
  stats: MonitoringStats | null;
  health: SystemHealth | null;
  selectedProjectId?: string;
  projectName?: string;
  isStreamConnected: boolean;
}

export const LogsDashboardHeader: React.FC<LogsDashboardHeaderProps> = ({
  stats,
  health,
  projectName,
  isStreamConnected,
}) => {
  const ollamaOk = health?.ollama?.status === 'available' && health?.ollama?.model_available;

  return (
    <div className="space-y-4">
      {/* Title & Status Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2 m-0">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]"></span>
              System Intelligence & Logs
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-medium bg-slate-800 text-cyan-300 border border-slate-700/80">
              SOC / Observability Command Center
            </span>
            {projectName && (
              <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-purple-950/60 text-purple-300 border border-purple-800/60">
                Scope: {projectName}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 m-0">
            Real-time visibility into AI agents, executions, development operations, testing, and security events.
          </p>
        </div>

        {/* Telemetry Health Badges */}
        <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
          {/* Live Stream Status */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <span
              className={`w-2 h-2 rounded-full ${
                isStreamConnected ? 'bg-emerald-400 shadow-[0_0_6px_#22c55e]' : 'bg-amber-400 animate-ping'
              }`}
            />
            <span>{isStreamConnected ? 'SSE Live' : 'Reconnecting...'}</span>
          </div>

          {/* Backend Online */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Server className="w-3.5 h-3.5 text-cyan-400" />
            <span>Backend Online</span>
          </div>

          {/* Database */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>SQLite Async</span>
          </div>

          {/* Ollama Local */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-slate-200">{health?.ollama?.configured_model || 'qwen2.5-coder:7b'}</span>
            {ollamaOk ? (
              <span className="text-emerald-400 font-medium">Ready</span>
            ) : (
              <span className="text-amber-400 font-medium">Offline</span>
            )}
          </div>

          {/* Active Workflows */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Layers className="w-3.5 h-3.5 text-amber-400" />
            <span>Workflows: <strong className="text-white">{stats?.active_workflows ?? 0}</strong></span>
          </div>
        </div>
      </div>

      {/* 6 SOC Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Total Events */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3.5 shadow-sm hover:border-slate-700 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Events</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white mt-1.5">
            {stats?.total_events.toLocaleString() ?? 0}
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-1 m-0">All recorded operations</p>
        </div>

        {/* Successful Operations */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3.5 shadow-sm hover:border-emerald-900/50 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-emerald-400">Success</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-300 mt-1.5">
            {stats?.successful_operations.toLocaleString() ?? 0}
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-1 m-0">Tasks, builds & tests</p>
        </div>

        {/* Warnings */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3.5 shadow-sm hover:border-amber-900/50 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-amber-400">Warnings</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300 mt-1.5">
            {stats?.warnings.toLocaleString() ?? 0}
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-1 m-0">Non-fatal warnings</p>
        </div>

        {/* Errors */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3.5 shadow-sm hover:border-rose-900/50 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-rose-400">Errors</span>
            <AlertCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-300 mt-1.5">
            {stats?.errors.toLocaleString() ?? 0}
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-1 m-0">Task & agent failures</p>
        </div>

        {/* Critical Events */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3.5 shadow-sm hover:border-red-800 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-red-400 font-semibold">Critical Events</span>
            <ShieldAlert className="w-4 h-4 text-red-400 animate-pulse" />
          </div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1.5">
            {stats?.critical_events.toLocaleString() ?? 0}
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-1 m-0">High-severity alerts</p>
        </div>

        {/* Active Agents */}
        <div className="bg-slate-900/90 border border-slate-800/80 rounded-xl p-3.5 shadow-sm hover:border-purple-900/50 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-purple-400">Active Agents</span>
            <Users className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-300 mt-1.5">
            {stats?.active_agents ?? 0}
          </div>
          <p className="text-[10px] text-slate-500 font-mono mt-1 m-0">Inference or tool use</p>
        </div>
      </div>
    </div>
  );
};

