import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  RotateCw,
  ExternalLink,
  Shield,
  Zap,
  Globe,
  Database,
  Terminal,
  Activity,
  Layers,
  Sparkles,
} from 'lucide-react';
import type { IntegrationStatusResponse, IntegrationTestResult } from '../../types';

interface IntegrationCardProps {
  integration: IntegrationStatusResponse;
  onToggle: (providerId: string, enabled: boolean) => Promise<void>;
  onTest: (providerId: string) => Promise<IntegrationTestResult>;
  onAction?: (providerId: string) => void;
}

export const IntegrationCard: React.FC<IntegrationCardProps> = ({
  integration,
  onToggle,
  onTest,
  onAction,
}) => {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<IntegrationTestResult | null>(null);

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'vcs':
        return <Terminal className="w-4 h-4 text-purple-400" />;
      case 'ci_cd':
        return <Zap className="w-4 h-4 text-amber-400" />;
      case 'security':
        return <Shield className="w-4 h-4 text-red-400" />;
      case 'observability':
      case 'error_tracking':
        return <Activity className="w-4 h-4 text-cyan-400" />;
      case 'monitoring':
        return <Activity className="w-4 h-4 text-emerald-400" />;
      case 'deployment':
        return <Globe className="w-4 h-4 text-blue-400" />;
      case 'storage':
        return <Database className="w-4 h-4 text-orange-400" />;
      default:
        return <Layers className="w-4 h-4 text-indigo-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'connected':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            Connected
          </span>
        );
      case 'not_configured':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <HelpCircle className="w-3 h-3 text-slate-400" />
            Local Fallback
          </span>
        );
      case 'disabled':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            Disabled
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-red-500/10 text-red-400 border border-red-500/30">
            <AlertCircle className="w-3 h-3 text-red-400" />
            Error
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
            Configured
          </span>
        );
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await onTest(integration.provider_id);
      setTestResult(res);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="bg-[#0D1320] border border-[#243044] hover:border-slate-700 rounded-xl p-5 shadow-lg flex flex-col justify-between transition group">
      <div>
        {/* Top Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-slate-900 border border-[#243044]">
              {getCategoryIcon(integration.category)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide m-0">
                  {integration.name}
                </h3>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  {integration.category}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                {integration.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {getStatusBadge(integration.status)}
          </div>
        </div>

        {/* Free Tier Callout */}
        <div className="my-3 p-2.5 rounded-lg bg-[#070A10] border border-[#1E293B] text-xs font-mono space-y-1">
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px]">
            <Sparkles className="w-3 h-3 text-emerald-400 shrink-0" />
            <span>FREE TIER ALLOWANCE</span>
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed m-0">
            {integration.free_tier_info}
          </p>
        </div>

        {/* Quota / Usage Bar if available */}
        {integration.usage && (
          <div className="my-2.5 space-y-1">
            <div className="flex justify-between text-[11px] font-mono text-slate-400">
              <span>Usage:</span>
              <span className="text-cyan-300 font-semibold">
                {integration.usage.quota_used} / {integration.usage.quota_total ?? '∞'} {integration.usage.quota_unit}
              </span>
            </div>
            {integration.usage.percentage !== null && integration.usage.percentage !== undefined && (
              <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-cyan-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${Math.min(integration.usage.percentage, 100)}%` }}
                />
              </div>
            )}
          </div>
        )}

        {/* Features Checklist */}
        <div className="mt-3 space-y-1">
          <p className="text-[10px] font-mono uppercase text-slate-500 tracking-wider font-semibold">
            CAPABILITIES
          </p>
          <div className="grid grid-cols-1 gap-1 text-[11px] text-slate-300 font-mono">
            {integration.features.slice(0, 4).map((f, idx) => (
              <div key={idx} className="flex items-center gap-1.5">
                <span className="w-1 h-1 rounded-full bg-indigo-400 shrink-0" />
                <span className="truncate">{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Live Message & Latency */}
        <div className="mt-3 pt-2 border-t border-[#1E293B] text-[11px] font-mono text-slate-400 flex items-center justify-between">
          <span className="truncate max-w-[260px]" title={integration.message}>
            {integration.message}
          </span>
          {integration.latency_ms && (
            <span className="text-slate-500 text-[10px] shrink-0">
              {Math.round(integration.latency_ms)}ms
            </span>
          )}
        </div>

        {/* Test Result Banner */}
        {testResult && (
          <div
            className={`mt-2 p-2 rounded text-[11px] font-mono border ${
              testResult.success
                ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
                : 'bg-red-950/40 border-red-800 text-red-300'
            }`}
          >
            {testResult.message}
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="mt-4 pt-3 border-t border-[#1E293B] flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {/* Enable / Disable switch */}
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={integration.is_enabled}
              onChange={(e) => onToggle(integration.provider_id, e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-600"></div>
            <span className="ml-1.5 text-[10px] font-mono text-slate-400">
              {integration.is_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </label>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition"
            title="Probe provider connectivity"
          >
            <RotateCw className={`w-3 h-3 ${testing ? 'animate-spin text-cyan-400' : 'text-slate-400'}`} />
            <span>Test</span>
          </button>

          {onAction && (
            <button
              onClick={() => onAction(integration.provider_id)}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-semibold shadow-md shadow-indigo-600/20 transition"
            >
              <span>Manage</span>
              <ExternalLink className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
