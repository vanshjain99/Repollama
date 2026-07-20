import React, { createContext, useContext, useState, useEffect, useRef } from "react";
import { open } from "@tauri-apps/plugin-dialog";

export type AnalysisStatus = "Idle" | "Analyzing" | "Complete" | "Error";

export interface RecentTask {
  id: string;
  title: string;
  subtitle: string;
  timestamp: number;
  type: "ast" | "git" | "vector";
}

interface AnalysisContextProps {
  repoPath: string;
  setRepoPath: (path: string) => void;
  analysisStatus: AnalysisStatus;
  setAnalysisStatus: (status: AnalysisStatus) => void;
  logs: string[];
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  isAnalyzing: boolean;
  astEntities: string;
  commitsParsed: string;
  vectorStorage: string;
  vectorStorageSub: string;
  recentTasks: RecentTask[];
  handleSelectDirectory: () => Promise<void>;
  handleStartAnalysis: () => Promise<void>;
  handleCancelAnalysis: () => void;
  ollamaModel: string;
  setOllamaModel: (m: string) => void;
  ollamaEndpoint: string;
  setOllamaEndpoint: (e: string) => void;
  contextWindow: number;
  setContextWindow: (c: number) => void;
  ignoredDirs: string;
  setIgnoredDirs: (i: string) => void;
  chunkSize: number;
  setChunkSize: (c: number) => void;
  incrementalCache: boolean;
  setIncrementalCache: (i: boolean) => void;
  userRole: "Developer" | "Architect";
  setUserRole: (role: "Developer" | "Architect") => void;
}

