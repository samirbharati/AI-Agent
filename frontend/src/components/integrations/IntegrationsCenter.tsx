import React, { useState, useEffect, useCallback } from 'react';
import {
  Layers,
  Sparkles,
  Shield,
  RotateCw,
  Zap,
  Globe,
  Database,
  Terminal,
  Activity,
  Heart,
} from 'lucide-react';
import {
  getIntegrations,
  testIntegration,
  toggleIntegration,
} from '../../services/api';
import type {
  IntegrationStatusResponse,
  IntegrationTestResult,
  Project,
} from '../../types';
import { IntegrationCard } from './IntegrationCard';
import { SecurityAuditModal } from './SecurityAuditModal';

interface IntegrationsCenterProps {
  project: Project | null;
}

export const IntegrationsCenter: React.FC<IntegrationsCenterProps> = ({ project }) => {
  const [integrations, setIntegrations] = useState<IntegrationStatusResponse[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getIntegrations(
        selectedCategory === 'all' ? undefined : selectedCategory
      );
      setIntegrations(data);
    } catch (e) {
      console.error('Failed to load integrations:', e);
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggle = async (providerId: string, enabled: boolean) => {
    try {
      await toggleIntegration(providerId, enabled);
      setIntegrations((prev) =>
        prev.map((i) =>
          i.provider_id === providerId
            ? { ...i, is_enabled: enabled, status: enabled ? i.status : 'disabled' }
            : i
        )
      );
    } catch (e) {
      console.error('Failed to toggle integration:', e);
    }
  };

  const handleTest = async (providerId: string): Promise<IntegrationTestResult> => {
    return await testIntegration(providerId);
  };

  const handleAction = (providerId: string) => {
    if (['semgrep', 'gitleaks', 'trivy'].includes(providerId)) {
      setIsAuditModalOpen(true);
    } else {
      alert(`Provider ${providerId} management console.`);
    }
  };

  const categories: { id: string; label: string; icon: any }[] = [
    { id: 'all', label: 'All Services', icon: Layers },
    { id: 'vcs', label: 'VCS & Git', icon: Terminal },
    { id: 'ci_cd', label: 'CI/CD Pipelines', icon: Zap },
    { id: 'security', label: 'Security Scanners', icon: Shield },
    { id: 'observability', label: 'Observability & Logs', icon: Activity },
    { id: 'monitoring', label: 'Uptime Monitoring', icon: Heart },
    { id: 'deployment', label: 'Deployment & Tunnel', icon: Globe },
    { id: 'storage', label: 'Object Storage', icon: Database },
  ];

  const connectedCount = integrations.filter((i) => i.status === 'connected').length;
  const fallbackCount = integrations.filter((i) => i.status === 'not_configured').length;

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="bg-[#0D1320] border border-[#243044] rounded-2xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 text-white">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight m-0">
                Free Developer Services & Cloud Infrastructure
              </h2>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                FREE-FOR-DEV READY
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed m-0">
              Curated zero-cost developer tiers for Git version control, CI/CD, SAST, secret detection,
              dependency CVE auditing, centralized logs, uptime heartbeats, edge hosting, and S3 object archival.
            </p>
          </div>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition shrink-0"
        >
          <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-cyan-400' : ''}`} />
          <span>Refresh All</span>
        </button>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 font-mono">
        <div className="bg-[#0D1320] border border-[#243044] rounded-xl p-4">
          <span className="text-xs text-slate-400">Total Services</span>
          <p className="text-2xl font-bold text-white mt-1 m-0">{integrations.length}</p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Standard Providers</span>
        </div>

        <div className="bg-[#0D1320] border border-[#243044] rounded-xl p-4">
          <span className="text-xs text-emerald-400">Active / Connected</span>
          <p className="text-2xl font-bold text-emerald-400 mt-1 m-0">{connectedCount}</p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Live Probes Passing</span>
        </div>

        <div className="bg-[#0D1320] border border-[#243044] rounded-xl p-4">
          <span className="text-xs text-indigo-400">Local-First Fallback</span>
          <p className="text-2xl font-bold text-indigo-300 mt-1 m-0">{fallbackCount}</p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">100% Local Resilience</span>
        </div>

        <div className="bg-[#0D1320] border border-[#243044] rounded-xl p-4">
          <span className="text-xs text-purple-400">Recurring Cost</span>
          <p className="text-2xl font-bold text-purple-300 mt-1 m-0">$0 / mo</p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">Free-Tier Infrastructure</span>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none pb-1">
        {categories.map((c) => {
          const Icon = c.icon;
          const isActive = selectedCategory === c.id;
          return (
            <button
              key={c.id}
              onClick={() => setSelectedCategory(c.id)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap border ${
                isActive
                  ? 'bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/20'
                  : 'bg-[#0D1320] text-slate-400 hover:text-white border-[#243044] hover:border-slate-600'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{c.label}</span>
            </button>
          );
        })}
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {integrations.map((i) => (
          <IntegrationCard
            key={i.provider_id}
            integration={i}
            onToggle={handleToggle}
            onTest={handleTest}
            onAction={handleAction}
          />
        ))}
      </div>

      {/* Security Audit Modal */}
      <SecurityAuditModal
        project={project}
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </div>
  );
};
