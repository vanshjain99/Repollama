import React, { createContext, useContext, useState, useEffect, useRef } from "react";
import { open } from "@tauri-apps/plugin-dialog";

export interface RecentTask {
  id: string;
  title: string;
  subtitle: string;
  timestamp: number;
  type: "ast" | "git" | "vector";
}

interface AnalysisContextProps {
  repoPath: string;
  logs: string[];
  isAnalyzing: boolean;
  astEntities: string;
  commitsParsed: string;
  vectorStorage: string;
  vectorStorageSub: string;
  recentTasks: RecentTask[];
  handleSelectDirectory: () => Promise<void>;
  handleStartAnalysis: () => void;
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
}

const AnalysisContext = createContext<AnalysisContextProps | undefined>(undefined);

export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [repoPath, setRepoPath] = useState<string>(() => {
    return localStorage.getItem("repollama_repo_path") || "";
  });
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

  const eventSourceRef = useRef<EventSource | null>(null);

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

  // Clean up EventSource connection on unmount of the Provider (app shutdown)
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

          // Populate recent tasks with the actual stats from this run
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
            return combined.slice(0, 9); // Keep latest 9 tasks (3 runs)
          });
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
        `[System] Error: Connection lost or failed to start stream.`,
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
    <AnalysisContext.Provider
      value={{
        repoPath,
        logs,
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
