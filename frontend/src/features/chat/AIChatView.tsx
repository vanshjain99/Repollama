import React, { useState, useEffect, useRef, useCallback } from "react";
import { Send, User, Bot, Trash2, Cpu, AlertCircle, RefreshCw } from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";

interface Message {
  role: "user" | "ai";
  content: string;
  timestamp: number;
}

export const AIChatView: React.FC = () => {
  const { ollamaModel, ollamaEndpoint, repoPath } = useAnalysis();
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const stored = localStorage.getItem("repollama_chat_history");
      return stored ? JSON.parse(stored) : [
        {
          role: "ai",
          content: "Hello! I am the Repollama Code Companion. I have indexed this repository and have access to the NetworkX graph, AST metadata, and Git history. What would you like to know about the architecture?",
          timestamp: Date.now()
        }
      ];
    } catch {
      return [
        {
          role: "ai",
          content: "Hello! I am the Repollama Code Companion. I have indexed this repository and have access to the NetworkX graph, AST metadata, and Git history. What would you like to know about the architecture?",
          timestamp: Date.now()
        }
      ];
    }
  });

  useEffect(() => {
    localStorage.setItem("repollama_chat_history", JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  // Health check — reusable so we can call it after each send and on endpoint change
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/health");
      if (res.ok) {
        const data = await res.json();
        setIsOffline(!data.ollama || !data.ollama.connected);
      } else {
        setIsOffline(true);
      }
    } catch {
      setIsOffline(true);
    }
  }, []);

  // Re-run health check on mount and whenever the configured endpoint changes
  useEffect(() => {
    checkHealth();
  }, [checkHealth, ollamaEndpoint]);

  const handleSend = async () => {
    if (!input.trim() || isGenerating) return;

    const userMsg: Message = {
      role: "user",
      content: input,
      timestamp: Date.now()
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsGenerating(true);

    try {
      const activeEndpoint = ollamaEndpoint || "http://localhost:11434";
      const response = await fetch("http://localhost:8000/api/v1/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Pass the active Ollama endpoint so the backend can route without restart
          "X-Ollama-Endpoint": activeEndpoint,
        },
        body: JSON.stringify({
          message: userMsg.content,
          model: ollamaModel,
          ollama_endpoint: activeEndpoint,
          repo_path: repoPath,  // Scope RAG to the active repository
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.error) {
          throw new Error(data.response);
        }
        setMessages((prev) => [
          ...prev,
          {
            role: "ai",
            content: data.response,
            timestamp: Date.now()
          }
        ]);
        setIsOffline(false);
        checkHealth();
      } else {
        throw new Error(`Server responded with ${response.status}`);
      }
    } catch (err) {
      console.error("Chat request failed:", err);
      const errMsg = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: `Could not reach Ollama at ${ollamaEndpoint || "http://localhost:11434"} (model: ${ollamaModel}).\n\nError: ${errMsg}\n\nPlease verify Ollama is running and the endpoint is correct in Settings.`,
          timestamp: Date.now()
        }
      ]);
      setIsOffline(true);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleClear = () => {
    if (window.confirm("Are you sure you want to clear chat history?")) {
      const resetMsg: Message = {
        role: "ai",
        content: "Hello! I am the Repollama Code Companion. I have indexed this repository and have access to the NetworkX graph, AST metadata, and Git history. What would you like to know about the architecture?",
        timestamp: Date.now()
      };
      setMessages([resetMsg]);
    }
  };

  const formatCode = (text: string) => {
    // Simple code block / inline code formatter
    const parts = text.split(/(```[\s\S]*?```|`[^`\n]+`)/g);
    return parts.map((part, index) => {
      if (part.startsWith("```")) {
        const lines = part.split("\n");
        const lang = lines[0].replace("```", "").trim();
        const code = lines.slice(1, -1).join("\n");
        return (
          <div key={index} className="my-3 border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-hidden bg-zinc-50 dark:bg-black/50 font-mono text-xs">
            {lang && (
              <div className="bg-zinc-200/50 dark:bg-zinc-900 px-4 py-1.5 border-b border-zinc-200 dark:border-zinc-800 text-[10px] text-zinc-550 dark:text-zinc-500 font-sans font-semibold uppercase tracking-wider">
                {lang}
              </div>
            )}
            <pre className="p-4 overflow-x-auto text-zinc-800 dark:text-zinc-300">
              <code>{code}</code>
            </pre>
          </div>
        );
      } else if (part.startsWith("`")) {
        const code = part.slice(1, -1);
        return (
          <code key={index} className="px-1.5 py-0.5 mx-0.5 rounded bg-zinc-150 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700/50 font-mono text-xs text-violet-600 dark:text-violet-400">
            {code}
          </code>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="h-[calc(100vh-12rem)] flex flex-col space-y-6 animate-fade-in text-zinc-850 dark:text-zinc-200">
      {/* View Header */}
      <div className="flex justify-between items-center flex-shrink-0">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <span>AI Code Companion</span>
            <span className="flex items-center gap-1 px-2 py-0.5 bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20 rounded text-[10px] uppercase tracking-wider font-semibold font-mono">
              <Cpu className="w-3 h-3" /> {ollamaModel}
            </span>
          </h2>
          <p className="text-xs text-zinc-500">
            Chat with your codebase using Ollama LLM embeddings and direct RAG queries.
          </p>
        </div>
        <button
          onClick={handleClear}
          title="Clear Chat History"
          className="p-2 text-zinc-500 hover:text-red-500 hover:bg-zinc-100 dark:hover:bg-zinc-900 border border-zinc-200 dark:border-zinc-900 rounded-lg transition-all duration-200 active:scale-95 flex items-center justify-center cursor-pointer"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Offline Alert */}
      {isOffline && (
        <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/20 text-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="flex-1">
            Ollama offline at{" "}
            <code className="font-mono bg-yellow-500/10 px-1 py-0.5 rounded">
              {ollamaEndpoint || "http://localhost:11434"}
            </code>
            . Verify Ollama is running, then check Settings.
          </span>
          <button
            onClick={checkHealth}
            title="Re-check connection"
            className="p-1 hover:bg-yellow-500/20 rounded transition-colors cursor-pointer flex-shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Chat Messages Container */}
      <div className="flex-1 bg-white dark:bg-zinc-950/20 border border-zinc-200 dark:border-zinc-900 rounded-xl flex flex-col overflow-hidden shadow-sm">
        <div className="flex-1 p-6 overflow-y-auto space-y-6 scrollbar-thin">
          {messages.map((msg, i) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={i}
                className={`flex gap-4 ${isUser ? "flex-row-reverse" : "flex-row"} animate-fade-in`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm border ${
                    isUser
                      ? "bg-zinc-150 border-zinc-305 dark:bg-zinc-900 dark:border-zinc-800 text-zinc-700 dark:text-zinc-305"
                      : "bg-violet-600 border-violet-700 text-white"
                  }`}
                >
                  {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    isUser
                      ? "bg-zinc-100/80 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-250 rounded-tr-none"
                      : "bg-white dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-900 text-zinc-850 dark:text-zinc-300 rounded-tl-none shadow-sm"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{formatCode(msg.content)}</div>
                </div>
              </div>
            );
          })}

          {/* Assistant Loading/Generating State */}
          {isGenerating && (
            <div className="flex gap-4 flex-row animate-pulse">
              <div className="w-8 h-8 rounded-lg bg-violet-600 border border-violet-700 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                <Bot className="w-4 h-4" />
              </div>
              <div className="max-w-[75%] rounded-2xl rounded-tl-none px-4 py-3.5 bg-white dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-900 flex items-center justify-center shadow-sm">
                <div className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-violet-500 animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="w-2.5 h-2.5 rounded-full bg-violet-500 animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="w-2.5 h-2.5 rounded-full bg-violet-500 animate-bounce"></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-zinc-200 dark:border-zinc-900 bg-zinc-50 dark:bg-zinc-950/50 flex-shrink-0">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              disabled={isGenerating}
              placeholder="Ask about codebase architecture, functions, or dependencies..."
              className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-xl pl-4 pr-12 py-3.5 text-sm text-zinc-800 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-violet-500/50 placeholder-zinc-450 dark:placeholder-zinc-650 disabled:bg-zinc-100/50 dark:disabled:bg-zinc-950/20"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isGenerating}
              className="absolute right-2 p-2.5 text-violet-600 dark:text-violet-400 hover:text-violet-500 dark:hover:text-violet-300 hover:bg-violet-500/10 rounded-lg transition-colors duration-200 cursor-pointer disabled:opacity-50 disabled:hover:bg-transparent"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIChatView;
