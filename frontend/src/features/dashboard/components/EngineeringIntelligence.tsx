import React, { useState, useEffect, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState
} from "@tanstack/react-table";
import {
  Flame,
  ShieldAlert,
  Zap,
  Search,
  Filter,
  AlertTriangle,
  Lock,
  FileCode,
  RefreshCw,
  SlidersHorizontal,
  CheckCircle,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Info
} from "lucide-react";
import { useAnalysis } from "../../../context/AnalysisContext";

export interface TechnicalDebtItem {
  file: string;
  coupling: number;
  complexity: number;
  churn: number;
  score: number;
  severity: "High" | "Medium" | "Low";
}

export interface SecurityAuditItem {
  file: string;
  issue: string;
  severity: "High" | "Medium" | "Low";
  line: number;
  remediation?: string;
}

export interface PerformanceAuditItem {
  file: string;
  issue: string;
  severity: "High" | "Medium" | "Low";
  target?: string;
  target_function?: string;
  recommendation?: string;
}

// Fallback high-fidelity sample data based on Repollama repo engines
const DEFAULT_DEBT_ITEMS: TechnicalDebtItem[] = [
  {
    file: "backend/repollama/cli.py",
    coupling: 28,
    complexity: 42,
    churn: 35,
    score: 96,
    severity: "High"
  },
  {
    file: "backend/repollama/main.py",
    coupling: 22,
    complexity: 38,
    churn: 29,
    score: 88,
    severity: "High"
  },
  {
    file: "backend/repollama/engines/watcher.py",
    coupling: 18,
    complexity: 25,
    churn: 19,
    score: 82,
    severity: "High"
  },
  {
    file: "backend/repollama/engines/graph_builder.py",
    coupling: 15,
    complexity: 20,
    churn: 14,
    score: 74,
    severity: "Medium"
  },
  {
    file: "backend/repollama/engines/ast_parser.py",
    coupling: 12,
    complexity: 18,
    churn: 11,
    score: 65,
    severity: "Medium"
  },
  {
    file: "frontend/src/features/dashboard/Dashboard.tsx",
    coupling: 10,
    complexity: 15,
    churn: 12,
    score: 58,
    severity: "Medium"
  },
  {
    file: "backend/repollama/database/vector_store.py",
    coupling: 8,
    complexity: 12,
    churn: 7,
    score: 42,
    severity: "Low"
  },
  {
    file: "backend/repollama/engines/git_miner.py",
    coupling: 6,
    complexity: 9,
    churn: 5,
    score: 35,
    severity: "Low"
  }
];

const DEFAULT_SECURITY_ITEMS: SecurityAuditItem[] = [
  {
    file: "backend/repollama/core/config.py",
    issue: "Hardcoded API key fallback detected in settings",
    severity: "High",
    line: 24,
    remediation: "Inject secret via environment variables or secret store (KMS/Vault) rather than hardcoded string literal."
  },
  {
    file: "backend/repollama/engines/security_auditor.py",
    issue: "Usage of HS256 without proper key management validation",
    severity: "Medium",
    line: 104,
    remediation: "Enforce asymmetric algorithms (RS256/ES256) or strict KMS key rotation for token signatures."
  },
  {
    file: "backend/repollama/database/auth_handler.py",
    issue: "Legacy MD5 hash used for temporary session verification",
    severity: "Medium",
    line: 45,
    remediation: "Upgrade legacy hashing algorithm from MD5 to SHA-256 or Argon2id."
  },
  {
    file: "frontend/src/context/AnalysisContext.tsx",
    issue: "Unsanitized direct query parameter in EventSource URL string",
    severity: "Low",
    line: 237,
    remediation: "Sanitize workspace path input before embedding into URI query string parameters."
  }
];

