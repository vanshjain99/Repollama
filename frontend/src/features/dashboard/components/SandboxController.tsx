import React, { useEffect, useState } from "react";
import {
  Play,
  Square,
  RefreshCw,
  Server,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
  Cpu,
  Layers
} from "lucide-react";
import { useAnalysis } from "../../../context/AnalysisContext";

interface SandboxStatus {
  docker_available: boolean;
  status: "running" | "stopped" | "booting" | "error";
  container_id?: string | null;
  host_port?: number | null;
  stack?: string | null;
  language?: string | null;
  warnings?: string[];
  message?: string;
}

export const SandboxController: React.FC = () => {
  const { repoPath } = useAnalysis();
  const [status, setStatus] = useState<SandboxStatus>({
    docker_available: true,
    status: "stopped",
    container_id: null,
    host_port: null,
    stack: null,
    warnings: [],
  });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/sandbox/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // Backend offline or unreachable
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleBootSandbox = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/sandbox/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: repoPath || "." }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setStatus({
          docker_available: true,
          status: "running",
          container_id: data.container_id,
          host_port: data.host_port,
          stack: data.stack_info?.stack,
          language: data.stack_info?.language,
          warnings: data.warnings || [],
          message: data.message,
        });
      } else {
        setErrorMsg(data.message || "Failed to boot sandbox");
        setStatus((prev) => ({
          ...prev,
          status: "error",
          docker_available: data.docker_available ?? prev.docker_available,
          warnings: data.warnings || [],
        }));
      }
    } catch (err: any) {
      setErrorMsg("Network error connecting to backend sandbox API");
    } finally {
      setLoading(false);
    }
  };

  const handleShutdownSandbox = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch("http://localhost:8000/api/v1/sandbox/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ container_id: status.container_id }),
      });
      if (res.ok) {
        setStatus({
          docker_available: status.docker_available,
          status: "stopped",
          container_id: null,
          host_port: null,
          stack: null,
          warnings: [],
        });
      }
    } catch (err: any) {
      setErrorMsg("Failed to shutdown sandbox");
    } finally {
      setLoading(false);
    }
  };

  const isRunning = status.status === "running";

  return (
    <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/30 dark:bg-zinc-950/40 p-6 space-y-6 shadow-sm hover:border-zinc-300 dark:hover:border-zinc-800/80 transition-all duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500">
            <Server className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Runtime Sandbox Controller
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Isolated Docker runtime environment & port proxy
            </p>
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          {isRunning ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Container Running
            </span>
          ) : status.status === "error" ? (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <AlertTriangle className="w-3 h-3" />
              Error
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-300 dark:border-zinc-700">
              <span className="w-1.5 h-1.5 rounded-full bg-zinc-400"></span>
              Stopped
            </span>
          )}
        </div>
      </div>

      {/* Warnings & Messages */}
      {errorMsg && (
        <div className="p-3.5 rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/40 text-red-700 dark:text-red-300 text-xs flex items-start gap-2.5">
          <ShieldAlert className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Sandbox Boot Alert</p>
            <p className="mt-0.5 opacity-90">{errorMsg}</p>
          </div>
        </div>
      )}

      {status.warnings && status.warnings.length > 0 && (
        <div className="p-3.5 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/40 text-amber-700 dark:text-amber-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Configuration Warning</p>
            {status.warnings.map((w, idx) => (
              <p key={idx} className="mt-0.5">{w}</p>
            ))}
          </div>
        </div>
      )}

      {!status.docker_available && (
        <div className="p-3.5 rounded-lg bg-zinc-200/50 dark:bg-zinc-900/50 border border-zinc-300 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 text-xs">
          <p className="font-medium text-zinc-800 dark:text-zinc-200">Docker Daemon Offline</p>
          <p className="mt-1">
            Docker is not running on this host. You can still test sandbox configuration detection or start Docker Desktop to enable real container sandboxing.
          </p>
        </div>
      )}

      {/* Sandbox Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-3.5 rounded-lg bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-900 space-y-1">
          <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-1">
            <Layers className="w-3 h-3 text-indigo-400" /> Stack Type
          </span>
          <p className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">
            {status.stack || "Detected on boot"}
          </p>
        </div>

        <div className="p-3.5 rounded-lg bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-900 space-y-1">
          <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-1">
            <Cpu className="w-3 h-3 text-violet-400" /> Container ID
          </span>
          <p className="text-xs font-mono font-semibold text-zinc-800 dark:text-zinc-200 truncate" title={status.container_id || "None"}>
            {status.container_id ? status.container_id.substring(0, 12) : "Not active"}
          </p>
        </div>

        <div className="p-3.5 rounded-lg bg-white dark:bg-zinc-900/40 border border-zinc-200 dark:border-zinc-900 space-y-1">
          <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex items-center gap-1">
            <ExternalLink className="w-3 h-3 text-emerald-400" /> Host Port Link
          </span>
          {status.host_port ? (
            <a
              href={`http://localhost:${status.host_port}`}
              target="_blank"
              rel="noreferrer"
              className="text-xs font-mono font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
            >
              http://localhost:{status.host_port}
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : (
            <p className="text-xs font-mono text-zinc-400">Unassigned</p>
          )}
        </div>
      </div>

      {/* Control Buttons */}
      <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-zinc-200 dark:border-zinc-900">
        <div className="text-xs text-zinc-500 font-mono">
          Endpoint: <span className="text-zinc-700 dark:text-zinc-300">/api/v1/sandbox/start</span>
        </div>

        <div className="flex gap-3">
          {isRunning ? (
            <button
              onClick={handleShutdownSandbox}
              disabled={loading}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-xs font-semibold transition-all duration-200 shadow-md shadow-red-600/20 flex items-center gap-2 cursor-pointer active:scale-95 disabled:opacity-50"
            >
              {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Square className="w-3.5 h-3.5 fill-white" />}
              <span>Shutdown Sandbox</span>
            </button>
          ) : (
            <button
              onClick={handleBootSandbox}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-all duration-200 shadow-md shadow-emerald-600/20 flex items-center gap-2 cursor-pointer active:scale-95 disabled:opacity-50"
            >
              {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-white" />}
              <span>Boot Sandbox</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default SandboxController;
