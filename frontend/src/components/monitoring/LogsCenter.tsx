import React, { useEffect, useState, useCallback } from 'react';
import {
  Terminal,
  Cpu,
  Users,
  ShieldCheck,
  Bug,
  Clock,
  Activity,
} from 'lucide-react';
import {
  getMonitoringEvents,
  getMonitoringStats,
  getAgentMonitoringStates,
  getLLMRequests,
  getToolExecutions,
  getIncidents,
  getMonitoringSecurityEvents,
  connectMonitoringStream,
} from '../../services/api';
import type {
  MonitoringEvent,
  MonitoringStats,
  AgentMonitoringState,
  LLMIntelligenceReport,
  ToolExecutionRecord,
  IncidentRecord,
  SecurityFinding,
  Project,
  SystemHealth,
} from '../../types';
import { LogsDashboardHeader } from './LogsDashboardHeader';
import { LogFilterPanel, type FilterState } from './LogFilterPanel';
import { LiveTerminal } from './LiveTerminal';
import { EventDetailDrawer } from './EventDetailDrawer';
import { AgentActivityGrid } from './AgentActivityGrid';
import { LLMMonitorPanel } from './LLMMonitorPanel';
import { ToolExecutionTable } from './ToolExecutionTable';
import { IncidentMonitor } from './IncidentMonitor';
import { SecurityEventPanel } from './SecurityEventPanel';
import { WorkflowTimeline } from './WorkflowTimeline';
import { LogExportModal } from './LogExportModal';

interface LogsCenterProps {
  projects: Project[];
  selectedProject: Project | null;
  health: SystemHealth | null;
}

