import React, { useEffect, useState } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Bug,
  Play,
  RefreshCw,
  Search,
} from 'lucide-react';
import type { QATestResult, SecurityScanReport } from '../types';
import {
  getDetectedSecurityTools,
  runProjectTests,
  scanProjectSecurity,
} from '../services/api';

interface QASecurityPanelProps {
  projectId: string;
}

export const QASecurityPanel: React.FC<QASecurityPanelProps> = ({ projectId }) => {
  const [activeTab, setActiveTab] = useState<'security' | 'qa'>('security');
  const [securityReport, setSecurityReport] = useState<SecurityScanReport | null>(null);
  const [detectedTools, setDetectedTools] = useState<Record<string, any>>({});
  const [qaResult, setQaResult] = useState<QATestResult | null>(null);
  const [loadingScan, setLoadingScan] = useState(false);
  const [loadingQA, setLoadingQA] = useState(false);

  const loadData = async () => {
    if (!projectId) return;
    try {
      const [toolsRes, scanRes] = await Promise.allSettled([
        getDetectedSecurityTools(),
        scanProjectSecurity(projectId),
      ]);

      if (toolsRes.status === 'fulfilled') {
        setDetectedTools(toolsRes.value.tools);
      }
      if (scanRes.status === 'fulfilled') {
        setSecurityReport(scanRes.value);
      }
    } catch (e) {
      console.error('Failed to load QA/Security data:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleRunSecurityScan = async () => {
    setLoadingScan(true);
    try {
      const report = await scanProjectSecurity(projectId);
      setSecurityReport(report);
    } catch (e) {
      console.error('Security scan failed:', e);
    } finally {
      setLoadingScan(false);
    }
  };

  const handleRunQATests = async () => {
    setLoadingQA(true);
    try {
      const res = await runProjectTests(projectId);
      setQaResult(res);
    } catch (e) {
      console.error('QA test run failed:', e);
    } finally {
      setLoadingQA(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col h-[460px]">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 mb-3 gap-2">
        <div className="flex items-center gap-2">
          {activeTab === 'security' ? (
            <Shield className="w-4 h-4 text-rose-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          )}
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 m-0">
            {activeTab === 'security' ? 'Security Audit & Vulnerabilities' : 'QA Automated Test Verification'}
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {/* Tab selector */}
          <div className="flex rounded-lg bg-slate-800 border border-slate-700 p-0.5 text-xs font-medium">
            <button
              onClick={() => setActiveTab('security')}
              className={`px-3 py-1 rounded transition flex items-center gap-1.5 ${
                activeTab === 'security'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Security Scan</span>
              {securityReport && securityReport.critical_count + securityReport.high_count > 0 && (
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              )}
            </button>
            <button
              onClick={() => setActiveTab('qa')}
              className={`px-3 py-1 rounded transition flex items-center gap-1.5 ${
                activeTab === 'qa'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Automated QA</span>
            </button>
          </div>

          {/* Trigger button */}
          {activeTab === 'security' ? (
            <button
              onClick={handleRunSecurityScan}
              disabled={loadingScan}
              className="flex items-center gap-1 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2.5 py-1 rounded-lg transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${loadingScan ? 'animate-spin text-indigo-400' : ''}`} />
              <span>{loadingScan ? 'Scanning...' : 'Rescan'}</span>
            </button>
          ) : (
            <button
              onClick={handleRunQATests}
              disabled={loadingQA}
              className="flex items-center gap-1 text-xs bg-emerald-600 hover:bg-emerald-500 text-white px-2.5 py-1 rounded-lg transition disabled:opacity-50 font-medium"
            >
              <Play className={`w-3 h-3 fill-white ${loadingQA ? 'animate-pulse' : ''}`} />
              <span>{loadingQA ? 'Running...' : 'Run Pytest'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Security Tab */}
      {activeTab === 'security' && (
        <div className="flex-1 flex flex-col gap-3 overflow-hidden">
          {/* Tools status bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-mono text-[11px]">Scanners:</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Built-in AST/Regex
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                  detectedTools?.semgrep?.installed
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-500 border-slate-700'
                }`}
              >
                Semgrep {detectedTools?.semgrep?.installed ? '✓' : '(Not installed)'}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                  detectedTools?.gitleaks?.installed
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-slate-800 text-slate-500 border-slate-700'
                }`}
              >
                Gitleaks {detectedTools?.gitleaks?.installed ? '✓' : '(Not installed)'}
              </span>
            </div>

            {/* Verdict */}
            {securityReport && (
              <div className="flex items-center gap-1.5 text-xs font-semibold">
                {securityReport.passed ? (
                  <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    <ShieldCheck className="w-3.5 h-3.5" /> Clean (0 Critical/High)
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                    <ShieldAlert className="w-3.5 h-3.5" /> {securityReport.critical_count} Critical,{' '}
                    {securityReport.high_count} High
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Findings List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {!securityReport || securityReport.findings.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs text-center p-6">
                <ShieldCheck className="w-8 h-8 text-emerald-500/50 mb-2" />
                <p className="m-0 font-medium text-slate-300">No Security Vulnerabilities Detected</p>
                <p className="m-0 text-slate-500 text-[11px] mt-1">
                  Deterministic secret scanning and OWASP pattern analysis passed with 0 findings.
                </p>
              </div>
            ) : (
              securityReport.findings.map((f) => (
                <div
                  key={f.id}
                  className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                    f.severity === 'critical'
                      ? 'bg-rose-500/5 border-rose-500/30'
                      : f.severity === 'high'
                      ? 'bg-amber-500/5 border-amber-500/30'
                      : 'bg-slate-800/40 border-slate-800'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded ${
                          f.severity === 'critical'
                            ? 'bg-rose-500/20 text-rose-400'
                            : 'bg-amber-500/20 text-amber-400'
                        }`}
                      >
                        {f.severity}
                      </span>
                      <span className="font-semibold text-white">{f.title}</span>
                      <span className="text-[10px] text-slate-500 font-mono">({f.rule_id})</span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      {f.file_path}
                      {f.line_number ? `:${f.line_number}` : ''}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-300 m-0 leading-relaxed">{f.description}</p>

                  {f.evidence && (
                    <div className="bg-slate-950 p-2 rounded text-[11px] font-mono text-rose-300 border border-slate-800">
                      <code>{f.evidence}</code>
                    </div>
                  )}

                  <div className="text-[11px] text-emerald-400 font-medium pt-1 border-t border-slate-800/60">
                    💡 Remediation: {f.remediation}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* QA Tab */}
      {activeTab === 'qa' && (
        <div className="flex-1 flex flex-col gap-3 overflow-hidden">
          {/* Status summary */}
          <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs">
            <div className="flex items-center gap-3 font-mono text-[11px]">
              <span>Status: <strong className="text-white uppercase">{qaResult?.status || 'Awaiting run'}</strong></span>
              {qaResult && (
                <>
                  <span className="text-emerald-400">Passed: {qaResult.passed_count}</span>
                  <span className="text-rose-400">Failed: {qaResult.failed_count}</span>
                  <span className="text-slate-400">Time: {qaResult.duration_seconds}s</span>
                </>
              )}
            </div>

            {qaResult && (
              <span
                className={`px-2 py-0.5 rounded text-xs font-semibold flex items-center gap-1 border ${
                  qaResult.passed
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                }`}
              >
                {qaResult.passed ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                {qaResult.passed ? 'Suite Passed' : 'Tests Failed'}
              </span>
            )}
          </div>

          {/* Test Failures & Bugs */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {!qaResult ? (
              <div className="h-full flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs text-center p-6">
                <Search className="w-8 h-8 text-slate-600 mb-2" />
                <p className="m-0 font-medium text-slate-300">No Test Run Executed Yet</p>
                <p className="m-0 text-slate-500 text-[11px] mt-1">
                  Click &ldquo;Run Pytest&rdquo; to execute the automated test suite in the project workspace.
                </p>
              </div>
            ) : qaResult.bugs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs text-center p-6">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
                <p className="m-0 font-medium text-white">All Automated Tests Passing</p>
                <p className="m-0 text-slate-500 text-[11px] mt-1">
                  Zero regressions or broken assertions detected across all unit test fixtures.
                </p>
              </div>
            ) : (
              qaResult.bugs.map((bug) => (
                <div
                  key={bug.id}
                  className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/5 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <Bug className="w-3.5 h-3.5 text-rose-400" />
                      <span className="font-semibold text-white">{bug.title}</span>
                    </div>
                    <span className="text-[9px] uppercase font-bold px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400">
                      {bug.severity}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-300">
                    <strong>Expected:</strong> {bug.expected_result}
                  </div>
                  <div className="text-[11px] text-rose-300 font-mono">
                    <strong>Actual:</strong> {bug.actual_result}
                  </div>

                  {bug.steps_to_reproduce && bug.steps_to_reproduce.length > 0 && (
                    <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-800">
                      <strong>Repro:</strong> {bug.steps_to_reproduce.join(' → ')}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