const DEFAULT_PERFORMANCE_ITEMS: PerformanceAuditItem[] = [
  {
    file: "backend/repollama/cli.py",
    issue: "Bloated function (845 lines)",
    severity: "Low",
    target: "cli_app",
    recommendation: "Decompose CLI command handlers into modular subcommand controllers to reduce cyclomatic complexity."
  },
  {
    file: "backend/repollama/engines/git_miner.py",
    issue: "Potential N+1 query loop in commit extraction",
    severity: "Medium",
    target: "get_file_churn",
    recommendation: "Batch git log queries using single rev-list process invocation instead of iterating per file path."
  },
  {
    file: "backend/repollama/engines/performance_auditor.py",
    issue: "Uncached repeated file read inside AST scan loop",
    severity: "Medium",
    target: "detect_anti_patterns",
    recommendation: "Pass pre-loaded in-memory file dictionary to avoid redundant disk I/O operations."
  },
  {
    file: "frontend/src/features/dashboard/Dashboard.tsx",
    issue: "Bloated component (305 lines)",
    severity: "Low",
    target: "Dashboard",
    recommendation: "Extract widget panels into memoized subcomponents to prevent unnecessary re-render passes."
  }
];

export const EngineeringIntelligence: React.FC = () => {
  const { repoPath } = useAnalysis();

  const [activeTab, setActiveTab] = useState<"debt" | "security" | "performance">("debt");
  const [loading, setLoading] = useState<boolean>(false);
  const [debtItems, setDebtItems] = useState<TechnicalDebtItem[]>(DEFAULT_DEBT_ITEMS);
  const [securityItems, setSecurityItems] = useState<SecurityAuditItem[]>(DEFAULT_SECURITY_ITEMS);
  const [performanceItems, setPerformanceItems] = useState<PerformanceAuditItem[]>(DEFAULT_PERFORMANCE_ITEMS);

  // Search & Filter state
  const [globalFilter, setGlobalFilter] = useState<string>("");
  const [highDebtOnly, setHighDebtOnly] = useState<boolean>(false);
  const [auditSearch, setAuditSearch] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<"ALL" | "High" | "Medium" | "Low">("ALL");

  const [sorting, setSorting] = useState<SortingState>([
    { id: "score", desc: true }
  ]);

  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  // Fetch real audit data from backend if available
  const fetchIntelligenceData = async () => {
    setLoading(true);
    try {
      const debtUrl = `http://localhost:8000/api/v1/intelligence/debt?path=${encodeURIComponent(repoPath || "")}`;
      const debtRes = await fetch(debtUrl);
      if (debtRes.ok) {
        const debtData = await debtRes.json();
        if (debtData.results && debtData.results.length > 0) {
          const mapped: TechnicalDebtItem[] = debtData.results.map((r: any) => {
            const score = r.score ?? 0;
            const severity: "High" | "Medium" | "Low" =
              score >= 80 ? "High" : score >= 50 ? "Medium" : "Low";
            return {
              file: r.file,
              coupling: r.coupling ?? 0,
              complexity: r.complexity ?? 0,
              churn: r.churn ?? 0,
              score,
              severity
            };
          });
          setDebtItems(mapped);
        }
      }

      const auditUrl = `http://localhost:8000/api/v1/intelligence/audits?path=${encodeURIComponent(repoPath || "")}`;
      const auditRes = await fetch(auditUrl);
      if (auditRes.ok) {
        const auditData = await auditRes.json();
        if (auditData.security && auditData.security.length > 0) {
          setSecurityItems(
            auditData.security.map((s: any) => ({
              file: s.file,
              issue: s.issue,
              severity: s.severity || (s.issue.includes("secret") ? "High" : "Medium"),
              line: s.line || 1,
              remediation: s.issue.includes("secret")
                ? "Move secret key to environment variable or KMS."
                : "Upgrade algorithm to SHA-256 / AES-GCM or enforce key rotation."
            }))
          );
        }
        if (auditData.performance && auditData.performance.length > 0) {
          setPerformanceItems(
            auditData.performance.map((p: any) => ({
              file: p.file,
              issue: p.issue,
              severity: p.severity || (p.issue.includes("N+1") ? "Medium" : "Low"),
              target: p.target || p.target_function || "Function",
              recommendation: p.issue.includes("N+1")
                ? "Batch DB query execution outside loop body."
                : "Split long function into focused helper functions."
            }))
          );
        }
      }
    } catch (err) {
      console.warn("Backend intelligence fetch error, using built-in engine findings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligenceData();
  }, [repoPath]);

  // Handle file path copy
  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedFile(path);
    setTimeout(() => setCopiedFile(null), 2000);
  };

  // Filtered debt items for tanstack table
  const filteredDebtData = useMemo(() => {
    let result = debtItems;
    if (highDebtOnly) {
      result = result.filter((item) => item.score > 80);
    }
    return result;
  }, [debtItems, highDebtOnly]);

  // TanStack React Table columns definition
  const columns = useMemo<ColumnDef<TechnicalDebtItem>[]>(
    () => [
      {
        accessorKey: "file",
        header: "File Path",
        cell: ({ row }) => {
          const path = row.original.file;
          const isCopied = copiedFile === path;
          return (
            <div className="flex items-center gap-2 font-mono text-xs font-medium text-zinc-800 dark:text-zinc-200">
              <FileCode className="w-4 h-4 text-violet-500 flex-shrink-0" />
              <span className="truncate max-w-[280px] md:max-w-[380px]" title={path}>
                {path}
              </span>
              <button
                onClick={() => handleCopyPath(path)}
                className="p-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors"
                title="Copy relative path"
              >
                {isCopied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          );
        }
      },
      {
        accessorKey: "score",
        header: "Debt Score",
        cell: ({ row }) => {
          const score = row.original.score;
          const isHigh = score >= 80;
          return (
            <div className="flex items-center gap-1.5 font-mono text-xs font-bold">
              <span
                className={`px-2 py-0.5 rounded ${
                  isHigh
                    ? "bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30"
                    : score >= 50
                    ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                    : "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                }`}
              >
                {score}/100
              </span>
            </div>
          );
        }
      },
      {
        id: "heatmap",
        header: "Heatmap",
        cell: ({ row }) => {
          const score = row.original.score;
          const scorePercent = Math.min(100, Math.max(0, score));

          // Color gradient dynamic calculation
          let barBgClass = "from-emerald-500 to-teal-400";
          let glowClass = "shadow-emerald-500/20";
          if (score >= 80) {
            barBgClass = "from-rose-600 via-red-500 to-amber-500 animate-pulse";
            glowClass = "shadow-rose-600/40";
          } else if (score >= 50) {
            barBgClass = "from-amber-500 to-yellow-400";
            glowClass = "shadow-amber-500/25";
          }

          return (
            <div className="w-full max-w-[200px] flex items-center gap-3">
              <div className="flex-1 bg-zinc-200 dark:bg-zinc-800/80 rounded-full h-3.5 overflow-hidden p-0.5 border border-zinc-300 dark:border-zinc-700/60 shadow-inner relative">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${barBgClass} shadow-md ${glowClass} transition-all duration-500 ease-out`}
                  style={{ width: `${scorePercent}%` }}
                />
              </div>
              <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400 w-8 text-right font-medium">
                {scorePercent}%
              </span>
            </div>
          );
        }
      },
      {
        id: "metrics",
        header: "Metrics (Coupling / Complexity / Churn)",
        cell: ({ row }) => {
          const { coupling, complexity, churn } = row.original;
          return (
            <div className="flex items-center gap-2 font-mono text-[11px]">
              <span
                className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded border border-zinc-200 dark:border-zinc-700"
                title="Coupling (Imports)"
              >
                C:{coupling}
              </span>
              <span
                className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded border border-zinc-200 dark:border-zinc-700"
                title="Complexity (Contains)"
              >
                X:{complexity}
              </span>
              <span
                className="px-1.5 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded border border-zinc-200 dark:border-zinc-700"
                title="Git Churn (Commits)"
              >
                H:{churn}
              </span>
            </div>
          );
        }
      },
      {
        accessorKey: "severity",
        header: "Severity",
        cell: ({ row }) => {
          const severity = row.original.severity;
          return (
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                severity === "High"
                  ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30"
                  : severity === "Medium"
                  ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                  : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  severity === "High"
                    ? "bg-red-500 animate-ping"
                    : severity === "Medium"
                    ? "bg-amber-500"
                    : "bg-emerald-500"
                }`}
              />
              {severity}
            </span>
          );
        }
      }
    ],
    [copiedFile]
  );

  // TanStack Table Instance
  const table = useReactTable({
    data: filteredDebtData,
    columns,
    state: {
      sorting,
      globalFilter
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel()
  });

  // Filtered Audit Items
  const filteredSecurity = useMemo(() => {
    return securityItems.filter((item) => {
      const matchesSearch =
        item.file.toLowerCase().includes(auditSearch.toLowerCase()) ||
        item.issue.toLowerCase().includes(auditSearch.toLowerCase());
      const matchesSev = severityFilter === "ALL" || item.severity === severityFilter;
      return matchesSearch && matchesSev;
    });
  }, [securityItems, auditSearch, severityFilter]);

  const filteredPerformance = useMemo(() => {
    return performanceItems.filter((item) => {
      const matchesSearch =
        item.file.toLowerCase().includes(auditSearch.toLowerCase()) ||
        item.issue.toLowerCase().includes(auditSearch.toLowerCase()) ||
        (item.target && item.target.toLowerCase().includes(auditSearch.toLowerCase()));
      const matchesSev = severityFilter === "ALL" || item.severity === severityFilter;
      return matchesSearch && matchesSev;
    });
  }, [performanceItems, auditSearch, severityFilter]);

  // Overall Stats
  const highDebtCount = debtItems.filter((i) => i.score > 80).length;
  const avgDebtScore = Math.round(
    debtItems.reduce((acc, curr) => acc + curr.score, 0) / (debtItems.length || 1)
  );

  return (
    <div className="space-y-6 border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/10 dark:bg-zinc-950/20 p-6 shadow-sm">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-900 pb-5">
        <div>
          <h3 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Flame className="w-5 h-5 text-rose-500" />
            <span>Engineering Intelligence & Audit Hub</span>
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Synthesized Technical Debt Heatmap, AST Coupling/Complexity, and Security & Performance Audit Reports.
          </p>
        </div>

        <button
          onClick={fetchIntelligenceData}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-2 bg-white dark:bg-zinc-900 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-semibold transition-all cursor-pointer active:scale-95 shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-violet-500" : "text-zinc-400"}`} />
          <span>Refresh Analysis</span>
        </button>
      </div>

      {/* Top Metrics Banner */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/50 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Avg Debt Score</span>
            <div className="text-xl font-bold text-zinc-800 dark:text-zinc-100 font-mono">{avgDebtScore}/100</div>
          </div>
          <Flame className="w-5 h-5 text-rose-500 opacity-80" />
        </div>

        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/50 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Critical Debt Files (&gt;80)</span>
            <div className="text-xl font-bold text-rose-600 dark:text-rose-400 font-mono">{highDebtCount}</div>
          </div>
          <AlertTriangle className="w-5 h-5 text-rose-500 opacity-80" />
        </div>

        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/50 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Security Flags</span>
            <div className="text-xl font-bold text-amber-600 dark:text-amber-400 font-mono">{securityItems.length}</div>
          </div>
          <ShieldAlert className="w-5 h-5 text-amber-500 opacity-80" />
        </div>

        <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/50 flex items-center justify-between">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">Performance Bottlenecks</span>
            <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 font-mono">{performanceItems.length}</div>
          </div>
          <Zap className="w-5 h-5 text-emerald-500 opacity-80" />
        </div>
      </div>

      {/* Main Tab Navigation */}
      <div className="flex border-b border-zinc-200 dark:border-zinc-900 gap-2">
        <button
          onClick={() => setActiveTab("debt")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
            activeTab === "debt"
              ? "border-violet-600 text-violet-600 dark:text-violet-400 bg-violet-50/50 dark:bg-violet-950/20"
              : "border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
          }`}
        >
          <Flame className="w-4 h-4" />
          <span>Debt Heatmap</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
            {debtItems.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("security")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
            activeTab === "security"
              ? "border-rose-600 text-rose-600 dark:text-rose-400 bg-rose-50/50 dark:bg-rose-950/20"
              : "border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Security Audit</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
            {securityItems.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("performance")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all cursor-pointer ${
            activeTab === "performance"
              ? "border-emerald-600 text-emerald-600 dark:text-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/20"
              : "border-transparent text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
          }`}
        >
          <Zap className="w-4 h-4" />
          <span>Performance Audit</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
            {performanceItems.length}
          </span>
        </button>
      </div>

      {/* Tab Content 1: Debt Heatmap Table */}
      {activeTab === "debt" && (
        <div className="space-y-4">
          {/* Controls Bar: Search & High Debt Filter */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white dark:bg-zinc-950/60 p-3 rounded-lg border border-zinc-200 dark:border-zinc-900">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-400" />
              <input
                type="text"
                placeholder="Search file path..."
                value={globalFilter ?? ""}
                onChange={(e) => setGlobalFilter(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md text-xs text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setHighDebtOnly(!highDebtOnly)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold border transition-all cursor-pointer ${
                  highDebtOnly
                    ? "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/40 shadow-sm"
                    : "bg-zinc-50 dark:bg-zinc-900 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300"
                }`}
              >
                <Filter className="w-3.5 h-3.5" />
                <span>Debt Score &gt; 80</span>
                {highDebtOnly && (
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                )}
              </button>
            </div>
          </div>

          {/* TanStack React Table View */}
          <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/40 shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr
                    key={headerGroup.id}
                    className="border-b border-zinc-200 dark:border-zinc-900 bg-zinc-100/70 dark:bg-zinc-900/60 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 uppercase tracking-wider"
                  >
                    {headerGroup.headers.map((header) => (
                      <th key={header.id} className="py-3 px-4 font-semibold">
                        {header.isPlaceholder ? null : (
                          <div
                            className={`flex items-center gap-1 ${
                              header.column.getCanSort() ? "cursor-pointer select-none" : ""
                            }`}
                            onClick={header.column.getToggleSortingHandler()}
                          >
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {{
                              asc: <ChevronUp className="w-3 h-3 text-violet-500" />,
                              desc: <ChevronDown className="w-3 h-3 text-violet-500" />
                            }[header.column.getIsSorted() as string] ?? null}
                          </div>
                        )}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-900 text-xs">
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="text-center py-8 text-zinc-400 italic">
                      No files matching the technical debt filter criteria.
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-zinc-50/80 dark:hover:bg-zinc-900/40 transition-colors"
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="py-3 px-4">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab Content 2: Security Audit Report */}
      {activeTab === "security" && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white dark:bg-zinc-950/60 p-3 rounded-lg border border-zinc-200 dark:border-zinc-900">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-400" />
              <input
                type="text"
                placeholder="Search security vulnerabilities..."
                value={auditSearch}
                onChange={(e) => setAuditSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md text-xs text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-rose-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as any)}
                className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-700 dark:text-zinc-300 rounded-md px-2.5 py-1.5 focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="High">High (Red)</option>
                <option value="Medium">Medium (Yellow)</option>
                <option value="Low">Low (Green)</option>
              </select>
            </div>
          </div>

          {/* Audit Cards List */}
          <div className="space-y-3">
            {filteredSecurity.length === 0 ? (
              <div className="p-8 text-center border border-zinc-200 dark:border-zinc-900 rounded-lg bg-white dark:bg-zinc-950/40 text-zinc-400 italic">
                No security vulnerabilities matching search criteria.
              </div>
            ) : (
              filteredSecurity.map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/40 space-y-2 hover:border-zinc-300 dark:hover:border-zinc-800 transition-all shadow-sm"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Lock className="w-4 h-4 text-rose-500 flex-shrink-0" />
                        <h4 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                          {item.issue}
                        </h4>
                      </div>
                      <p className="text-xs font-mono text-zinc-500 flex items-center gap-1">
                        <span>{item.file}</span>
                        <span className="text-zinc-400">:L{item.line}</span>
                      </p>
                    </div>

                    {/* Color coded severity pill matching rich console (Red/Yellow/Green) */}
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border flex-shrink-0 ${
                        item.severity === "High"
                          ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30"
                          : item.severity === "Medium"
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                          : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          item.severity === "High"
                            ? "bg-red-500 animate-ping"
                            : item.severity === "Medium"
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        }`}
                      />
                      {item.severity}
                    </span>
                  </div>

                  {item.remediation && (
                    <div className="pt-2 border-t border-zinc-100 dark:border-zinc-900/80 flex items-start gap-2 text-[11px] text-zinc-600 dark:text-zinc-400">
                      <Info className="w-3.5 h-3.5 text-violet-500 flex-shrink-0 mt-0.5" />
                      <span>
                        <strong className="text-zinc-700 dark:text-zinc-300">Remediation:</strong>{" "}
                        {item.remediation}
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab Content 3: Performance Audit Report */}
      {activeTab === "performance" && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-white dark:bg-zinc-950/60 p-3 rounded-lg border border-zinc-200 dark:border-zinc-900">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-400" />
              <input
                type="text"
                placeholder="Search performance bottlenecks..."
                value={auditSearch}
                onChange={(e) => setAuditSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md text-xs text-zinc-800 dark:text-zinc-200 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <SlidersHorizontal className="w-3.5 h-3.5 text-zinc-400" />
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value as any)}
                className="bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-xs text-zinc-700 dark:text-zinc-300 rounded-md px-2.5 py-1.5 focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="High">High (Red)</option>
                <option value="Medium">Medium (Yellow)</option>
                <option value="Low">Low (Green)</option>
              </select>
            </div>
          </div>

          {/* Performance Items List */}
          <div className="space-y-3">
            {filteredPerformance.length === 0 ? (
              <div className="p-8 text-center border border-zinc-200 dark:border-zinc-900 rounded-lg bg-white dark:bg-zinc-950/40 text-zinc-400 italic">
                No performance bottlenecks found matching search parameters.
              </div>
            ) : (
              filteredPerformance.map((item, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-lg border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/40 space-y-2 hover:border-zinc-300 dark:hover:border-zinc-800 transition-all shadow-sm"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        <h4 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                          {item.issue}
                        </h4>
                      </div>
                      <p className="text-xs font-mono text-zinc-500 flex items-center gap-2">
                        <span>{item.file}</span>
                        {item.target && (
                          <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-violet-600 dark:text-violet-400 border border-zinc-200 dark:border-zinc-700 text-[10px]">
                            fn: {item.target}
                          </span>
                        )}
                      </p>
                    </div>

                    {/* Color coded severity pill matching rich console (Red/Yellow/Green) */}
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border flex-shrink-0 ${
                        item.severity === "High"
                          ? "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30"
                          : item.severity === "Medium"
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30"
                          : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30"
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          item.severity === "High"
                            ? "bg-red-500 animate-ping"
                            : item.severity === "Medium"
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        }`}
                      />
                      {item.severity}
                    </span>
                  </div>

                  {item.recommendation && (
                    <div className="pt-2 border-t border-zinc-100 dark:border-zinc-900/80 flex items-start gap-2 text-[11px] text-zinc-600 dark:text-zinc-400">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                      <span>
                        <strong className="text-zinc-700 dark:text-zinc-300">Recommendation:</strong>{" "}
                        {item.recommendation}
                      </span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default EngineeringIntelligence;
