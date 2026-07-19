import React, { useEffect, useState } from "react";
import { Cpu, Database, Save, Activity, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";

export const SettingsView: React.FC = () => {
  const {
    ollamaModel,
    setOllamaModel,
    ollamaEndpoint,
    setOllamaEndpoint,
    contextWindow,
    setContextWindow,
    ignoredDirs,
    setIgnoredDirs,
    chunkSize,
    setChunkSize,
    incrementalCache,
    setIncrementalCache,
  } = useAnalysis();

  const [endpointInput, setEndpointInput] = useState(ollamaEndpoint);
  const [modelSelect, setModelSelect] = useState(ollamaModel);
  const [contextInput, setContextInput] = useState(contextWindow);
  const [ignoredInput, setIgnoredInput] = useState(ignoredDirs);
  const [chunkInput, setChunkInput] = useState(chunkSize);
  const [incrementalInput, setIncrementalInput] = useState(incrementalCache);

  const [connectionStatus, setConnectionStatus] = useState<"checking" | "connected" | "disconnected">("checking");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const checkHealth = async () => {
    setConnectionStatus("checking");
    try {
      const response = await fetch("http://localhost:8000/health");
      if (response.ok) {
        const data = await response.json();
        if (data.ollama && data.ollama.connected) {
          setConnectionStatus("connected");
        } else {
          setConnectionStatus("disconnected");
        }
      } else {
        setConnectionStatus("disconnected");
      }
    } catch {
      setConnectionStatus("disconnected");
    }
  };

  useEffect(() => {
    checkHealth();
  }, [ollamaEndpoint]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    // Update context (also persists to localStorage and fires POST /api/v1/settings for endpoint)
    setOllamaEndpoint(endpointInput);
    setOllamaModel(modelSelect);
    setContextWindow(contextInput);
    setIgnoredDirs(ignoredInput);
    setChunkSize(chunkInput);
    setIncrementalCache(incrementalInput);

    // Explicitly sync to backend so the in-memory OllamaManager is updated immediately
    try {
      const res = await fetch("http://localhost:8000/api/v1/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ollama_base_url: endpointInput }),
      });
      if (!res.ok) {
        setSaveError(`Backend sync failed (HTTP ${res.status}). Settings saved locally.`);
      } else {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      }
    } catch {
      setSaveError("Backend unreachable. Settings saved locally and will sync on next request.");
    } finally {
      setIsSaving(false);
    }

    // Re-check health after save
    checkHealth();
  };

  return (
    <div className="space-y-6 animate-fade-in text-zinc-800 dark:text-zinc-200">
      <div>
        <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">System Settings</h2>
        <p className="text-xs text-zinc-500">
          Configure Ollama models, FastAPI backend connection endpoint, and indexing parameters.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Connection Health status indicator */}
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900">
          <div className="flex-1 min-w-0">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Ollama Engine Status</h3>
            <p className="text-xs text-zinc-650 dark:text-zinc-400 mt-0.5">
              Current endpoint: {ollamaEndpoint}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {connectionStatus === "checking" && (
              <>
                <Activity className="w-4 h-4 text-amber-500 animate-pulse" />
                <span className="text-xs font-medium text-amber-600 dark:text-amber-400">Verifying...</span>
              </>
            )}
            {connectionStatus === "connected" && (
              <>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">Connected</span>
              </>
            )}
            {connectionStatus === "disconnected" && (
              <>
                <XCircle className="w-4 h-4 text-red-500" />
                <span className="text-xs font-medium text-red-650 dark:text-red-400">Offline / Unreachable</span>
              </>
            )}
          </div>
        </div>

        {/* Local LLM Configuration */}
        <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/10 dark:bg-zinc-950/20 p-6 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-violet-500 dark:text-violet-400" />
            <span>Local LLM Configuration</span>
          </h3>

          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-505 dark:text-zinc-450 block">Ollama Server Endpoint</label>
                <input
                  type="text"
                  value={endpointInput}
                  onChange={(e) => setEndpointInput(e.target.value)}
                  className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg px-3 py-2 text-sm text-zinc-800 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                  placeholder="e.g. http://localhost:11434"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-505 dark:text-zinc-450 block">Default Model Tag</label>
                <select
                  value={modelSelect}
                  onChange={(e) => setModelSelect(e.target.value)}
                  className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg px-3 py-2 text-sm text-zinc-800 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                >
                  <option value="qwen2.5-coder:1.5b">qwen2.5-coder:1.5b ✓ Installed (Fast)</option>
                  <option value="qwen2.5-coder:7b">qwen2.5-coder:7b (Recommended)</option>
                  <option value="qwen2.5-coder">qwen2.5-coder (Latest)</option>
                  <option value="deepseek-coder:33b">deepseek-coder:33b (Heavy)</option>
                  <option value="llama3:latest">llama3:latest (General)</option>
                </select>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-505 dark:text-zinc-450 block">Context Window Size</label>
              <input
                type="number"
                value={contextInput}
                onChange={(e) => setContextInput(Number(e.target.value))}
                className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg px-3 py-2 text-sm text-zinc-800 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
              />
            </div>
          </div>
        </div>

        {/* Indexing Preferences */}
        <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/10 dark:bg-zinc-950/20 p-6 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
            <span>Indexing Preferences</span>
          </h3>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-505 dark:text-zinc-450 block">Ignored Directories (Comma separated)</label>
              <input
                type="text"
                value={ignoredInput}
                onChange={(e) => setIgnoredInput(e.target.value)}
                className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg px-3 py-2 text-sm text-zinc-800 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-505 dark:text-zinc-450 block">Vector Store Chunk Size</label>
              <input
                type="number"
                value={chunkInput}
                onChange={(e) => setChunkInput(Number(e.target.value))}
                className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg px-3 py-2 text-sm text-zinc-800 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
              />
            </div>

            <div className="flex items-center gap-3 pt-2">
              <input
                type="checkbox"
                id="incremental"
                checked={incrementalInput}
                onChange={(e) => setIncrementalInput(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-800 text-violet-600 bg-white dark:bg-zinc-950 focus:ring-violet-500"
              />
              <label htmlFor="incremental" className="text-sm font-medium text-zinc-700 dark:text-zinc-300 select-none">
                Enable Incremental SHA-256 Hash Caching
              </label>
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div className="flex items-center justify-end gap-4">
          {saveSuccess && (
            <span className="text-sm text-emerald-500 animate-fade-in font-medium">
              Settings saved and synced to backend!
            </span>
          )}
          {saveError && (
            <span className="text-sm text-amber-500 animate-fade-in font-medium">
              {saveError}
            </span>
          )}
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-6 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-violet-600/60 text-white rounded-lg text-sm font-semibold transition-all duration-200 shadow-md shadow-violet-600/20 active:scale-[0.98] cursor-pointer disabled:cursor-not-allowed"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>{isSaving ? "Saving..." : "Save Settings"}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default SettingsView;
