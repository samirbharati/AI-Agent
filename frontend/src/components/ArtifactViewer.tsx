import React, { useEffect, useState } from 'react';
import { FileText, Copy, Check } from 'lucide-react';
import type { Artifact, ArtifactDetail } from '../types';
import { getArtifactContent } from '../services/api';

interface ArtifactViewerProps {
  projectId: string;
  artifacts: Artifact[];
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ projectId, artifacts }) => {
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [currentDetail, setCurrentDetail] = useState<ArtifactDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (artifacts.length > 0 && !selectedName) {
      setSelectedName(artifacts[0].name);
    }
  }, [artifacts, selectedName]);

  useEffect(() => {
    if (selectedName && projectId) {
      setLoading(true);
      getArtifactContent(projectId, selectedName)
        .then((detail) => setCurrentDetail(detail))
        .catch((err) => console.error('Failed to load artifact:', err))
        .finally(() => setLoading(false));
    }
  }, [selectedName, projectId]);

  const handleCopy = () => {
    if (currentDetail?.content) {
      navigator.clipboard.writeText(currentDetail.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-col h-[480px]">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 m-0">
            Generated Artifacts & Specifications
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          Documents: <strong className="text-white">{artifacts.length}</strong>
        </span>
      </div>

      {artifacts.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-slate-500 text-xs">
          No artifacts generated yet. They will appear here once agents run.
        </div>
      ) : (
        <div className="flex-1 flex flex-col md:flex-row gap-4 overflow-hidden">
          {/* Artifact List */}
          <div className="w-full md:w-56 shrink-0 space-y-1 overflow-y-auto pr-1">
            {artifacts.map((a) => (
              <button
                key={a.id}
                onClick={() => setSelectedName(a.name)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition flex items-center justify-between gap-2 ${
                  selectedName === a.name
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <span className="truncate">{a.name}</span>
                <span className="text-[10px] text-slate-500 uppercase font-mono shrink-0">
                  {a.artifact_type.slice(0, 4)}
                </span>
              </button>
            ))}
          </div>

          {/* Document Content View */}
          <div className="flex-1 flex flex-col bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
            <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-mono text-slate-300 font-medium">
                {selectedName || 'Select an artifact'}
              </span>
              {currentDetail && (
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy Text'}</span>
                </button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 text-xs font-mono leading-relaxed text-slate-300 whitespace-pre-wrap selection:bg-indigo-500/30">
              {loading ? (
                <div className="text-slate-500">Loading document content...</div>
              ) : currentDetail?.content ? (
                currentDetail.content
              ) : (
                <div className="text-slate-600">No content available.</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
