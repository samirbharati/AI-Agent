import React, { useEffect, useState, useCallback } from 'react';
import {
  ShieldCheck,
  Users,
  ShieldAlert,
  Bug,
  FileText,
} from 'lucide-react';
import type {
  Project,
  QualityGateResult,
  QualityCertificationReport,
  LoadTestStageResult,
  BugRecord,
} from '../../types';
import {
  runQualityAudit,
  getLatestQualityGates,
  getLoadTestRuns,
  runLoadTest,
  getQualityBugs,
  recordBugRepair,
  getQualityReports,
} from '../../services/api';
import { QualityOverviewPanel } from './QualityOverviewPanel';
import { LoadTestingPanel } from './LoadTestingPanel';
import { SecurityBreakerPanel } from './SecurityBreakerPanel';
import { BugLifecyclePanel } from './BugLifecyclePanel';
import { QualityReportsPanel } from './QualityReportsPanel';

interface ProductQualityCenterProps {
  project: Project | null;
}

export const ProductQualityCenter: React.FC<ProductQualityCenterProps> = ({ project }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'load' | 'security' | 'bugs' | 'reports'>('overview');
  const [report, setReport] = useState<QualityCertificationReport | null>(null);
  const [gates, setGates] = useState<QualityGateResult[]>([]);
  const [loadStages, setLoadStages] = useState<LoadTestStageResult[]>([]);
  const [bugs, setBugs] = useState<BugRecord[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [isRunningAudit, setIsRunningAudit] = useState(false);
  const [isRunningLoad, setIsRunningLoad] = useState(false);

  const loadData = useCallback(async () => {
    if (!project) return;
    try {
      const [g, l, b, r] = await Promise.all([
        getLatestQualityGates(project.id).catch(() => []),
        getLoadTestRuns(project.id).catch(() => []),
        getQualityBugs(project.id).catch(() => []),
        getQualityReports(project.id).catch(() => []),
      ]);
      setGates(g);
      setLoadStages(l);
      setBugs(b);
      setReports(r);
    } catch (err) {
      console.error('Failed loading quality center data:', err);
    }
  }, [project]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunAudit = async () => {
    if (!project) return;
    setIsRunningAudit(true);
    try {
      const res = await runQualityAudit(project.id, {
        run_load_test: true,
        max_load_stages: 3,
      });
      setReport(res);
      await loadData();
    } catch (err) {
      console.error('Audit failed:', err);
    } finally {
      setIsRunningAudit(false);
    }
  };

  const handleRunLoadTest = async (testPath: string, maxStages: number) => {
    if (!project) return;
    setIsRunningLoad(true);
    try {
      const stages = await runLoadTest(project.id, { test_path: testPath, max_stages: maxStages });
      setLoadStages(stages);
      await loadData();
    } catch (err) {
      console.error('Load test failed:', err);
    } finally {
      setIsRunningLoad(false);
    }
  };

  const handleRecordRepair = async (
    bugId: string,
    fixSummary: string,
    retestPassed: boolean,
    evidence: string
  ) => {
    if (!project) return;
    await recordBugRepair(project.id, bugId, {
      fix_summary: fixSummary,
      retest_passed: retestPassed,
      verification_evidence: evidence,
    });
    await loadData();
  };

  if (!project) {
    return (
      <div className="min-h-[500px] flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-2xl p-8 text-center bg-[#0D1320]">
        <ShieldCheck className="w-12 h-12 text-slate-500 mb-3" />
        <h3 className="text-lg font-bold text-white mb-1">No Project Selected</h3>
        <p className="text-sm text-slate-400 max-w-sm">
          Select or create a project to access the Product Quality & Reliability Engineering Center.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Navigation Sub-Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#1E293B] pb-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white leading-tight">Product Quality Center</h2>
            <p className="text-[11px] text-slate-400 font-mono">
              Project: <span className="text-cyan-400 font-bold">{project.name}</span>
            </p>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 bg-[#0D1320] p-1 border border-[#1E293B] rounded-xl text-xs font-mono">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition ${
              activeTab === 'overview'
                ? 'bg-emerald-600 text-white font-bold shadow-md shadow-emerald-600/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Overview & 10 Gates</span>
          </button>

          <button
            onClick={() => setActiveTab('load')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition ${
              activeTab === 'load'
                ? 'bg-cyan-600 text-white font-bold shadow-md shadow-cyan-600/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Load & Concurrency</span>
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition ${
              activeTab === 'security'
                ? 'bg-rose-600 text-white font-bold shadow-md shadow-rose-600/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Security Breaker</span>
          </button>

          <button
            onClick={() => setActiveTab('bugs')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition ${
              activeTab === 'bugs'
                ? 'bg-amber-600 text-white font-bold shadow-md shadow-amber-600/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Bug className="w-3.5 h-3.5" />
            <span>Defect Lifecycle</span>
          </button>

          <button
            onClick={() => setActiveTab('reports')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition ${
              activeTab === 'reports'
                ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-600/20'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Certification Reports</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      {activeTab === 'overview' && (
        <QualityOverviewPanel
          report={report}
          gates={gates}
          isRunning={isRunningAudit}
          onRunAudit={handleRunAudit}
        />
      )}

      {activeTab === 'load' && (
        <LoadTestingPanel
          loadStages={loadStages}
          isRunning={isRunningLoad}
          onRunLoadTest={handleRunLoadTest}
        />
      )}

      {activeTab === 'security' && (
        <SecurityBreakerPanel securitySummary={report?.security_summary || null} />
      )}

      {activeTab === 'bugs' && (
        <BugLifecyclePanel
          bugs={bugs}
          onRecordRepair={handleRecordRepair}
        />
      )}

      {activeTab === 'reports' && (
        <QualityReportsPanel projectId={project.id} reports={reports} />
      )}
    </div>
  );
};
