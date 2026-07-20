import React from "react";
import { Shield, ShieldAlert, UserCheck, CheckCircle2, Lock } from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";

export const RoleManager: React.FC = () => {
  const { userRole, setUserRole } = useAnalysis();

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
            <UserCheck className="w-4.5 h-4.5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Role-Based Access Control (RBAC)
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Select your simulated role to test gatekeeper enforcement & bypass rules
            </p>
          </div>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            userRole === "Architect"
              ? "bg-amber-500/10 text-amber-600 border-amber-500/30 dark:bg-amber-500/20 dark:text-amber-400"
              : "bg-blue-500/10 text-blue-600 border-blue-500/30 dark:bg-blue-500/20 dark:text-blue-400"
          }`}
        >
          {userRole === "Architect" ? <ShieldAlert className="w-3.5 h-3.5" /> : <Shield className="w-3.5 h-3.5" />}
          Active: {userRole}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Developer Role Button */}
        <button
          type="button"
          onClick={() => setUserRole("Developer")}
          className={`relative text-left p-4 rounded-xl border transition-all cursor-pointer ${
            userRole === "Developer"
              ? "border-blue-500 bg-blue-50/50 dark:bg-blue-950/20 ring-2 ring-blue-500/20"
              : "border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-950/50"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-mono text-xs font-bold">
                DEV
              </span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Developer Role
              </span>
            </div>
            {userRole === "Developer" && (
              <CheckCircle2 className="w-4 h-4 text-blue-500" />
            )}
          </div>
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
            Standard gatekeeper rules. Architectural drift or high technical debt (&gt;80) will fail PR checks.
          </p>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-zinc-500 dark:text-zinc-400">
            <Lock className="w-3 h-3 text-zinc-400" />
            <span>Cannot bypass drift rules</span>
          </div>
        </button>

        {/* Architect Role Button */}
        <button
          type="button"
          onClick={() => setUserRole("Architect")}
          className={`relative text-left p-4 rounded-xl border transition-all cursor-pointer ${
            userRole === "Architect"
              ? "border-amber-500 bg-amber-50/50 dark:bg-amber-950/20 ring-2 ring-amber-500/20"
              : "border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-zinc-50/50 dark:bg-zinc-950/50"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center font-mono text-xs font-bold">
                ARC
              </span>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                Architect Role
              </span>
            </div>
            {userRole === "Architect" && (
              <CheckCircle2 className="w-4 h-4 text-amber-500" />
            )}
          </div>
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
            Elevated permissions. Allowed to bypass architectural drift gates provided debt score is ≤ 80.
          </p>
          <div className="mt-3 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400 font-medium">
            <ShieldAlert className="w-3 h-3" />
            <span>Permission: bypass_drift enabled</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default RoleManager;
