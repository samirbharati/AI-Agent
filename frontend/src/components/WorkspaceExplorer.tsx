import React, { useEffect, useState } from 'react';
import {
  FolderTree,
  FileCode,
  GitBranch,
  Copy,
  Check,
  RefreshCw,
  GitCommit,
  FileText,
} from 'lucide-react';
import type { GitStatus, WorkspaceFile, WorkspaceFileContent } from '../types';
import { getGitDiff, getGitStatus, getWorkspaceFileContent, getWorkspaceFiles } from '../services/api';

interface WorkspaceExplorerProps {
  projectId: string;
}

export const WorkspaceExplorer: React.FC<WorkspaceExplorerProps> = ({ projectId }) => {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<WorkspaceFileContent | null>(null);
  const [gitStatus, setGitStatus] = useState<GitStatus | null>(null);
  const [gitDiff, setGitDiff] = useState<string>('');
  const [viewMode, setViewMode] = useState<'code' | 'diff'>('code');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadWorkspace = async () => {
    if (!projectId) return;
    try {
      const [filesRes, gitRes, diffRes] = await Promise.allSettled([
        getWorkspaceFiles(projectId),
        getGitStatus(projectId),
        getGitDiff(projectId),
      ]);

      if (filesRes.status === 'fulfilled') {
        setFiles(filesRes.value.files);
        if (filesRes.value.files.length > 0 && !selectedFile) {
          setSelectedFile(filesRes.value.files[0].path);
        }
      }
      if (gitRes.status === 'fulfilled') {
        setGitStatus(gitRes.value);
      }
      if (diffRes.status === 'fulfilled') {
        setGitDiff(diffRes.value.diff);
      }
    } catch (e) {
      console.error('Failed to load workspace data:', e);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, [projectId]);

  useEffect(() => {
    if (selectedFile && projectId && viewMode === 'code') {
      setLoading(true);
      getWorkspaceFileContent(projectId, selectedFile)
        .then((c) => setFileContent(c))
        .catch((err) => console.error('Failed to load file content:', err))
        .finally(() => setLoading(false));
    }
  }, [selectedFile, projectId, viewMode]);

  const handleCopy = () => {
    const textToCopy = viewMode === 'code' ? fileContent?.content : gitDiff;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col h-[500px]">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 mb-3 gap-2">
        <div className="flex items-center gap-2">
          <FolderTree className="w-4 h-4 text-emerald-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 m-0">
            Workspace Files & Git Isolation
          </h3>
        </div>

        <div className="flex items-center gap-3">
          {/* Git Branch Pill */}
          {gitStatus?.initialized ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 border border-slate-700 text-xs font-mono text-slate-300">
              <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
              <span>{gitStatus.branch || 'main'}</span>
              {(gitStatus.modified.length > 0 || gitStatus.untracked.length > 0) && (
                <span className="w-2 h-2 rounded-full bg-amber-400" title="Uncommitted changes" />
              )}
            </div>
          ) : (
            <span className="text-[11px] text-slate-500 font-mono">Git repo: uninitialized</span>
          )}

          {/* Code vs Diff Mode Toggle */}
          <div className="flex rounded-lg bg-slate-800 border border-slate-700 p-0.5 text-xs font-medium">
            <button
              onClick={() => setViewMode('code')}
              className={`px-2.5 py-1 rounded transition ${
                viewMode === 'code'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Files ({files.length})
            </button>
            <button
              onClick={() => setViewMode('diff')}
              className={`px-2.5 py-1 rounded transition flex items-center gap-1 ${
                viewMode === 'diff'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <GitCommit className="w-3.5 h-3.5" />
              <span>Diff</span>
            </button>
          </div>

          <button
            onClick={loadWorkspace}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
            title="Refresh workspace"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Workspace Body */}
      {viewMode === 'diff' ? (
        <div className="flex-1 flex flex-col bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs">
            <span className="font-mono text-slate-300">Git Working Tree Diff</span>
            {gitDiff && (
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy Diff'}</span>
              </button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap selection:bg-indigo-500/30">
            {gitDiff || (
              <div className="text-slate-500 text-xs text-center py-12">
                No uncommitted diff against base branch.
              </div>
            )}
          </div>
        </div>
      ) : files.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs p-6 text-center">
          <FileCode className="w-8 h-8 text-slate-600 mb-2" />
          <p className="m-0 font-medium text-slate-400">Workspace is empty</p>
          <p className="m-0 text-slate-500 text-[11px] mt-1">
            Generated source files written to <code>workspace/projects/{projectId}</code> will appear here.
          </p>
        </div>
      ) : (
        <div className="flex-1 flex flex-col md:flex-row gap-3 overflow-hidden">
          {/* File Tree */}
          <div className="w-full md:w-64 shrink-0 space-y-1 overflow-y-auto pr-1 border-r border-slate-800/80">
            {files.map((file) => (
              <button
                key={file.path}
                onClick={() => setSelectedFile(file.path)}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono transition flex items-center justify-between gap-1.5 ${
                  selectedFile === file.path
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-1.5 truncate">
                  <FileText className="w-3.5 h-3.5 shrink-0 text-indigo-400" />
                  <span className="truncate">{file.path}</span>
                </div>
                <span className="text-[10px] text-slate-500 shrink-0 font-sans">
                  {file.size_bytes > 1024
                    ? `${(file.size_bytes / 1024).toFixed(1)}k`
                    : `${file.size_bytes}b`}
                </span>
              </button>
            ))}
          </div>

          {/* File Content Preview */}
          <div className="flex-1 flex flex-col bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-mono text-slate-300 font-medium">
                {selectedFile || 'Select a file'}
              </span>
              {fileContent && (
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy Code'}</span>
                </button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 text-xs font-mono leading-relaxed text-slate-200 whitespace-pre-wrap selection:bg-indigo-500/30">
              {loading ? (
                <div className="text-slate-500">Loading file...</div>
              ) : fileContent?.content ? (
                fileContent.content
              ) : (
                <div className="text-slate-600">Select a file from the explorer to view code.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