export const LogsCenter: React.FC<LogsCenterProps> = ({
  projects,
  selectedProject,
  health,
}) => {
  // Navigation sub-tab
  const [activeTab, setActiveTab] = useState<
    'terminal' | 'agents' | 'llm' | 'tools' | 'incidents' | 'security' | 'timeline'
  >('terminal');

  // Core Data States
  const [events, setEvents] = useState<MonitoringEvent[]>([]);
  const [stats, setStats] = useState<MonitoringStats | null>(null);
  const [agents, setAgents] = useState<AgentMonitoringState[]>([]);
  const [llmReport, setLlmReport] = useState<LLMIntelligenceReport | null>(null);
  const [tools, setTools] = useState<ToolExecutionRecord[]>([]);
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [securityFindings, setSecurityFindings] = useState<SecurityFinding[]>([]);

  // UI Interactive States
  const [selectedEvent, setSelectedEvent] = useState<MonitoringEvent | null>(null);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [isStreamConnected, setIsStreamConnected] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  // Filter State
  const [filters, setFilters] = useState<FilterState>({
    severity: 'all',
    source: 'all',
    category: 'all',
    project_id: selectedProject?.id || 'all',
    time_range: 'all',
    status: 'all',
    search: '',
  });

  // Keep project_id in filters synchronized if selected project changes
  useEffect(() => {
    if (selectedProject?.id) {
      setFilters((prev) => ({ ...prev, project_id: selectedProject.id }));
    }
  }, [selectedProject?.id]);

  // Load events based on filters and pagination
  const loadEvents = useCallback(async () => {
    try {
      const res = await getMonitoringEvents({
        project_id: filters.project_id,
        severity: filters.severity,
        source: filters.source,
        category: filters.category,
        status: filters.status,
        search: filters.search,
        time_range: filters.time_range,
        page,
        page_size: 50,
      });
      setEvents(res.items);
      setTotalPages(res.total_pages);
      setTotalRecords(res.total);
    } catch (err) {
      console.error('Failed to load monitoring events:', err);
    }
  }, [filters, page]);

  // Load high-level stats and sub-panel data
  const loadSubsystemData = useCallback(async () => {
    const pid = filters.project_id;
    try {
      const [statsRes, agentsRes, llmRes, toolsRes, incRes, secRes] = await Promise.allSettled([
        getMonitoringStats(pid),
        getAgentMonitoringStates(pid),
        getLLMRequests(pid),
        getToolExecutions(pid),
        getIncidents(pid),
        getMonitoringSecurityEvents(pid),
      ]);

      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (agentsRes.status === 'fulfilled') setAgents(agentsRes.value);
      if (llmRes.status === 'fulfilled') setLlmReport(llmRes.value);
      if (toolsRes.status === 'fulfilled') setTools(toolsRes.value);
      if (incRes.status === 'fulfilled') setIncidents(incRes.value);
      if (secRes.status === 'fulfilled') setSecurityFindings(secRes.value);
    } catch (err) {
      console.error('Failed to load subsystem data:', err);
    }
  }, [filters.project_id]);

  // Fetch data on filter or page change
  useEffect(() => {
    loadEvents();
  }, [loadEvents]);

  useEffect(() => {
    loadSubsystemData();
    const interval = setInterval(loadSubsystemData, 8000);
    return () => clearInterval(interval);
  }, [loadSubsystemData]);

  // Connect live monitoring SSE stream
  useEffect(() => {
    const disconnect = connectMonitoringStream(
      (newEvent) => {
        setIsStreamConnected(true);
        // Prepend new event if on page 1 and no search filter
        setEvents((prev) => {
          if (prev.some((e) => e.id === newEvent.id)) return prev;
          return [newEvent, ...prev.slice(0, 49)];
        });
        setTotalRecords((prev) => prev + 1);
      },
      () => {
        setIsStreamConnected(false);
      },
      filters.project_id
    );

    setIsStreamConnected(true);
    return () => disconnect();
  }, [filters.project_id]);

  const handleClearFilters = () => {
    setFilters({
      severity: 'all',
      source: 'all',
      category: 'all',
      project_id: selectedProject?.id || 'all',
      time_range: 'all',
      status: 'all',
      search: '',
    });
    setPage(1);
  };

  const handleFilterByTrace = (traceId: string) => {
    setFilters((prev) => ({ ...prev, search: traceId }));
    setActiveTab('terminal');
    setSelectedEvent(null);
  };

  const handleSelectTimelineStage = (category: string) => {
    setFilters((prev) => ({ ...prev, category }));
    setActiveTab('terminal');
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-200">
      {/* 1. Header & System Health Status */}
      <LogsDashboardHeader
        stats={stats}
        health={health}
        projectName={selectedProject?.name}
        isStreamConnected={isStreamConnected}
      />

      {/* 2. Command Center Sub-Navigation Tabs */}
      <div className="flex items-center gap-1.5 p-1 bg-slate-900/90 border border-slate-800 rounded-xl overflow-x-auto text-xs font-mono">
        <button
          onClick={() => setActiveTab('terminal')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'terminal'
              ? 'bg-cyan-600 text-white font-bold shadow-md shadow-cyan-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Live Terminal</span>
        </button>

        <button
          onClick={() => setActiveTab('agents')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'agents'
              ? 'bg-purple-600 text-white font-bold shadow-md shadow-purple-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Agent Operations ({agents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('llm')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'llm'
              ? 'bg-indigo-600 text-white font-bold shadow-md shadow-indigo-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>LLM Intelligence</span>
        </button>

        <button
          onClick={() => setActiveTab('tools')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'tools'
              ? 'bg-teal-600 text-white font-bold shadow-md shadow-teal-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Tool Activity ({tools.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('incidents')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'incidents'
              ? 'bg-rose-600 text-white font-bold shadow-md shadow-rose-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Bug className="w-3.5 h-3.5" />
          <span>Incidents ({incidents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('security')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'security'
              ? 'bg-amber-600 text-white font-bold shadow-md shadow-amber-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Security Audit ({securityFindings.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition shrink-0 ${
            activeTab === 'timeline'
              ? 'bg-blue-600 text-white font-bold shadow-md shadow-blue-600/20'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Workflow Timeline</span>
        </button>
      </div>

      {/* 3. Tab Content Panes */}
      {activeTab === 'terminal' && (
        <div className="space-y-4">
          <LogFilterPanel
            filters={filters}
            onChange={(f) => {
              setFilters(f);
              setPage(1);
            }}
            onClear={handleClearFilters}
            onExport={() => setIsExportModalOpen(true)}
            projects={projects}
          />

          <LiveTerminal
            events={events}
            selectedEvent={selectedEvent}
            onSelectEvent={(e) => setSelectedEvent(e)}
            page={page}
            totalPages={totalPages}
            onPageChange={(p) => setPage(p)}
            totalEvents={totalRecords}
            isStreaming={isStreamConnected}
          />
        </div>
      )}

      {activeTab === 'agents' && <AgentActivityGrid agents={agents} />}

      {activeTab === 'llm' && (
        <LLMMonitorPanel
          report={llmReport}
          onRefresh={loadSubsystemData}
        />
      )}

      {activeTab === 'tools' && <ToolExecutionTable tools={tools} />}

      {activeTab === 'incidents' && <IncidentMonitor incidents={incidents} />}

      {activeTab === 'security' && <SecurityEventPanel findings={securityFindings} />}

      {activeTab === 'timeline' && (
        <WorkflowTimeline
          currentStatus={selectedProject?.status || 'pending'}
          onSelectStage={handleSelectTimelineStage}
        />
      )}

      {/* 4. Event Detail Right-Side Drawer */}
      <EventDetailDrawer
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
        onFilterByTrace={handleFilterByTrace}
      />

      {/* 5. Log Export Dialog */}
      <LogExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        filters={filters}
      />
    </div>
  );
};

