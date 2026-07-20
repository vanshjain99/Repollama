import React, { useState, useEffect, useRef } from "react";
import { Terminal, RefreshCw, Copy, Check, ShieldCheck, FileText, AlertCircle } from "lucide-react";

export const AuditLogViewer: React.FC = () => {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const terminalEndRef = useRef<HTMLDivElement | null>(null);

  const fetchAuditLog = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/governance/audit-log?limit=50");
      if (!res.ok) {
        throw new Error(`Failed to fetch audit log: HTTP ${res.status}`);
      }
      const data = await res.json();
      setLogs(data.lines || []);
    } catch (err: any) {
      console.error("Audit log fetch error:", err);
      setError(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLog();

    let interval: any = null;
    if (autoRefresh) {
      interval = setInterval(() => {
        fetchAuditLog();
      }, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  const handleCopyLogs = () => {
    if (logs.length === 0) return;
    navigator.clipboard.writeText(logs.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const parseLogLine = (line: string) => {
    // Expected format: [2026-07-20 15:00:00] ACTION: CI Check Triggered ...
    const match = line.match(/^\[(.*?)\]\s*(.*)$/);
    if (match) {
      return {
        timestamp: match[1],
        content: match[2],
      };
    }
    return { timestamp: null, content: line };
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm space-y-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-zinc-800 text-zinc-100 flex items-center justify-center font-mono">
            <FileText className="w-4.5 h-4.5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Enterprise Audit Log Viewer
              </h3>
              <span className="px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 font-mono text-[10px] border border-zinc-200 dark:border-zinc-700">
                Last 50 lines
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Read-only log stream from <code className="font-mono text-indigo-500">.repollama_data/enterprise_audit.log</code>
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 cursor-pointer mr-2 select-none">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-zinc-300 text-indigo-600 focus:ring-indigo-500"
            />
            <span>Auto-refresh</span>
          </label>

          <button
            type="button"
            onClick={handleCopyLogs}
            disabled={logs.length === 0}
            className="p-2 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 transition-colors cursor-pointer active:scale-95 disabled:opacity-40"
            title="Copy logs to clipboard"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
          </button>

          <button
            type="button"
            onClick={fetchAuditLog}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 font-medium text-xs transition-colors cursor-pointer active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Audit Log Terminal Screen */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-zinc-300 shadow-inner overflow-hidden flex flex-col h-[320px]">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-zinc-800 text-[11px] text-zinc-500">
          <span className="flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            enterprise_audit.log
          </span>
          <span>{logs.length} entries</span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1.5 pr-2 custom-scrollbar">
          {logs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-zinc-500 italic text-center p-6 space-y-2">
              <ShieldCheck className="w-8 h-8 opacity-40 text-zinc-400" />
              <p>No audit log entries recorded yet.</p>
              <p className="text-[11px]">Run a Gatekeeper check above to generate audit logs.</p>
            </div>
          ) : (
            logs.map((line, idx) => {
              const { timestamp, content } = parseLogLine(line);
              return (
                <div
                  key={idx}
                  className="flex items-start gap-2 py-0.5 px-1.5 rounded hover:bg-zinc-900/80 transition-colors"
                >
                  <span className="text-zinc-600 select-none text-[10px] w-6 text-right font-mono flex-shrink-0 pt-0.5">
                    {idx + 1}
                  </span>

                  {timestamp && (
                    <span className="text-indigo-400/90 font-mono text-[11px] flex-shrink-0 select-none">
                      [{timestamp}]
                    </span>
                  )}

                  <span
                    className={`flex-1 break-all ${
                      content.includes("ACTION:")
                        ? "text-zinc-200"
                        : content.includes("ERROR")
                        ? "text-red-400"
                        : "text-zinc-400"
                    }`}
                  >
                    {content}
                  </span>
                </div>
              );
            })
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
};

export default AuditLogViewer;