const AnalysisContext = createContext<AnalysisContextProps | undefined>(undefined);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [repoPath, setRepoPath] = useState<string>(() => {
    return localStorage.getItem("repollama_repo_path") || "";
  });
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("Idle");
  const [logs, setLogs] = useState<string[]>(() => {
    try {
      const stored = localStorage.getItem("repollama_logs");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

  const [astEntities, setAstEntities] = useState<string>(() => {
    return localStorage.getItem("repollama_ast_entities") || "0";
  });
  const [commitsParsed, setCommitsParsed] = useState<string>(() => {
    return localStorage.getItem("repollama_commits_parsed") || "0 commits";
  });
  const [vectorStorage, setVectorStorage] = useState<string>(() => {
    return localStorage.getItem("repollama_vector_storage") || "Not Initialized";
  });
  const [vectorStorageSub, setVectorStorageSub] = useState<string>(() => {
    return localStorage.getItem("repollama_vector_storage_sub") || "0 document chunk embeddings";
  });
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>(() => {
    try {
      const stored = localStorage.getItem("repollama_recent_tasks");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [ollamaModel, setOllamaModel] = useState<string>(() => {
    return localStorage.getItem("repollama_ollama_model") || "qwen2.5-coder:1.5b";
  });
  const [ollamaEndpoint, setOllamaEndpoint] = useState<string>(() => {
    return localStorage.getItem("repollama_ollama_endpoint") || "http://localhost:11434";
  });
  const [contextWindow, setContextWindow] = useState<number>(() => {
    return Number(localStorage.getItem("repollama_context_window") || "8192");
  });
  const [ignoredDirs, setIgnoredDirs] = useState<string>(() => {
    return localStorage.getItem("repollama_ignored_dirs") || "node_modules, venv, .git, dist, build, .repollama_data";
  });
  const [chunkSize, setChunkSize] = useState<number>(() => {
    return Number(localStorage.getItem("repollama_chunk_size") || "1000");
  });
  const [incrementalCache, setIncrementalCache] = useState<boolean>(() => {
    return localStorage.getItem("repollama_incremental_cache") !== "false";
  });
  const [userRole, setUserRole] = useState<"Developer" | "Architect">(() => {
    return (localStorage.getItem("repollama_user_role") as "Developer" | "Architect") || "Developer";
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  // Sync state with localStorage
  useEffect(() => {
    localStorage.setItem("repollama_user_role", userRole);
  }, [userRole]);

  // Sync state with localStorage
  useEffect(() => {
    localStorage.setItem("repollama_repo_path", repoPath);
  }, [repoPath]);

  useEffect(() => {
    localStorage.setItem("repollama_logs", JSON.stringify(logs));
  }, [logs]);

  useEffect(() => {
    localStorage.setItem("repollama_ast_entities", astEntities);
  }, [astEntities]);

  useEffect(() => {
    localStorage.setItem("repollama_commits_parsed", commitsParsed);
  }, [commitsParsed]);

  useEffect(() => {
    localStorage.setItem("repollama_vector_storage", vectorStorage);
  }, [vectorStorage]);

  useEffect(() => {
    localStorage.setItem("repollama_vector_storage_sub", vectorStorageSub);
  }, [vectorStorageSub]);

  useEffect(() => {
    localStorage.setItem("repollama_recent_tasks", JSON.stringify(recentTasks));
  }, [recentTasks]);

  useEffect(() => {
    localStorage.setItem("repollama_ollama_model", ollamaModel);
  }, [ollamaModel]);

  useEffect(() => {
    localStorage.setItem("repollama_ollama_endpoint", ollamaEndpoint);
    if (ollamaEndpoint) {
      fetch("http://localhost:8000/api/v1/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ollama_base_url: ollamaEndpoint }),
      }).catch(err => console.error("Failed to sync settings with backend:", err));
    }
  }, [ollamaEndpoint]);

  useEffect(() => {
    localStorage.setItem("repollama_context_window", String(contextWindow));
  }, [contextWindow]);

  useEffect(() => {
    localStorage.setItem("repollama_ignored_dirs", ignoredDirs);
  }, [ignoredDirs]);

  useEffect(() => {
    localStorage.setItem("repollama_chunk_size", String(chunkSize));
  }, [chunkSize]);

  useEffect(() => {
    localStorage.setItem("repollama_incremental_cache", String(incrementalCache));
  }, [incrementalCache]);

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
        setLogs([]); // Clear logs when path changes
        setAnalysisStatus("Idle");
      }
    } catch (err) {
      console.error("Failed to select directory:", err);
      setLogs((prev) => [...prev, `[System] Error: Failed to open directory picker: ${err}`]);
      setAnalysisStatus("Error");
    }
  };

  const handleStartAnalysis = async () => {
    if (!repoPath || isAnalyzing) return;

    setIsAnalyzing(true);
    setAnalysisStatus("Analyzing");
    setLogs([`[System] Initializing analysis pipeline for workspace: ${repoPath}`]);

    // Send POST /api/v1/analyze request to trigger MacroCompiler engine
    try {
      setLogs((prev) => [...prev, `[MacroCompiler] Triggering POST /api/v1/analyze...`]);
      const res = await fetch("http://localhost:8000/api/v1/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: repoPath, repo_paths: [repoPath] }),
      });

      if (res.ok) {
        const data = await res.json();
        setLogs((prev) => [
          ...prev,
          `[MacroCompiler] Initial compile result: ${data.message} (Nodes: ${data.nodes ?? 0}, Edges: ${data.edges ?? 0})`,
        ]);
      } else {
        const errText = await res.text();
        setLogs((prev) => [
          ...prev,
          `[System] Notice: POST /api/v1/analyze responded with status ${res.status}: ${errText}`,
        ]);
      }
    } catch (err) {
      console.warn("POST /api/v1/analyze request error:", err);
      setLogs((prev) => [
        ...prev,
        `[System] Notice: MacroCompiler POST trigger returned: ${err}`,
      ]);
    }

    // Connect to SSE log terminal stream
    setLogs((prev) => [...prev, `[System] Subscribing to live SSE log stream (/api/v1/analyze/stream)...`]);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sseUrl = `http://localhost:8000/api/v1/analyze/stream?path=${encodeURIComponent(repoPath)}`;
    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      const logMsg = event.data;
      setLogs((prev) => [...prev, logMsg]);

      if (logMsg.startsWith("[System] Error:")) {
        setAnalysisStatus("Error");
      }

      // Extract stats upon analysis completion
      if (logMsg.startsWith("[System] Analysis complete.")) {
        const match = logMsg.match(/Nodes:\s*(\d+),\s*Edges:\s*(\d+),\s*Collection Size:\s*(\d+)(?:,\s*Commits:\s*(\d+))?/);
        if (match) {
          const nodes = parseInt(match[1], 10);
          const collectionSize = parseInt(match[3], 10);
          const commits = match[4] ? parseInt(match[4], 10) : 0;

          const finalEntities = nodes.toLocaleString();
          const finalCommits = commits > 0 ? `${commits.toLocaleString()} commits` : "0 commits";
          const finalVS = "Active";
          const finalVSSub = `${collectionSize.toLocaleString()} document chunk embeddings`;

          setAstEntities(finalEntities);
          setCommitsParsed(finalCommits);
          setVectorStorage(finalVS);
          setVectorStorageSub(finalVSSub);

          const now = Date.now();
          const newTasks: RecentTask[] = [
            {
              id: `ast-${now}`,
              title: "Semantics indexed",
              subtitle: repoPath,
              timestamp: now,
              type: "ast",
            },
            {
              id: `git-${now}`,
              title: "Git log extracted",
              subtitle: finalCommits,
              timestamp: now - 1000,
              type: "git",
            },
            {
              id: `vector-${now}`,
              title: "Vectors loaded",
              subtitle: finalVSSub,
              timestamp: now - 2000,
              type: "vector",
            },
          ];

          setRecentTasks((prev) => {
            const combined = [...newTasks, ...prev];
            return combined.slice(0, 9);
          });
        }
      }

      if (logMsg === "[Pipeline] Analysis Complete!") {
        eventSource.close();
        setIsAnalyzing(false);
        setAnalysisStatus("Complete");
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource error:", err);
      setLogs((prev) => [
        ...prev,
        `[System] Error: Connection lost or failed to start log stream.`,
      ]);
      eventSource.close();
      setIsAnalyzing(false);
      setAnalysisStatus("Error");
    };
  };

  const handleCancelAnalysis = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsAnalyzing(false);
    setAnalysisStatus("Idle");
    setLogs((prev) => [...prev, `[System] Warning: Analysis canceled by user.`]);
  };

  return (
    <AnalysisContext.Provider
      value={{
        repoPath,
        setRepoPath,
        analysisStatus,
        setAnalysisStatus,
        logs,
        setLogs,
        isAnalyzing,
        astEntities,
        commitsParsed,
        vectorStorage,
        vectorStorageSub,
        recentTasks,
        handleSelectDirectory,
        handleStartAnalysis,
        handleCancelAnalysis,
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
        userRole,
        setUserRole,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  );
};

export const useAnalysis = () => {
  const context = useContext(AnalysisContext);
  if (context === undefined) {
    throw new Error("useAnalysis must be used within an AnalysisProvider");
  }
  return context;
};
