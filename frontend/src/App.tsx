import React, { useEffect, useState, useCallback } from 'react';
import {
  approveArchitecture,
  approveRequirements,
  createProject,
  getAgentRuns,
  getArtifacts,
  getHealth,
  getProjects,
  getTasks,
  getWorkflowStatus,
  resumeWorkflow,
  startWorkflow,
  connectWorkflowEvents,
} from './services/api';
import type {
  Artifact,
  AgentRun,
  Project,
  ProjectCreatePayload,
  SystemHealth,
  Task,
  WorkflowEvent,
} from './types';
import { Header } from './components/Header';
import { NewProjectModal } from './components/NewProjectModal';
import { StageProgress } from './components/StageProgress';
import { WorkflowControls } from './components/WorkflowControls';
import { AgentRoster } from './components/AgentRoster';
import { TaskBoard } from './components/TaskBoard';
import { LiveLogs } from './components/LiveLogs';
import { ArtifactViewer } from './components/ArtifactViewer';
import { WorkspaceExplorer } from './components/WorkspaceExplorer';
import { QASecurityPanel } from './components/QASecurityPanel';
import { LogsCenter } from './components/monitoring/LogsCenter';
import { TerminalCenter } from './components/terminal/TerminalCenter';
import { FolderGit2, Layers } from 'lucide-react';

