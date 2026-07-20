import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Command } from "@tauri-apps/api/shell";
import { Server, RefreshCw, AlertTriangle, ShieldCheck } from "lucide-react";
import MainLayout from "./components/layout/MainLayout";
import Dashboard from "./features/dashboard/Dashboard";
import ArchitectureView from "./features/architecture/ArchitectureView";
import SandboxView from "./features/sandbox/SandboxView";
import AIChatView from "./features/chat/AIChatView";
import SettingsView from "./features/settings/SettingsView";
import GovernanceView from "./features/governance/GovernanceView";
import HealthCheck from "./features/onboarding/HealthCheck";
import { AnalysisProvider } from "./context/AnalysisContext";

export async function ping_server(): Promise<boolean> {
  try {
    const res = await fetch("http://localhost:8000/api/v1/health");
    if (res.ok) {
      const data = await res.json();
      return data.status === "healthy" || res.status === 200;
    }
    return false;
  } catch {
    return false;
  }
}

function App() {
  const [backendReady, setBackendReady] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [attemptCount, setAttemptCount] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isHealthPassed, setIsHealthPassed] = useState<boolean>(false);

  const initBackend = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    setAttemptCount(0);

    // Check if server is already running
    let isHealthy = await ping_server();

    if (!isHealthy) {
      try {
        const command = Command.sidecar("bin/repollama-engine");
        await command.spawn();
      } catch (err) {
        console.warn("Tauri sidecar spawn notice (browser/dev mode active):", err);
      }

      // Wait for backend to pass health check
      const maxAttempts = 30;
      for (let i = 1; i <= maxAttempts; i++) {
        setAttemptCount(i);
        isHealthy = await ping_server();
        if (isHealthy) break;
        await new Promise((r) => setTimeout(r, 1000));
      }
    }

    if (isHealthy) {
      setBackendReady(true);
      setIsLoading(false);
    } else {
      setBackendReady(false);
      setIsLoading(false);
      setErrorMsg("Failed to connect to Repollama Engine on http://localhost:8000.");
    }
  };

  useEffect(() => {
    initBackend();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-slate-100 font-sans p-6">
        <div className="relative flex items-center justify-center mb-8">
          <div className="absolute inset-0 rounded-full bg-cyan-500/20 blur-xl animate-pulse" />
          <div className="relative p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl">
            <Server className="w-12 h-12 text-cyan-400 animate-bounce" />
          </div>
        </div>

        <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent mb-2">
          Repollama Enterprise Control Center
        </h1>
        <p className="text-slate-400 text-sm mb-6 font-medium">
          Starting and connecting to Python Engine Sidecar...
        </p>

        <div className="flex items-center space-x-3 bg-slate-900/80 px-4 py-2.5 rounded-full border border-slate-800 text-xs text-slate-300 mb-4 shadow-inner">
          <RefreshCw className="w-4 h-4 text-cyan-400 animate-spin" />
          <span>
            Health checking <code className="text-cyan-300 font-mono">http://localhost:8000/api/v1/health</code>
            {attemptCount > 0 && ` (Attempt ${attemptCount}/30)`}
          </span>
        </div>

        <div className="w-64 h-1.5 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 animate-pulse w-full" />
        </div>
      </div>
    );
  }

  if (!backendReady && errorMsg) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-950 text-slate-100 font-sans p-6">
        <div className="p-5 rounded-2xl bg-red-950/40 border border-red-800/60 mb-6 max-w-md text-center shadow-xl">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-red-300 mb-1">Backend Connection Failed</h2>
          <p className="text-xs text-red-200/80">{errorMsg}</p>
        </div>

        <div className="flex items-center space-x-4">
          <button
            onClick={initBackend}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm transition-all shadow-lg shadow-cyan-900/40 active:scale-95 cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry Connection</span>
          </button>

          <button
            onClick={() => setBackendReady(true)}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-sm transition-all border border-slate-700 cursor-pointer"
          >
            <ShieldCheck className="w-4 h-4 text-slate-400" />
            <span>Bypass & Open Health Check</span>
          </button>
        </div>
      </div>
    );
  }

  if (!isHealthPassed) {
    return <HealthCheck onProceed={() => setIsHealthPassed(true)} />;
  }

  return (
    <BrowserRouter>
      <AnalysisProvider>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="architecture" element={<ArchitectureView />} />
            <Route path="sandbox" element={<SandboxView />} />
            <Route path="governance" element={<GovernanceView />} />
            <Route path="chat" element={<AIChatView />} />
            <Route path="settings" element={<SettingsView />} />
          </Route>
        </Routes>
      </AnalysisProvider>
    </BrowserRouter>
  );
}

export default App;
