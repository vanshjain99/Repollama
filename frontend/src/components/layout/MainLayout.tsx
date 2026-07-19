import React, { useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  GitBranch,
  MessageSquare,
  Settings,
  Terminal,
  Activity,
  Sun,
  Moon
} from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";

interface SidebarItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const SidebarItem: React.FC<SidebarItemProps> = ({ to, icon, label }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
          isActive
            ? "bg-zinc-200 text-zinc-900 shadow-sm border border-zinc-300 dark:bg-zinc-800 dark:text-zinc-50 dark:border-zinc-700/50"
            : "text-zinc-500 hover:text-zinc-900 hover:bg-zinc-200/50 dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-900/50"
        }`
      }
    >
      <span className="w-5 h-5 flex items-center justify-center">{icon}</span>
      <span>{label}</span>
    </NavLink>
  );
};

export const MainLayout: React.FC = () => {
  const { repoPath } = useAnalysis();
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    return (localStorage.getItem("theme") as "light" | "dark") || "light";
  });

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-zinc-50 text-zinc-800 dark:bg-zinc-950 dark:text-zinc-100 font-sans">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 flex flex-col border-r border-zinc-200 dark:border-zinc-900 bg-zinc-100/80 dark:bg-zinc-950/80 backdrop-blur-md">
        {/* Header */}
        <div className="h-16 flex items-center px-6 border-b border-zinc-200 dark:border-zinc-900 gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
            <Terminal className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-zinc-800 dark:text-zinc-50 m-0">
              Repollama
            </h1>
            <p className="text-[10px] text-zinc-500 font-mono tracking-wider uppercase">
              Repo Intelligence
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          <SidebarItem
            to="/"
            icon={<LayoutDashboard className="w-4.5 h-4.5" />}
            label="Dashboard"
          />
          <SidebarItem
            to="/architecture"
            icon={<GitBranch className="w-4.5 h-4.5" />}
            label="Architecture"
          />
          <SidebarItem
            to="/chat"
            icon={<MessageSquare className="w-4.5 h-4.5" />}
            label="AI Chat"
          />
          <SidebarItem
            to="/settings"
            icon={<Settings className="w-4.5 h-4.5" />}
            label="Settings"
          />
        </nav>

        {/* Footer/System Status */}
        <div className="p-4 border-t border-zinc-200 dark:border-zinc-900 bg-zinc-100 dark:bg-zinc-950">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-zinc-200/50 border border-zinc-300/50 dark:bg-zinc-900/40 dark:border-zinc-800/50">
            <div className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300 truncate">
                Local Engine
              </p>
              <p className="text-[10px] text-zinc-500 font-mono truncate">
                Connected: localhost:8000
              </p>
            </div>
            <Activity className="w-4 h-4 text-zinc-400 dark:text-zinc-600" />
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden bg-zinc-100/50 dark:bg-zinc-900/30">
        <header className="h-16 flex items-center justify-between px-8 border-b border-zinc-200 dark:border-zinc-900 bg-zinc-200/20 dark:bg-zinc-950/20 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-zinc-500">Workspace:</span>
            <span className="text-xs font-mono text-zinc-700 dark:text-zinc-300 bg-zinc-200 dark:bg-zinc-900 px-2 py-0.5 rounded border border-zinc-300 dark:border-zinc-800">
              {repoPath || "No repository selected"}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
              <span>Ollama: qwen2.5-coder</span>
            </div>
            
            <button
              onClick={toggleTheme}
              className="p-1.5 rounded-lg bg-zinc-200 hover:bg-zinc-300/80 border border-zinc-300 text-zinc-700 dark:bg-zinc-900 dark:hover:bg-zinc-800/80 dark:border-zinc-800 dark:text-zinc-300 transition-all duration-200 cursor-pointer active:scale-95 flex items-center justify-center"
              title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
            >
              {theme === "light" ? (
                <Moon className="w-4 h-4" />
              ) : (
                <Sun className="w-4 h-4" />
              )}
            </button>
          </div>
        </header>

        {/* Scrollable Container */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="max-w-6xl mx-auto space-y-8">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
};

export default MainLayout;