export const App: React.FC = () => {
  const [viewMode, setViewMode] = useState<'workspace' | 'terminal' | 'monitoring'>('workspace');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [isStreamConnected, setIsStreamConnected] = useState(false);

  // Load system health
  const refreshHealth = useCallback(async () => {
    try {
      const h = await getHealth();
      setHealth(h);
    } catch (e) {
      console.error('Failed to load health:', e);
    }
  }, []);

  // Load project list
  const loadProjects = useCallback(async () => {
    try {
      const res = await getProjects();
      setProjects(res.projects);
      if (res.projects.length > 0 && !selectedProject) {
        setSelectedProject(res.projects[0]);
      }
    } catch (e) {
      console.error('Failed to load projects:', e);
    }
  }, [selectedProject]);

  // Load details for selected project
  const loadProjectDetails = useCallback(async (projectId: string) => {
    setIsRefreshing(true);
    try {
      const [tasksRes, artifactsRes, runsRes, statusRes] = await Promise.allSettled([
        getTasks(projectId),
        getArtifacts(projectId),
        getAgentRuns(projectId),
        getWorkflowStatus(projectId),
      ]);

      if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value.tasks);
      if (artifactsRes.status === 'fulfilled') setArtifacts(artifactsRes.value.artifacts);
      if (runsRes.status === 'fulfilled') setAgentRuns(runsRes.value.runs);
      if (statusRes.status === 'fulfilled') {
        setSelectedProject((prev) =>
          prev && prev.id === projectId ? { ...prev, status: statusRes.value.status } : prev
        );
      }
    } catch (e) {
      console.error('Failed to refresh project data:', e);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshHealth();
    loadProjects();
  }, [refreshHealth, loadProjects]);

  useEffect(() => {
    if (selectedProject?.id) {
      loadProjectDetails(selectedProject.id);

      // Connect SSE Live Stream
      const disconnect = connectWorkflowEvents(
        selectedProject.id,
        (evt) => {
          setIsStreamConnected(true);
          setEvents((prev) => [...prev, evt]);

          // Update status if event indicates a status transition
          if (evt.project_status) {
            setSelectedProject((prev) =>
              prev ? { ...prev, status: evt.project_status as any } : prev
            );
          }

          // Trigger data reload on significant milestones
          if (['agent_completed', 'status_changed', 'artifact_created'].includes(evt.event_type)) {
            loadProjectDetails(selectedProject.id);
          }
        },
        () => {
          setIsStreamConnected(true);
        },
        () => {
          setIsStreamConnected(false);
        }
      );

      return () => {
        disconnect();
        setIsStreamConnected(false);
      };
    }
  }, [selectedProject?.id, loadProjectDetails]);

  // Action Handlers
  const handleCreateProject = async (payload: ProjectCreatePayload) => {
    const created = await createProject(payload);
    await loadProjects();
    setSelectedProject(created);
  };

  const handleStartWorkflow = async () => {
    if (!selectedProject) return;
    setIsActionLoading(true);
    try {
      await startWorkflow(selectedProject.id);
      await loadProjectDetails(selectedProject.id);
    } catch (err: any) {
      alert(`Error starting workflow: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleResumeWorkflow = async () => {
    if (!selectedProject) return;
    setIsActionLoading(true);
    try {
      await resumeWorkflow(selectedProject.id);
      await loadProjectDetails(selectedProject.id);
    } catch (err: any) {
      alert(`Error resuming workflow: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleApproveRequirements = async (comments = '') => {
    if (!selectedProject) return;
    setIsActionLoading(true);
    try {
      await approveRequirements(selectedProject.id, comments);
      await loadProjectDetails(selectedProject.id);
    } catch (err: any) {
      alert(`Error approving requirements: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleApproveArchitecture = async (comments = '') => {
    if (!selectedProject) return;
    setIsActionLoading(true);
    try {
      await approveArchitecture(selectedProject.id, comments);
      await loadProjectDetails(selectedProject.id);
    } catch (err: any) {
      alert(`Error approving architecture: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={(p) => {
          setSelectedProject(p);
          setEvents([]);
        }}
        onOpenNewProject={() => setIsModalOpen(true)}
        onRefresh={() => {
          if (selectedProject) loadProjectDetails(selectedProject.id);
          refreshHealth();
        }}
        isRefreshing={isRefreshing}
        health={health}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {viewMode === 'monitoring' ? (
          <LogsCenter
            projects={projects}
            selectedProject={selectedProject}
            health={health}
          />
        ) : viewMode === 'terminal' ? (
          <TerminalCenter
            project={selectedProject}
            onOpenTraceLogs={(_traceId?: string) => setViewMode('monitoring')}
          />
        ) : selectedProject ? (
          <>
            {/* Project Overview Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    <FolderGit2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white m-0">{selectedProject.name}</h2>
                    <p className="text-xs text-slate-400 font-mono m-0">ID: {selectedProject.id}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
                  <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Lang: {selectedProject.preferred_language || 'python'}
                  </span>
                  <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    Framework: {selectedProject.preferred_framework || 'fastapi'}
                  </span>
                  <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    DB: {selectedProject.preferred_database || 'sqlite'}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed m-0">
                {selectedProject.description}
              </p>
            </div>

            {/* Stage Progress */}
            <StageProgress status={selectedProject.status} />

            {/* Workflow Action Controls */}
            <WorkflowControls
              project={selectedProject}
              onStart={handleStartWorkflow}
              onResume={handleResumeWorkflow}
              onApproveRequirements={handleApproveRequirements}
              onApproveArchitecture={handleApproveArchitecture}
              loading={isActionLoading}
            />

            {/* Specialized Agent Team Roster */}
            <AgentRoster runs={agentRuns} />

            {/* Two-Column Layout: Task Board & Real-Time Event Stream */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <TaskBoard tasks={tasks} />
              <LiveLogs
                events={events}
                onClear={() => setEvents([])}
                isConnected={isStreamConnected}
                onOpenMonitoringCenter={() => setViewMode('monitoring')}
              />
            </div>

            {/* Workspace Files & Git Isolation */}
            <WorkspaceExplorer projectId={selectedProject.id} />

            {/* QA Automated Verification & Security Scan */}
            <QASecurityPanel projectId={selectedProject.id} />

            {/* Generated Artifacts Viewer */}
            <ArtifactViewer projectId={selectedProject.id} artifacts={artifacts} />
          </>
        ) : (
          <div className="min-h-[500px] flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-4 border border-indigo-500/20">
              <Layers className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">No Project Selected</h3>
            <p className="text-sm text-slate-400 max-w-md mb-6">
              Create a new software project by providing natural-language requirements. The AI
              multi-agent team will analyse, architect, plan, implement, test, and review the code.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition shadow-lg shadow-indigo-600/20"
            >
              Create First Project
            </button>
          </div>
        )}
      </main>

      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateProject}
      />
    </div>
  );
};

export default App;
