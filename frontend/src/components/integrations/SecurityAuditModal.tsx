import React, { useState } from 'react';
import {
  X,
  Shield,
  Play,
  RotateCw,
  CheckCircle2,
  FileCode,
} from 'lucide-react';
import { runSecurityAudit } from '../../services/api';
import type { Project, SecurityAuditResult } from '../../types';

interface SecurityAuditModalProps {
  project: Project | null;
  isOpen: boolean;
  onClose: () => void;
}

export const SecurityAuditModal: React.FC<SecurityAuditModalProps> = ({
  project,
  isOpen,
  onClose,
}) => {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SecurityAuditResult | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'semgrep' | 'gitleaks' | 'trivy'>('all');

  if (!isOpen) return null;

  const handleStartAudit = async () => {
    if (!project) return;
    setRunning(true);
    try {
      const res = await runSecurityAudit(project.id);
      setResult(res);
    } catch (err) {
      console.error('Audit failed:', err);
    } finally {
      setRunning(false);
    }
  };

  const findings = result?.findings || [];
  const filteredFindings = findings.filter((f) => {
    if (activeTab === 'all') return true;
    return f.scanner === activeTab;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-3xl bg-[#0D1320] border border-[#1E293B] rounded-2xl shadow-2xl p-6 font-mono flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#1E293B]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide m-0">
                Security Scanner Suite (Semgrep, Gitleaks, Trivy)
              </h2>
              <p className="text-xs text-slate-400 m-0">
                Project: {project ? project.name : 'No project selected'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Controls & Summary Banner */}
        <div className="py-4 border-b border-[#1E293B] flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={handleStartAudit}
              disabled={running || !project}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs shadow-lg shadow-red-600/20 disabled:opacity-50 transition"
            >
              {running ? (
                <RotateCw className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4 fill-white" />
              )}
              <span>{running ? 'Scanning Workspace...' : 'Run Security Audit'}</span>
            </button>
          </div>

          {result && (
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                Total: <strong className="text-white">{result.total_findings}</strong>
              </span>
              <span className="px-2.5 py-1 rounded bg-red-950/40 border border-red-800 text-red-400 font-bold">
                Crit: {result.critical_count}
              </span>
              <span className="px-2.5 py-1 rounded bg-amber-950/40 border border-amber-800 text-amber-400 font-bold">
                High: {result.high_count}
              </span>
              <span className="px-2.5 py-1 rounded bg-blue-950/40 border border-blue-800 text-blue-400 font-bold">
                Med: {result.medium_count}
              </span>
            </div>
          )}
        </div>

        {/* Tab Filter */}
        <div className="flex border-b border-[#1E293B] bg-[#0A0E17] text-xs">
          {[
            { id: 'all', label: 'All Scanners' },
            { id: 'semgrep', label: 'Semgrep (SAST)' },
            { id: 'gitleaks', label: 'Gitleaks (Secrets)' },
            { id: 'trivy', label: 'Trivy (Dependencies)' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 font-semibold transition border-b-2 ${
                activeTab === tab.id
                  ? 'border-red-400 text-red-300 bg-[#0D1320]'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Findings List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#07090D]">
          {!result && !running && (
            <div className="text-center py-16 text-slate-500 text-xs">
              <Shield className="w-8 h-8 text-slate-600 mx-auto mb-2 opacity-50" />
              <p>Ready to audit project workspace.</p>
              <p className="text-[11px] text-slate-600 mt-1">
                Click &quot;Run Security Audit&quot; to execute static analysis, secret detection, and CVE checks.
              </p>
            </div>
          )}

          {running && (
            <div className="text-center py-16 text-slate-400 text-xs space-y-2">
              <RotateCw className="w-8 h-8 animate-spin text-red-400 mx-auto" />
              <p>Running multi-scanner analysis on project workspace...</p>
            </div>
          )}

          {result && filteredFindings.length === 0 && !running && (
            <div className="text-center py-16 text-emerald-400 text-xs">
              <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
              <p className="font-bold text-sm">Workspace Passed All Security Audits</p>
              <p className="text-slate-400 text-xs mt-1">
                No vulnerabilities, secrets, or vulnerable dependencies detected.
              </p>
            </div>
          )}

          {filteredFindings.map((f, idx) => (
            <div
              key={f.id || idx}
              className="p-3.5 rounded-lg bg-[#0D1320] border border-[#243044] hover:border-slate-600 transition space-y-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${
                      f.severity === 'critical'
                        ? 'bg-red-500/20 text-red-300 border-red-500/40'
                        : f.severity === 'high'
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : 'bg-blue-500/20 text-blue-300 border-blue-500/40'
                    }`}
                  >
                    {f.severity}
                  </span>
                  <span className="text-xs font-bold text-slate-100">{f.title}</span>
                </div>
                <span className="text-[10px] text-slate-500 uppercase px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                  {f.scanner}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed m-0">{f.description}</p>

              {f.file_path && (
                <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                  <FileCode className="w-3.5 h-3.5 text-slate-500" />
                  <span>
                    {f.file_path}
                    {f.line_number ? `:${f.line_number}` : ''}
                  </span>
                </div>
              )}

              {f.code_snippet && (
                <pre className="text-[11px] text-red-300 bg-red-950/20 p-2 rounded border border-red-950/40 font-mono overflow-x-auto whitespace-pre-wrap">
                  {f.code_snippet}
                </pre>
              )}

              {f.remediation && (
                <div className="text-[11px] text-emerald-400 bg-emerald-950/20 p-2 rounded border border-emerald-950/40">
                  <strong>Remediation:</strong> {f.remediation}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
