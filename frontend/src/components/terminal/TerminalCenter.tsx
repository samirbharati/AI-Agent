import React, { useState, useEffect, useCallback } from 'react';
import type { Project, TerminalCommand, TerminalEventItem, TerminalProcess, TerminalSecurityStatus, TerminalSession } from '../../types';
import {
  clearTerminalSession,
  closeTerminalSession,
  connectTerminalStream,
  createTerminalSession,
  executeTerminalCommand,
  getTerminalHistory,
  getTerminalProcesses,
  getTerminalSecurityStatus,
  getTerminalSessions,
  interruptTerminalSession,
  stopTerminalProcess,
  updateTerminalSession,
} from '../../services/api';
import { TerminalHeader } from './TerminalHeader';
import { TerminalTabs } from './TerminalTabs';
import { TerminalConsole } from './TerminalConsole';
import { CommandInspectorDrawer } from './CommandInspectorDrawer';
import { CommandHistoryPanel } from './CommandHistoryPanel';
import { ProcessMonitorPanel } from './ProcessMonitorPanel';
import { SpecializedConsoleView } from './SpecializedConsoleView';
import { TerminalExportModal } from './TerminalExportModal';
import { SlidersHorizontal } from 'lucide-react';

interface TerminalCenterProps {
  project: Project | null;
  onOpenLogsCenter?: () => void;
  onOpenTraceLogs?: (traceId: string) => void;
}

