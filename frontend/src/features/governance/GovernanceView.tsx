import React, { useState } from "react";
import { ShieldCheck, GitPullRequest, Activity } from "lucide-react";
import RoleManager from "./RoleManager";
import PRCheckForm, { type CICheckResult } from "./PRCheckForm";
import DriftReportView from "./DriftReportView";
import AuditLogViewer from "./AuditLogViewer";

export const GovernanceView: React.FC = () => {
  const [ciCheckResult, setCiCheckResult] = useState<CICheckResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleCheckComplete = (result: CICheckResult) => {
    setCiCheckResult(result);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-zinc-900 via-indigo-950 to-zinc-900 text-white p-6 rounded-2xl border border-zinc-800 shadow-lg">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">
              Governance & CI/CD Gatekeeper
            </h1>
          </div>
          <p className="text-xs text-zinc-400 max-w-2xl pl-10">
            Control center for architectural enforcement, quality gates, dependency drift detection, and RBAC enterprise auditing.
          </p>
        </div>

        <div className="flex items-center gap-3 pl-10 md:pl-0">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800/80 border border-zinc-700/60 text-xs font-mono text-zinc-300">
            <GitPullRequest className="w-3.5 h-3.5 text-indigo-400" />
            <span>CI Gate: Active</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs font-mono text-emerald-400">
            <Activity className="w-3.5 h-3.5" />
            <span>Audit Engine Online</span>
          </div>
        </div>
      </div>

      {/* Role Manager section */}
      <RoleManager />

      {/* Grid: PR Check UI & Drift Report */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PRCheckForm
          onCheckComplete={handleCheckComplete}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
        />
        <DriftReportView driftReport={ciCheckResult ? ciCheckResult.drift : null} />
      </div>

      {/* Audit Log Viewer Section */}
      <AuditLogViewer />
    </div>
  );
};

export default GovernanceView;
