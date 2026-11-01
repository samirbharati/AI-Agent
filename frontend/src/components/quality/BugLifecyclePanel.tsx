import React, { useState } from 'react';
import {
  Bug as BugIcon,
  AlertOctagon,
  Wrench,
} from 'lucide-react';
import type { BugRecord } from '../../types';

interface BugLifecyclePanelProps {
  bugs: BugRecord[];
  onRecordRepair: (
    bugId: string,
    fixSummary: string,
    retestPassed: boolean,
    evidence: string
  ) => Promise<void>;
}

export const BugLifecyclePanel: React.FC<BugLifecyclePanelProps> = ({
  bugs,
  onRecordRepair,
}) => {
  const [selectedBugId, setSelectedBugId] = useState<string | null>(null);
  const [fixSummary, setFixSummary] = useState('');
  const [retestPassed, setRetestPassed] = useState(true);
  const [evidence, setEvidence] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOpenRepairModal = (bug: BugRecord) => {
    setSelectedBugId(bug.id);
    setFixSummary('');
    setRetestPassed(true);
    setEvidence(`Verification executed via automated test on ${new Date().toISOString()}`);
  };

  const handleSubmitRepair = async () => {
    if (!selectedBugId || !fixSummary.trim()) return;
    setIsSubmitting(true);
    try {
      await onRecordRepair(selectedBugId, fixSummary, retestPassed, evidence);
      setSelectedBugId(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <BugIcon className="w-5 h-5 text-rose-400" />
              <h3 className="text-lg font-bold text-white tracking-tight">
                Defect Tracking & Automated Repair Lifecycle
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Discovered bugs are assigned for repair with regression verification. Max 3 repair attempts before human escalation.
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="px-2.5 py-1 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-bold">
              {bugs.filter((b) => b.status === 'open' || b.status === 'in_progress').length} Active
            </span>
            <span className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
              {bugs.filter((b) => b.status === 'blocked').length} Blocked
            </span>
            <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
              {bugs.filter((b) => b.status === 'verified').length} Verified
            </span>
          </div>
        </div>

        {bugs.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs font-mono">
            Zero defects currently recorded for this project.
          </div>
        ) : (
          <div className="space-y-3.5">
            {bugs.map((b) => {
              const isBlocked = b.status === 'blocked';
              const isVerified = b.status === 'verified';

              return (
                <div
                  key={b.id}
                  className={`border rounded-xl p-4 transition ${
                    isBlocked
                      ? 'border-amber-500/40 bg-amber-500/5'
                      : isVerified
                      ? 'border-emerald-500/30 bg-[#111827]/40'
                      : 'border-[#1E293B] bg-[#111827]'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-4 mb-2">
                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                            b.severity === 'critical'
                              ? 'bg-rose-500/20 text-rose-400'
                              : 'bg-amber-500/20 text-amber-400'
                          }`}
                        >
                          {b.severity}
                        </span>
                        <h4 className="text-sm font-semibold text-slate-200">{b.title}</h4>
                      </div>
                      <p className="text-xs text-slate-400">{b.description}</p>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className="text-[11px] font-mono text-slate-400 block">
                          Attempts: <strong className="text-cyan-400">{b.attempt_count}/3</strong>
                        </span>
                        <span
                          className={`text-[10px] font-mono uppercase font-bold ${
                            isBlocked ? 'text-amber-400' : isVerified ? 'text-emerald-400' : 'text-slate-400'
                          }`}
                        >
                          {b.status}
                        </span>
                      </div>

                      {!isVerified && (
                        <button
                          onClick={() => handleOpenRepairModal(b)}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-white font-mono text-xs flex items-center gap-1.5 transition"
                        >
                          <Wrench className="w-3.5 h-3.5" />
                          <span>Record Repair</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {isBlocked && (
                    <div className="mt-2.5 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center gap-2 text-xs font-mono text-amber-300">
                      <AlertOctagon className="w-4 h-4 text-amber-400 flex-shrink-0" />
                      <span>
                        Max repair attempts (3) exhausted without successful verification. Human intervention required.
                      </span>
                    </div>
                  )}

                  {b.fix_summary && (
                    <div className="mt-2 pt-2 border-t border-[#1E293B] text-xs font-mono text-slate-400">
                      <span className="text-slate-500">Last repair: </span>
                      <span className="text-slate-300">{b.fix_summary}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Repair Attempt Modal */}
      {selectedBugId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-[#0D1320] border border-[#1E293B] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Wrench className="w-4 h-4 text-indigo-400" />
              <span>Record Defect Repair & QA Retest</span>
            </h3>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Developer Fix Summary</label>
                <textarea
                  value={fixSummary}
                  onChange={(e) => setFixSummary(e.target.value)}
                  placeholder="Describe code changes made to eliminate the bug..."
                  className="w-full bg-[#111827] border border-[#1F2937] p-2.5 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                  rows={3}
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">QA Verification Retest Outcome</label>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer text-emerald-400">
                    <input
                      type="radio"
                      name="retestOutcome"
                      checked={retestPassed}
                      onChange={() => setRetestPassed(true)}
                    />
                    <span>PASSED (Bug Verified Fixed)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-rose-400">
                    <input
                      type="radio"
                      name="retestOutcome"
                      checked={!retestPassed}
                      onChange={() => setRetestPassed(false)}
                    />
                    <span>FAILED (Regression / Bug Persists)</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">QA Evidence / Test Logs</label>
                <input
                  type="text"
                  value={evidence}
                  onChange={(e) => setEvidence(e.target.value)}
                  className="w-full bg-[#111827] border border-[#1F2937] p-2 rounded-lg text-slate-200 focus:outline-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1E293B]">
              <button
                onClick={() => setSelectedBugId(null)}
                className="px-4 py-2 rounded-lg text-xs font-mono text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitRepair}
                disabled={isSubmitting || !fixSummary.trim()}
                className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-mono text-xs font-bold transition"
              >
                {isSubmitting ? 'Recording...' : 'Submit Verification'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
