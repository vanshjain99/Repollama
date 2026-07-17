import React, { useState, useEffect, useRef } from "react";
import {
  FolderOpen,
  RefreshCw,
  Cpu,
  GitCommit,
  Database,
  Search,
  CheckCircle2,
  Clock,
  Terminal,
  Play,
  XCircle
} from "lucide-react";
import { open } from "@tauri-apps/plugin-dialog";

export const Dashboard: React.FC = () => {
  const [repoPath, setRepoPath] = useState<string>("");
  const [logs, setLogs] = useState<string[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  
  // Dashboard stats from stream completion
  const [astEntities, setAstEntities] = useState<string>("1,248");
  const commitsParsed = "432 commits";
  const [vectorStorage, setVectorStorage] = useState<string>("ChromaDB Ready");

  const [vectorStorageSub, setVectorStorageSub] = useState<string>("3,490 document chunk embeddings");

  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-scroll logs terminal to bottom
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs]);

  // Clean up EventSource connection on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSelectDirectory = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "Select Repository Workspace",
      });
      if (selected) {
        const path = Array.isArray(selected) ? selected[0] : selected;
        setRepoPath(path);
        // Clear old logs when a new path is selected
        setLogs([]);
      }
    } catch (err) {
      console.error("Failed to select directory:", err);
      setLogs((prev) => [...prev, `[System] Error: Failed to open directory picker: ${err}`]);
    }
  };

  const handleStartAnalysis = () => {
    if (!repoPath || isAnalyzing) return;

    setIsAnalyzing(true);
    setLogs([`[System] Connecting to analysis pipeline...`]);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sseUrl = `http://localhost:8000/api/v1/analyze/stream?path=${encodeURIComponent(repoPath)}`;
    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      const logMsg = event.data;
      setLogs((prev) => [...prev, logMsg]);

      // Dynamic stats extraction on analysis complete
      if (logMsg.startsWith("[System] Analysis complete.")) {
        const match = logMsg.match(/Nodes:\s*(\d+),\s*Edges:\s*(\d+),\s*Collection Size:\s*(\d+)/);
        if (match) {
          const nodes = parseInt(match[1], 10);
          const collectionSize = parseInt(match[3], 10);

          setAstEntities(nodes.toLocaleString());
          setVectorStorage("Active");
          setVectorStorageSub(`${collectionSize.toLocaleString()} document chunk embeddings`);
        }
      }

      if (logMsg === "[Pipeline] Analysis Complete!") {
        eventSource.close();
        setIsAnalyzing(false);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource error:", err);
      setLogs((prev) => [
        ...prev,
        `[System] Error: Connection lost or failed to start stream.`
      ]);
      eventSource.close();
      setIsAnalyzing(false);
    };
  };

  const handleCancelAnalysis = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsAnalyzing(false);
    setLogs((prev) => [...prev, `[System] Warning: Analysis canceled by user.`]);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome Hero */}
      <div className="relative overflow-hidden rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-gradient-to-br from-zinc-100 to-zinc-200 dark:from-zinc-900 dark:to-zinc-950 p-8 shadow-xl">
        <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-violet-600/5 dark:bg-violet-600/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-40 h-40 bg-indigo-600/5 dark:bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="max-w-2xl space-y-4">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-zinc-900 dark:text-transparent dark:bg-clip-text dark:bg-gradient-to-r dark:from-zinc-50 dark:via-zinc-100 dark:to-zinc-300">
            Understand your repository, instantly.
          </h2>
          <p className="text-sm text-zinc-650 dark:text-zinc-400 leading-relaxed">
            Repollama uses local semantic analysis, Git history mining, and custom embeddings to construct a local knowledge graph of your project. Select a repository to begin parsing.
          </p>
          
          <div className="pt-2 flex flex-wrap gap-4">
            <button
              onClick={handleSelectDirectory}
              className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-semibold transition-all duration-200 shadow-md shadow-violet-600/20 active:scale-[0.98] cursor-pointer"
            >
              <FolderOpen className="w-4 h-4" />
              <span>Select Repository</span>
            </button>
            <button 
              onClick={handleStartAnalysis}
              disabled={!repoPath || isAnalyzing}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all duration-200 cursor-pointer ${
                !repoPath || isAnalyzing
                  ? "bg-zinc-100 text-zinc-400 border-zinc-200 dark:bg-zinc-900/40 dark:text-zinc-600 dark:border-zinc-950 cursor-not-allowed"
                  : "bg-white hover:bg-zinc-100 text-zinc-700 border-zinc-200 hover:border-zinc-300 dark:bg-zinc-900 dark:hover:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-850 dark:hover:border-zinc-700"
              }`}
            >
              <RefreshCw className={`w-4 h-4 ${isAnalyzing ? "animate-spin text-violet-400" : "text-zinc-500 dark:text-zinc-400"}`} />
              <span>Rescan Directory</span>
            </button>
          </div>
        </div>
      </div>

      {/* Repository Selection and Analysis Controls */}
      <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/10 dark:bg-zinc-950/20 p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900 pb-4">
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-violet-500 dark:text-violet-400" />
            <span>Repository Analysis Control</span>
          </h3>
          {isAnalyzing && (
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-violet-500"></span>
            </span>
          )}
        </div>

        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="flex-1 w-full space-y-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Repository Path</label>
            <div className="flex gap-2">
              <input
                type="text"
                readOnly
                value={repoPath}
                placeholder="No repository selected"
                className="flex-1 px-4 py-2.5 bg-white dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-900 text-zinc-800 dark:text-zinc-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-violet-500/50 placeholder-zinc-400 dark:placeholder-zinc-600 font-mono"
              />
              <button
                onClick={handleSelectDirectory}
                className="px-4 py-2.5 bg-white hover:bg-zinc-100 dark:bg-zinc-900 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-lg text-sm font-medium border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 transition-all duration-200 flex items-center gap-2 cursor-pointer active:scale-95"
              >
                <FolderOpen className="w-4 h-4 text-zinc-500 dark:text-zinc-400" />
                <span>Browse...</span>
              </button>
            </div>
          </div>
          
          <div className="flex gap-2 w-full md:w-auto">
            {isAnalyzing ? (
              <button
                onClick={handleCancelAnalysis}
                className="flex-1 md:flex-initial px-6 py-2.5 bg-red-50 hover:bg-red-100 dark:bg-red-950/30 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 rounded-lg text-sm font-semibold border border-red-200 dark:border-red-900/30 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer active:scale-95"
              >
                <XCircle className="w-4 h-4" />
                <span>Cancel</span>
              </button>
            ) : (
              <button
                onClick={handleStartAnalysis}
                disabled={!repoPath || isAnalyzing}
                className={`flex-1 md:flex-initial px-6 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer shadow-md ${
                  !repoPath || isAnalyzing
                    ? "bg-zinc-100 text-zinc-400 border border-zinc-200 dark:bg-zinc-900/50 dark:text-zinc-600 dark:border-zinc-950 cursor-not-allowed shadow-none"
                    : "bg-violet-600 hover:bg-violet-500 text-white shadow-violet-600/10 active:scale-95"
                }`}
              >
                <Play className="w-4 h-4" />
                <span>Start Analysis</span>
              </button>
            )}
          </div>
        </div>

        {/* Live Execution Logs Terminal */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-505 dark:text-zinc-400 block">Live Execution Logs</label>
          <div className="h-64 rounded-lg bg-zinc-955 dark:bg-black/70 border border-zinc-200 dark:border-zinc-900 p-4 font-mono text-xs text-zinc-300 dark:text-zinc-400 overflow-y-auto flex flex-col space-y-1 scrollbar-thin">
            {logs.length === 0 ? (
              <div className="text-zinc-700 italic">No logs received yet. Select a repository and start analysis.</div>
            ) : (
              logs.map((log, index) => {
                let colorClass = "text-zinc-400";
                if (log.startsWith("[System]")) {
                  if (log.includes("Error")) {
                    colorClass = "text-red-400 font-semibold bg-red-950/10 px-1 py-0.5 rounded";
                  } else if (log.includes("Warning")) {
                    colorClass = "text-yellow-400 font-semibold bg-yellow-950/10 px-1 py-0.5 rounded";
                  } else {
                    colorClass = "text-blue-400 font-semibold";
                  }
                } else if (log.startsWith("[AST]")) {
                  colorClass = "text-emerald-400";
                } else if (log.startsWith("[Pipeline]")) {
                  colorClass = "text-violet-400 font-bold bg-violet-950/10 px-1 py-0.5 rounded";
                }
                return (
                  <div key={index} className={`leading-relaxed whitespace-pre-wrap ${colorClass}`}>
                    {log}
                  </div>
                );
              })
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/40 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-800/80 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider">AST Entities</span>
            <Cpu className="w-4 h-4 text-violet-500 dark:text-violet-400" />
          </div>
          <div>
            <div className="text-2xl font-bold text-zinc-800 dark:text-zinc-100">{astEntities}</div>
            <p className="text-xs text-zinc-500 mt-1">Classes, functions & modules</p>
          </div>
        </div>

        <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/40 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-800/80 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider">Git Miner Metrics</span>
            <GitCommit className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
          </div>
          <div>
            <div className="text-2xl font-bold text-zinc-800 dark:text-zinc-100">{commitsParsed}</div>
            <p className="text-xs text-zinc-500 mt-1">Parsed file churn & contributions</p>
          </div>
        </div>

        <div className="p-6 rounded-xl border border-zinc-200 dark:border-zinc-900 bg-white dark:bg-zinc-950/40 space-y-4 hover:border-zinc-300 dark:hover:border-zinc-800/80 transition-all duration-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-zinc-500 uppercase tracking-wider">Vector Storage</span>
            <Database className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
          </div>
          <div>
            <div className="text-2xl font-bold text-zinc-800 dark:text-zinc-100">{vectorStorage}</div>
            <p className="text-xs text-zinc-500 mt-1">{vectorStorageSub}</p>
          </div>
        </div>
      </div>

      {/* Main Grid: Recent Scans / System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* System Status Panel */}
        <div className="lg:col-span-2 border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/10 dark:bg-zinc-950/20 p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900 pb-4">
            <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">Index System Status</h3>
            <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              Operational
            </span>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between p-3.5 bg-white dark:bg-zinc-950/40 rounded-lg border border-zinc-200 dark:border-zinc-900 shadow-sm">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
                <div>
                  <h4 className="text-xs font-medium text-zinc-800 dark:text-zinc-200">AST Parser (Tree-sitter)</h4>
                  <p className="text-[10px] text-zinc-500">Deterministically mapped dependencies</p>
                </div>
              </div>
              <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">v1.0.0</span>
            </div>

            <div className="flex items-center justify-between p-3.5 bg-white dark:bg-zinc-950/40 rounded-lg border border-zinc-200 dark:border-zinc-900 shadow-sm">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
                <div>
                  <h4 className="text-xs font-medium text-zinc-800 dark:text-zinc-200">Git Miner Engine</h4>
                  <p className="text-[10px] text-zinc-500">Calculated file churn and developers history</p>
                </div>
              </div>
              <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">Active</span>
            </div>

            <div className="flex items-center justify-between p-3.5 bg-white dark:bg-zinc-950/40 rounded-lg border border-zinc-200 dark:border-zinc-900 shadow-sm">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
                <div>
                  <h4 className="text-xs font-medium text-zinc-800 dark:text-zinc-200">Graph Builder (NetworkX)</h4>
                  <p className="text-[10px] text-zinc-500">Entity linkages and structural index loaded</p>
                </div>
              </div>
              <span className="text-xs font-mono text-zinc-500 dark:text-zinc-400">Ready</span>
            </div>
          </div>
        </div>

        {/* Recent Scans Panel */}
        <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/10 dark:bg-zinc-950/20 p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900 pb-4">
            <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">Recent Tasks</h3>
            <span className="text-[10px] font-mono text-zinc-500">Active History</span>
          </div>

          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded bg-zinc-200 dark:bg-zinc-900 flex items-center justify-center border border-zinc-300 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 flex-shrink-0">
                <Search className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-zinc-800 dark:text-zinc-200 truncate">Semantics indexed</p>
                  <span className="text-[10px] text-zinc-500 flex items-center gap-1 font-mono">
                    <Clock className="w-3 h-3" /> 2m ago
                  </span>
                </div>
                <p className="text-[10px] text-zinc-500 truncate">/repollama-workspace</p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="w-7 h-7 rounded bg-zinc-200 dark:bg-zinc-900 flex items-center justify-center border border-zinc-300 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 flex-shrink-0">
                <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-zinc-800 dark:text-zinc-200 truncate">Git log extracted</p>
                  <span className="text-[10px] text-zinc-500 flex items-center gap-1 font-mono">
                    <Clock className="w-3 h-3" /> 10m ago
                  </span>
                </div>
                <p className="text-[10px] text-zinc-500 truncate">Commit log mining done</p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="w-7 h-7 rounded bg-zinc-200 dark:bg-zinc-900 flex items-center justify-center border border-zinc-300 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 flex-shrink-0">
                <Database className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium text-zinc-800 dark:text-zinc-200 truncate">Vectors loaded</p>
                  <span className="text-[10px] text-zinc-500 flex items-center gap-1 font-mono">
                    <Clock className="w-3 h-3" /> 1h ago
                  </span>
                </div>
                <p className="text-[10px] text-zinc-500 truncate">ChromaDB initialized</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

