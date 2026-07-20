import React, { useState } from "react";
import { PlusCircle, MinusCircle, FileCode, Code, CheckCircle, AlertTriangle, Layers } from "lucide-react";

interface DriftReportProps {
  driftReport: Record<string, any> | null;
}

export const DriftReportView: React.FC<DriftReportProps> = ({ driftReport }) => {
  const [viewMode, setViewMode] = useState<"diff" | "json">("diff");

  if (!driftReport || Object.keys(driftReport).length === 0) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-6 text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-500 flex items-center justify-center mx-auto">
          <CheckCircle className="w-6 h-6" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            No Architectural Drift Detected
          </h4>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-md mx-auto">
            Dependencies across the base and target git references are fully aligned. No unapproved module additions or removals were detected.
          </p>
        </div>
      </div>
    );
  }

  const fileEntries = Object.entries(driftReport);
  let totalAdded = 0;
  let totalRemoved = 0;

  fileEntries.forEach(([_, changes]) => {
    if (changes && typeof changes === "object") {
      if (Array.isArray(changes.added)) totalAdded += changes.added.length;
      if (Array.isArray(changes.removed)) totalRemoved += changes.removed.length;
    }
  });

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-purple-500/10 dark:bg-purple-500/20 text-purple-600 dark:text-purple-400 flex items-center justify-center">
            <Layers className="w-4.5 h-4.5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Architectural Drift Report
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Visualizing dependency changes between base and target references
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Summary Badges */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium border border-emerald-500/20">
              +{totalAdded} added
            </span>
            <span className="px-2 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400 font-medium border border-red-500/20">
              -{totalRemoved} removed
            </span>
          </div>

          {/* View Mode Switcher */}
          <div className="flex items-center rounded-lg bg-zinc-100 dark:bg-zinc-800 p-0.5 border border-zinc-200 dark:border-zinc-700">
            <button
              type="button"
              onClick={() => setViewMode("diff")}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
                viewMode === "diff"
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs"
                  : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              Diff View
            </button>
            <button
              type="button"
              onClick={() => setViewMode("json")}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
                viewMode === "json"
                  ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs"
                  : "text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              JSON View
            </button>
          </div>
        </div>
      </div>

      {/* View Content */}
      {viewMode === "json" ? (
        <div className="bg-zinc-950 rounded-xl p-4 overflow-x-auto border border-zinc-800 font-mono text-xs text-zinc-300">
          <pre>{JSON.stringify(driftReport, null, 2)}</pre>
        </div>
      ) : (
        <div className="space-y-4">
          {fileEntries.map(([filePath, changes]: [string, any]) => {
            const addedList: string[] = Array.isArray(changes?.added) ? changes.added : [];
            const removedList: string[] = Array.isArray(changes?.removed) ? changes.removed : [];
            const modifiedList: string[] = Array.isArray(changes?.modified) ? changes.modified : [];

            return (
              <div
                key={filePath}
                className="rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden bg-zinc-50/50 dark:bg-zinc-950/40"
              >
                {/* File Header */}
                <div className="px-4 py-2.5 bg-zinc-100 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
                  <div className="flex items-center gap-2 font-mono text-xs text-zinc-800 dark:text-zinc-200 font-semibold">
                    <FileCode className="w-4 h-4 text-indigo-500" />
                    <span>{filePath}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] font-mono">
                    {addedList.length > 0 && (
                      <span className="text-emerald-600 dark:text-emerald-400">
                        +{addedList.length}
                      </span>
                    )}
                    {removedList.length > 0 && (
                      <span className="text-red-600 dark:text-red-400">
                        -{removedList.length}
                      </span>
                    )}
                  </div>
                </div>

                {/* Diff Lines Body */}
                <div className="p-3 font-mono text-xs space-y-1.5 bg-zinc-950/90 text-zinc-200">
                  {/* Added dependencies */}
                  {addedList.map((dep, idx) => (
                    <div
                      key={`add-${idx}`}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono"
                    >
                      <PlusCircle className="w-3.5 h-3.5 flex-shrink-0 text-emerald-400" />
                      <span className="select-none font-bold text-emerald-500">+</span>
                      <span>{dep}</span>
                      <span className="ml-auto text-[10px] uppercase font-sans tracking-wider px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300">
                        Added Dep
                      </span>
                    </div>
                  ))}

                  {/* Removed dependencies */}
                  {removedList.map((dep, idx) => (
                    <div
                      key={`rem-${idx}`}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 font-mono"
                    >
                      <MinusCircle className="w-3.5 h-3.5 flex-shrink-0 text-red-400" />
                      <span className="select-none font-bold text-red-500">-</span>
                      <span>{dep}</span>
                      <span className="ml-auto text-[10px] uppercase font-sans tracking-wider px-1.5 py-0.2 rounded bg-red-500/20 text-red-300">
                        Removed Dep
                      </span>
                    </div>
                  ))}

                  {/* Modified dependencies */}
                  {modifiedList.map((dep, idx) => (
                    <div
                      key={`mod-${idx}`}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 text-amber-400" />
                      <span className="select-none font-bold text-amber-500">~</span>
                      <span>{dep}</span>
                      <span className="ml-auto text-[10px] uppercase font-sans tracking-wider px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300">
                        Modified
                      </span>
                    </div>
                  ))}

                  {addedList.length === 0 && removedList.length === 0 && modifiedList.length === 0 && (
                    <div className="text-zinc-500 italic px-2 py-1 text-[11px]">
                      No line-level dependency diffs recorded for this file.
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DriftReportView;
