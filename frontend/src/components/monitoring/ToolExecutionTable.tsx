import React from 'react';
import { Terminal, GitBranch, FileCode, Play, ShieldAlert } from 'lucide-react';
import type { ToolExecutionRecord } from '../../types';

interface ToolExecutionTableProps {
  tools: ToolExecutionRecord[];
}

export const ToolExecutionTable: React.FC<ToolExecutionTableProps> = ({ tools }) => {
  const getToolIcon = (name: string) => {
    const n = name.toLowerCase();
    if (n.includes('git')) return <GitBranch className="w-4 h-4 text-cyan-400" />;
    if (n.includes('file')) return <FileCode className="w-4 h-4 text-emerald-400" />;
    if (n.includes('security') || n.includes('scan')) return <ShieldAlert className="w-4 h-4 text-amber-400" />;
    return <Play className="w-4 h-4 text-purple-400" />;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-1 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono m-0 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            Execution & Tool Activity
          </h2>
          <p className="text-xs text-slate-400 m-0">
            Real process executions, file filesystem manipulations, Git operations, and automated test runners.
          </p>
        </div>
      </div>

      <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto max-h-[460px]">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-950/60 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800 sticky top-0">
              <tr>
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Tool / Op</th>
                <th className="py-2.5 px-3">Calling Agent</th>
                <th className="py-2.5 px-3">Command / Detail</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3">Exit Code</th>
                <th className="py-2.5 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {tools.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-10 text-slate-500">
                    No tool executions logged yet. Operations will appear here when agents run tests or git ops.
                  </td>
                </tr>
              ) : (
                tools.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-2 px-3 text-slate-400">
                      {new Date(t.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-2 px-3 font-semibold text-white flex items-center gap-2">
                      {getToolIcon(t.tool_name)}
                      <span>{t.tool_name}</span>
                    </td>
                    <td className="py-2 px-3 text-purple-300">
                      {t.calling_agent.toUpperCase()}
                    </td>
                    <td className="py-2 px-3 text-slate-300 max-w-xs truncate" title={t.message}>
                      {t.command ? (
                        <code className="text-[11px] bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 text-cyan-300">
                          {Array.isArray(t.command) ? t.command.join(' ') : String(t.command)}
                        </code>
                      ) : (
                        t.message
                      )}
                    </td>
                    <td className="py-2 px-3 text-emerald-400 font-bold">
                      {t.duration_ms !== null && t.duration_ms !== undefined
                        ? `${(t.duration_ms / 1000).toFixed(2)}s`
                        : '—'}
                    </td>
                    <td className="py-2 px-3">
                      {t.exit_code !== null && t.exit_code !== undefined ? (
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            t.exit_code === 0
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-900'
                              : 'bg-rose-950 text-rose-400 border border-rose-900'
                          }`}
                        >
                          code: {t.exit_code}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      <span className="text-[10px] font-bold uppercase text-slate-300">
                        {t.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