export const TerminalCenter: React.FC<TerminalCenterProps> = ({
  project,
  onOpenTraceLogs,
}) => {
  const [sessions, setSessions] = useState<TerminalSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('');
  const [secondarySessionId, setSecondarySessionId] = useState<string | null>(null);
  const [isSplit, setIsSplit] = useState(false);
  const [activeEvents, setActiveEvents] = useState<TerminalEventItem[]>([]);
  const [secondaryEvents, setSecondaryEvents] = useState<TerminalEventItem[]>([]);

  const [processes, setProcesses] = useState<TerminalProcess[]>([]);
  const [history, setHistory] = useState<TerminalCommand[]>([]);
  const [securityStatus, setSecurityStatus] = useState<TerminalSecurityStatus | null>(null);

  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isProcessesOpen, setIsProcessesOpen] = useState(false);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [selectedCommand, setSelectedCommand] = useState<TerminalCommand | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSpecializedConsoles, setShowSpecializedConsoles] = useState(false);

  // Load sessions and security status
  const loadSessions = useCallback(async () => {
    try {
      const sess = await getTerminalSessions(project?.id);
      setSessions(sess);
      if (sess.length > 0 && (!activeSessionId || !sess.find((s) => s.id === activeSessionId))) {
        setActiveSessionId(sess[0].id);
      }
    } catch (e) {
      console.error('Failed to load terminal sessions:', e);
    }
  }, [project?.id, activeSessionId]);

  const loadProcessesAndHistory = useCallback(async () => {
    try {
      const [procs, hist, sec] = await Promise.all([
        getTerminalProcesses(project?.id),
        activeSessionId ? getTerminalHistory(activeSessionId, 50) : Promise.resolve([]),
        getTerminalSecurityStatus(),
      ]);
      setProcesses(procs);
      setHistory(hist);
      setSecurityStatus(sec);
    } catch (e) {
      console.error('Failed to load terminal telemetry:', e);
    }
  }, [project?.id, activeSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    loadProcessesAndHistory();
    const interval = setInterval(loadProcessesAndHistory, 5000);
    return () => clearInterval(interval);
  }, [loadProcessesAndHistory]);

  // Connect active session live stream
  useEffect(() => {
    if (!activeSessionId) return;
    setActiveEvents([]);

    const disconnect = connectTerminalStream(
      activeSessionId,
      (item) => {
        setActiveEvents((prev) => [...prev, item]);
      },
      (err) => console.error('Active terminal stream error:', err)
    );

    return () => disconnect();
  }, [activeSessionId]);

  // Connect secondary session stream if split
  useEffect(() => {
    if (!secondarySessionId || !isSplit) return;
    setSecondaryEvents([]);

    const disconnect = connectTerminalStream(
      secondarySessionId,
      (item) => {
        setSecondaryEvents((prev) => [...prev, item]);
      },
      (err) => console.error('Secondary terminal stream error:', err)
    );

    return () => disconnect();
  }, [secondarySessionId, isSplit]);

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;
  const secondarySession = sessions.find((s) => s.id === secondarySessionId) || null;
  const hasRunningProcess = processes.some((p) => p.session_id === activeSessionId && p.status === 'running');

  // Command execution handler
  const handleExecute = async (commandStr: string, targetSessionId = activeSessionId) => {
    if (!targetSessionId) return;
    try {
      await executeTerminalCommand(targetSessionId, { command: commandStr });
      loadProcessesAndHistory();
    } catch (e: any) {
      setActiveEvents((prev) => [
        ...prev,
        {
          type: 'error',
          data: `[ERROR] Execution rejected: ${e.message || e}\n`,
          sequence: Date.now(),
        },
      ]);
    }
  };

  const handleInterrupt = async (targetSessionId = activeSessionId) => {
    if (!targetSessionId) return;
    try {
      await interruptTerminalSession(targetSessionId);
      loadProcessesAndHistory();
    } catch (e) {
      console.error('Failed to interrupt process:', e);
    }
  };

  const handleClear = async (targetSessionId = activeSessionId) => {
    if (!targetSessionId) return;
    try {
      await clearTerminalSession(targetSessionId);
      if (targetSessionId === activeSessionId) setActiveEvents([]);
      if (targetSessionId === secondarySessionId) setSecondaryEvents([]);
    } catch (e) {
      console.error('Failed to clear terminal:', e);
    }
  };

  const handleCreateSession = async () => {
    if (!project) return;
    const name = `Terminal ${sessions.length + 1}`;
    try {
      const s = await createTerminalSession({ project_id: project.id, name });
      setSessions((prev) => [...prev, s]);
      setActiveSessionId(s.id);
    } catch (e) {
      console.error('Failed to create session:', e);
    }
  };

  const handleCloseSession = async (id: string) => {
    try {
      await closeTerminalSession(id);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSessionId === id && remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
      }
      if (secondarySessionId === id) {
        setSecondarySessionId(null);
        setIsSplit(false);
      }
    } catch (e) {
      console.error('Failed to close session:', e);
    }
  };

  const handleRenameSession = async (id: string, name: string) => {
    try {
      const updated = await updateTerminalSession(id, { name });
      setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch (e) {
      console.error('Failed to rename session:', e);
    }
  };

  const handleStopProcess = async (pid: number) => {
    try {
      await stopTerminalProcess(pid);
      loadProcessesAndHistory();
    } catch (e) {
      console.error('Failed to stop process:', e);
    }
  };

  const handleCopyOutput = () => {
    const text = activeEvents.map((e) => e.data).join('');
    navigator.clipboard.writeText(text);
  };

  return (
    <div
      className={`flex flex-col bg-[#07090D] border border-[#1E293B] shadow-2xl overflow-hidden ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : 'h-[calc(100vh-8rem)] rounded-xl my-4 mx-6'
      }`}
    >
      {/* Header */}
      <TerminalHeader
        project={project}
        activeSession={activeSession}
        runningProcessCount={processes.filter((p) => p.status === 'running').length}
        securityStatus={securityStatus}
        onNewTerminal={handleCreateSession}
        onSplitTerminal={() => {
          if (!isSplit && sessions.length > 1) {
            const other = sessions.find((s) => s.id !== activeSessionId);
            setSecondarySessionId(other ? other.id : sessions[0].id);
            setIsSplit(true);
          } else {
            setIsSplit(!isSplit);
          }
        }}
        isSplit={isSplit}
        onClearTerminal={() => handleClear(activeSessionId)}
        onRestartSession={() => handleClear(activeSessionId)}
        onStopProcess={() => {
          const runP = processes.find((p) => p.session_id === activeSessionId && p.status === 'running');
          if (runP) handleStopProcess(runP.process_id);
          else handleInterrupt(activeSessionId);
        }}
        hasRunningProcess={hasRunningProcess}
        onCopyOutput={handleCopyOutput}
        onOpenExport={() => setIsExportOpen(true)}
        onToggleFullscreen={() => setIsFullscreen(!isFullscreen)}
        isFullscreen={isFullscreen}
        onToggleHistory={() => setIsHistoryOpen(!isHistoryOpen)}
        isHistoryOpen={isHistoryOpen}
        onToggleProcesses={() => setIsProcessesOpen(!isProcessesOpen)}
        isProcessesOpen={isProcessesOpen}
      />

      {/* Tabs */}
      <div className="flex items-center justify-between bg-[#07090D] border-b border-[#1E293B] pr-3">
        <TerminalTabs
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={setActiveSessionId}
          onCloseSession={handleCloseSession}
          onRenameSession={handleRenameSession}
          onNewSession={handleCreateSession}
        />

        <button
          onClick={() => setShowSpecializedConsoles(!showSpecializedConsoles)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-semibold transition border ${
            showSpecializedConsoles
              ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border-slate-800'
          }`}
          title="Toggle Build/QA/Security/Git Specialized Consoles"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Specialized Consoles</span>
        </button>
      </div>

      {/* Main Terminal Viewport (Single or Split) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Primary Console */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <TerminalConsole
            session={activeSession}
            events={activeEvents}
            onExecuteCommand={(cmd) => handleExecute(cmd, activeSessionId)}
            onInterrupt={() => handleInterrupt(activeSessionId)}
            isRunning={hasRunningProcess}
          />
        </div>

        {/* Secondary Console if Split */}
        {isSplit && (
          <div className="flex-1 flex flex-col border-l border-[#1E293B] overflow-hidden">
            <TerminalConsole
              session={secondarySession}
              events={secondaryEvents}
              onExecuteCommand={(cmd) => handleExecute(cmd, secondarySessionId || undefined)}
              onInterrupt={() => secondarySessionId && handleInterrupt(secondarySessionId)}
              isRunning={processes.some((p) => p.session_id === secondarySessionId && p.status === 'running')}
            />
          </div>
        )}
      </div>

      {/* Specialized Console Drawer (Collapsible bottom panel) */}
      {showSpecializedConsoles && (
        <div className="h-64 border-t border-[#1E293B]">
          <SpecializedConsoleView
            projectId={project?.id || null}
            onInspectCommand={(cmd) => setSelectedCommand(cmd)}
            onReExecute={(cmd) => handleExecute(cmd, activeSessionId)}
          />
        </div>
      )}

      {/* Drawers and Modals */}
      <CommandInspectorDrawer
        command={selectedCommand}
        isOpen={Boolean(selectedCommand)}
        onClose={() => setSelectedCommand(null)}
        onOpenTraceLogs={onOpenTraceLogs}
      />

      <CommandHistoryPanel
        history={history}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectCommand={(cmd) => setSelectedCommand(cmd)}
        onReExecuteCommand={(cmdStr) => handleExecute(cmdStr, activeSessionId)}
        onRefreshHistory={loadProcessesAndHistory}
      />

      <ProcessMonitorPanel
        processes={processes}
        isOpen={isProcessesOpen}
        onClose={() => setIsProcessesOpen(false)}
        onStopProcess={handleStopProcess}
        onRefresh={loadProcessesAndHistory}
      />

      <TerminalExportModal
        sessionId={activeSessionId}
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
      />
    </div>
  );
};

