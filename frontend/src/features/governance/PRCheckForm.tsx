import React, { useState } from "react";
import { Play, GitCompare, RefreshCw, AlertCircle, CheckCircle2, ShieldAlert, Gauge, Layers } from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";

export interface CICheckResult {
  status: string;
  passed: boolean;
  bypassed: boolean;
  highest_debt_score: number;
  has_drift: boolean;
  drift: Record<string, { added?: string[]; removed?: string[]; modified?: string[] }>;
  base_ref: string;
  target_ref: string;
  role: string;
  message?: string;
}

interface PRCheckFormProps {
  onCheckComplete: (result: CICheckResult) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const PRCheckForm: React.FC<PRCheckFormProps> = ({
  onCheckComplete,
  isLoading,
  setIsLoading,
}) => {
  const { repoPath, userRole } = useAnalysis();
  const [baseRef, setBaseRef] = useState<string>("HEAD~1");
  const [targetRef, setTargetRef] = useState<string>("HEAD");
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<CICheckResult | null>(null);

  const handleRunCheck = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/governance/ci-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path: repoPath || undefined,
          base_ref: baseRef.trim(),
          target_ref: targetRef.trim(),
          role: userRole.toLowerCase(),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(errData.detail || `Server responded with HTTP ${res.status}`);
      }

      const data: CICheckResult = await res.json();
      setLastResult(data);
      onCheckComplete(data);
    } catch (err: any) {
      console.error("Failed to run CI Check:", err);
      setError(err.message || "Failed to run Gatekeeper check.");
    } finally {
      setIsLoading(false);
    }
  };

  const applyPreset = (base: string, target: string) => {
    setBaseRef(base);
    setTargetRef(target);
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
            <GitCompare className="w-4.5 h-4.5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              PR Architecture & Quality Gatekeeper
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Evaluate PR changes against architectural drift and debt thresholds
            </p>
          </div>
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="flex items-center gap-2 text-xs flex-wrap">
        <span className="text-zinc-500 font-medium text-[11px] uppercase tracking-wider">Quick Presets:</span>
        <button
          type="button"
          onClick={() => applyPreset("HEAD~1", "HEAD")}
          className="px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors font-mono text-[11px] cursor-pointer"
        >
          HEAD~1 ➔ HEAD
        </button>
        <button
          type="button"
          onClick={() => applyPreset("main", "HEAD")}
          className="px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors font-mono text-[11px] cursor-pointer"
        >
          main ➔ HEAD
        </button>
        <button
          type="button"
          onClick={() => applyPreset("HEAD", "working_dir")}
          className="px-2.5 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors font-mono text-[11px] cursor-pointer"
        >
          HEAD ➔ Working Tree
        </button>
      </div>

      <form onSubmit={handleRunCheck} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="base_ref" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
              Base Reference (<code className="font-mono text-indigo-500">base_ref</code>)
            </label>
            <input
              id="base_ref"
              type="text"
              value={baseRef}
              onChange={(e) => setBaseRef(e.target.value)}
              placeholder="e.g. HEAD~1 or main"
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>

          <div>
            <label htmlFor="target_ref" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
              Target Reference (<code className="font-mono text-indigo-500">target_ref</code>)
            </label>
            <input
              id="target_ref"
              type="text"
              value={targetRef}
              onChange={(e) => setTargetRef(e.target.value)}
              placeholder="e.g. HEAD or working_dir"
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2">
          <div className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
            <span>Role Context:</span>
            <span className="font-semibold text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded">
              {userRole}
            </span>
          </div>

          <button
            id="run_gatekeeper_check_btn"
            type="submit"
            disabled={isLoading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer active:scale-98"
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Evaluating PR...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Gatekeeper Check</span>
              </>
            )}
          </button>
        </div>
      </form>

      {error && (
        <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Result Status Banner */}
      {lastResult && (
        <div
          className={`p-4 rounded-xl border transition-all ${
            lastResult.passed
              ? lastResult.bypassed
                ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                : "bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200"
              : "bg-red-500/10 border-red-500/30 text-red-900 dark:text-red-200"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              {lastResult.passed ? (
                lastResult.bypassed ? (
                  <ShieldAlert className="w-5 h-5 text-amber-500" />
                ) : (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                )
              ) : (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
              <span className="font-bold text-base">
                {lastResult.passed
                  ? lastResult.bypassed
                    ? "PASS (Bypassed Drift Check)"
                    : "PASS"
                  : "FAIL (Gatekeeper Check Rejected)"}
              </span>
            </div>
            <span className="text-xs font-mono opacity-75">
              Role: {lastResult.role}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1 border-t border-current/10">
            <div className="flex items-center gap-2">
              <Gauge className="w-4 h-4 text-indigo-500" />
              <span>Highest Debt Score:</span>
              <span
                className={`font-bold font-mono px-1.5 py-0.5 rounded ${
                  lastResult.highest_debt_score > 80
                    ? "bg-red-500/20 text-red-600 dark:text-red-400"
                    : "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {lastResult.highest_debt_score} / 80
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-500" />
              <span>Architectural Drift:</span>
              <span
                className={`font-bold font-mono px-1.5 py-0.5 rounded ${
                  lastResult.has_drift
                    ? lastResult.bypassed
                      ? "bg-amber-500/20 text-amber-600 dark:text-amber-400"
                      : "bg-red-500/20 text-red-600 dark:text-red-400"
                    : "bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
                }`}
              >
                {lastResult.has_drift ? "Detected (Added Deps)" : "None"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PRCheckForm;
