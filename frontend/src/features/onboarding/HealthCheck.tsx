import React, { useEffect, useState, useCallback } from "react";
import {
  Server,
  Container,
  Cpu,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

export interface HealthStatus {
  backend: boolean;
  docker: boolean;
  ollama: boolean;
}

interface HealthCheckProps {
  onProceed: () => void;
}

export const HealthCheck: React.FC<HealthCheckProps> = ({ onProceed }) => {
  const [health, setHealth] = useState<HealthStatus>({
    backend: false,
    docker: false,
    ollama: false,
  });
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/health");
      if (res.ok) {
        const data = await res.json();
        setHealth({
          backend: Boolean(data.backend ?? true),
          docker: Boolean(data.docker),
          ollama: Boolean(data.ollama),
        });
      } else {
        setHealth({
          backend: false,
          docker: false,
          ollama: false,
        });
      }
    } catch {
      setHealth({
        backend: false,
        docker: false,
        ollama: false,
      });
    } finally {
      setIsRefreshing(false);
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(() => {
      fetchHealth();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchHealth]);

  const canProceed = health.backend && health.ollama;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-12 flex flex-col justify-between items-center relative overflow-hidden">
      {/* Background Subtle Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-cyan-600/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-10 w-96 h-96 bg-indigo-600/10 blur-[140px] rounded-full pointer-events-none" />

      {/* Header Section */}
      <div className="w-full max-w-3xl flex flex-col items-center text-center mt-6 z-10">
        <div className="flex items-center space-x-3 bg-slate-900/90 px-4 py-1.5 rounded-full border border-slate-800 text-xs font-semibold text-cyan-400 mb-6 shadow-inner">
          <ShieldCheck className="w-4 h-4" />
          <span>Pre-Flight Checklist & Onboarding</span>
        </div>

        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 via-cyan-200 to-indigo-300 bg-clip-text text-transparent mb-3">
          System Environment Health Check
        </h1>
        <p className="text-slate-400 text-sm md:text-base max-w-xl">
          Repollama runs locally on your machine. Verify backend core services, runtime Docker sandboxing, and local Ollama LLM before launching.
        </p>
      </div>

      {/* 3 Status Cards */}
      <div className="w-full max-w-3xl my-8 space-y-4 z-10">
        {/* Card 1: Repollama Core Engine */}
        <div
          className={`p-5 rounded-2xl border transition-all duration-300 flex items-start justify-between ${
            health.backend
              ? "bg-slate-900/80 border-emerald-500/40 shadow-lg shadow-emerald-950/20"
              : "bg-slate-900/40 border-red-500/40 shadow-lg shadow-red-950/20"
          }`}
        >
          <div className="flex items-start space-x-4">
            <div
              className={`p-3 rounded-xl ${
                health.backend ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
              }`}
            >
              <Server className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-slate-100 text-base">Repollama Core Engine</h3>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                    health.backend
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : "bg-red-500/10 text-red-400 border border-red-500/30"
                  }`}
                >
                  {health.backend ? "Connected" : "Disconnected"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Local Python sidecar process responsible for AST parsing, vector embeddings, and backend APIs.
              </p>
            </div>
          </div>
          <div>
            {health.backend ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-1" />
            ) : (
              <XCircle className="w-6 h-6 text-red-400 shrink-0 mt-1" />
            )}
          </div>
        </div>

        {/* Card 2: Docker Desktop */}
        <div
          className={`p-5 rounded-2xl border transition-all duration-300 flex items-start justify-between ${
            health.docker
              ? "bg-slate-900/80 border-emerald-500/40 shadow-lg shadow-emerald-950/20"
              : "bg-slate-900/40 border-slate-800 shadow-lg"
          }`}
        >
          <div className="flex items-start space-x-4">
            <div
              className={`p-3 rounded-xl ${
                health.docker ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
              }`}
            >
              <Container className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-slate-100 text-base">Docker Desktop</h3>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                    health.docker
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : "bg-red-500/10 text-red-400 border border-red-500/30"
                  }`}
                >
                  {health.docker ? "Connected" : "Missing / Stopped"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {health.docker
                  ? "Connected & ready for isolated runtime sandboxing."
                  : "Required for Runtime Sandboxing. Please start Docker Desktop."}
              </p>
            </div>
          </div>
          <div>
            {health.docker ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-1" />
            ) : (
              <XCircle className="w-6 h-6 text-red-400 shrink-0 mt-1" />
            )}
          </div>
        </div>

        {/* Card 3: Ollama Local LLM */}
        <div
          className={`p-5 rounded-2xl border transition-all duration-300 flex items-start justify-between ${
            health.ollama
              ? "bg-slate-900/80 border-emerald-500/40 shadow-lg shadow-emerald-950/20"
              : "bg-slate-900/40 border-red-500/40 shadow-lg shadow-red-950/20"
          }`}
        >
          <div className="flex items-start space-x-4">
            <div
              className={`p-3 rounded-xl ${
                health.ollama ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
              }`}
            >
              <Cpu className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-slate-100 text-base">Ollama Local LLM</h3>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                    health.ollama
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : "bg-red-500/10 text-red-400 border border-red-500/30"
                  }`}
                >
                  {health.ollama ? "Connected" : "Missing / Offline"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {health.ollama ? (
                  "Connected & ready for offline RAG & LLM code insights."
                ) : (
                  <span className="flex items-center space-x-1.5 text-red-300">
                    <span>Required for AI Insights. Run</span>
                    <code className="bg-slate-950 px-1.5 py-0.5 rounded text-cyan-300 font-mono text-[11px] border border-slate-800">
                      ollama run qwen2.5-coder
                    </code>
                    <span>in your terminal.</span>
                  </span>
                )}
              </p>
            </div>
          </div>
          <div>
            {health.ollama ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0 mt-1" />
            ) : (
              <XCircle className="w-6 h-6 text-red-400 shrink-0 mt-1" />
            )}
          </div>
        </div>
      </div>

      {/* Footer / Gatekeeper Actions */}
      <div className="w-full max-w-3xl flex flex-col space-y-4 z-10">
        {/* Docker Optional Warning Banner */}
        {!health.docker && canProceed && (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center space-x-3 shadow-lg">
            <AlertTriangle className="w-5 h-5 shrink-0 text-amber-400" />
            <span>
              Docker Desktop is not detected. Runtime Sandboxing features will be unavailable, but you may proceed with Core Analysis and AI Chat.
            </span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-slate-800/80">
          <div className="flex items-center space-x-3 text-xs text-slate-400">
            <button
              onClick={fetchHealth}
              disabled={isRefreshing}
              className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-cyan-400" : ""}`} />
              <span>Refresh Status</span>
            </button>

            {lastChecked && (
              <span className="text-[11px] text-slate-500 hidden sm:inline">
                Auto-checking every 3s (Last: {lastChecked.toLocaleTimeString()})
              </span>
            )}
          </div>

          <button
            onClick={onProceed}
            disabled={!canProceed}
            className={`flex items-center space-x-2 px-6 py-3 rounded-xl text-sm font-semibold transition-all shadow-lg cursor-pointer ${
              canProceed
                ? "bg-cyan-500 hover:bg-cyan-400 text-slate-950 shadow-cyan-900/50 active:scale-95"
                : "bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-60"
            }`}
          >
            <span>Proceed to Dashboard</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default HealthCheck;
