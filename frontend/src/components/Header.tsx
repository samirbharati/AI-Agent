import React from 'react';
import { Cpu, Plus, RefreshCw, Terminal, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Project, SystemHealth } from '../types';

interface HeaderProps {
  projects: Project[];
  selectedProject: Project | null;
  onSelectProject: (p: Project) => void;
  onOpenNewProject: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  health: SystemHealth | null;
}

export const Header: React.FC<HeaderProps> = ({
  projects,
  selectedProject,
  onSelectProject,
  onOpenNewProject,
  onRefresh,
  isRefreshing,
  health,
}) => {
  const ollamaOk = health?.ollama?.status === 'available' && health?.ollama?.model_available;

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30 px-6 py-3.5">
      <div className="flex flex-wrap items-center justify-between gap-4 max-w-7xl mx-auto">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Terminal className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-lg tracking-tight text-white m-0">AgentForge</h1>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 m-0">Autonomous Multi-Agent Software Development</p>
          </div>
        </div>

        {/* Project Selector & System Telemetry */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Health Pill */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="font-mono text-slate-300">
              {health?.ollama?.configured_model || 'qwen2.5-coder:7b'}
            </span>
            {ollamaOk ? (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Local Ollama
              </span>
            ) : (
              <span className="flex items-center gap-1 text-amber-400 font-medium">
                <AlertCircle className="w-3 h-3 text-amber-400" /> Ollama Offline
              </span>
            )}
          </div>

          {/* Project Dropdown */}
          <div className="relative">
            <select
              value={selectedProject?.id || ''}
              onChange={(e) => {
                const found = projects.find((p) => p.id === e.target.value);
                if (found) onSelectProject(found);
              }}
              className="bg-slate-800 border border-slate-700 text-slate-100 text-sm rounded-lg px-3 py-1.5 pr-8 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium max-w-[220px] truncate"
            >
              {projects.length === 0 && <option value="">No projects yet</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Refresh state"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-400' : ''}`} />
          </button>

          {/* New Project CTA */}
          <button
            onClick={onOpenNewProject}
            className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-3.5 py-1.5 rounded-lg shadow-md shadow-indigo-600/20 transition active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>
    </header>
  );
};
