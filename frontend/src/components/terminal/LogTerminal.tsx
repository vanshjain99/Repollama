import React, { useEffect, useRef, useState } from "react";
import { Terminal as TerminalIcon, Trash2, ArrowDown, CheckCircle2, AlertCircle, RefreshCw, MinusCircle } from "lucide-react";
import { useAnalysis, type AnalysisStatus } from "../../context/AnalysisContext";

interface LogTerminalProps {
  heightClass?: string;
  showTitle?: boolean;
}

export const LogTerminal: React.FC<LogTerminalProps> = ({
  heightClass = "h-80",
  showTitle = true,
}) => {
  const { logs, setLogs, analysisStatus } = useAnalysis();
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll effect
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, autoScroll]);

  const handleClearLogs = () => {
    setLogs([]);
  };

  const renderStatusBadge = (status: AnalysisStatus) => {
    switch (status) {
      case "Analyzing":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/30">
            <RefreshCw className="w-3 h-3 animate-spin" />
            Analyzing
          </span>
        );
      case "Complete":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3 h-3" />
            Complete
          </span>
        );
      case "Error":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/30">
            <AlertCircle className="w-3 h-3" />
            Error
          </span>
        );
      case "Idle":
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
            <MinusCircle className="w-3 h-3" />
            Idle
          </span>
        );
    }
  };

  const formatLogLine = (log: string, index: number) => {
    let colorClass = "text-zinc-300";
    if (log.startsWith("[System]")) {
      if (log.includes("Error") || log.includes("failed") || log.includes("Failed")) {
        colorClass = "text-red-400 font-semibold bg-red-950/20 px-1 py-0.5 rounded";
      } else if (log.includes("Warning") || log.includes("Notice")) {
        colorClass = "text-yellow-400 font-semibold bg-yellow-950/20 px-1 py-0.5 rounded";
      } else {
        colorClass = "text-sky-400 font-medium";
      }
    } else if (log.startsWith("[AST]")) {
      colorClass = "text-emerald-400";
    } else if (log.startsWith("[MacroCompiler]")) {
      colorClass = "text-cyan-400 font-medium";
    } else if (log.startsWith("[Pipeline]")) {
      colorClass = "text-violet-400 font-bold bg-violet-950/20 px-1 py-0.5 rounded";
    }

    return (
      <div key={index} className={`leading-relaxed whitespace-pre-wrap ${colorClass}`}>
        {log}
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-2xl overflow-hidden flex flex-col font-mono text-xs">
      {/* Terminal Toolbar */}
      <div className="px-4 py-2.5 bg-zinc-900/90 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
            <div className="w-3 h-3 rounded-full bg-emerald-500/80"></div>
          </div>
          {showTitle && (
            <span className="text-zinc-400 font-medium text-xs flex items-center gap-1.5 ml-2">
              <TerminalIcon className="w-3.5 h-3.5 text-violet-400" />
              Live Execution Terminal
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {renderStatusBadge(analysisStatus)}

          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-1 rounded text-[11px] flex items-center gap-1 border transition-colors cursor-pointer ${
              autoScroll
                ? "bg-violet-950/50 text-violet-300 border-violet-800/60"
                : "bg-zinc-800/60 text-zinc-400 border-zinc-700 hover:bg-zinc-800"
            }`}
            title="Toggle Auto-Scroll"
          >
            <ArrowDown className={`w-3 h-3 ${autoScroll ? "text-violet-400" : "text-zinc-500"}`} />
            Auto-Scroll
          </button>

          <button
            onClick={handleClearLogs}
            disabled={logs.length === 0}
            className="p-1 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            title="Clear Logs"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Content Area */}
      <div
        ref={containerRef}
        className={`${heightClass} p-4 overflow-y-auto space-y-1 text-zinc-300 scrollbar-thin scrollbar-thumb-zinc-800 bg-zinc-950`}
      >
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 italic gap-2 py-8">
            <TerminalIcon className="w-8 h-8 text-zinc-700 opacity-60" />
            <span>Terminal ready. Select a repository and click &quot;Start Analysis&quot; to begin parsing.</span>
          </div>
        ) : (
          logs.map((log, index) => formatLogLine(log, index))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
};

export default LogTerminal;
