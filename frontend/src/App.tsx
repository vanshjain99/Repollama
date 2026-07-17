import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./components/layout/MainLayout";
import Dashboard from "./features/dashboard/Dashboard";

// Simple placeholders for other views to ensure seamless navigation
const ArchitecturePlaceholder: React.FC = () => (
  <div className="space-y-6 animate-fade-in">
    <div className="border border-zinc-900 rounded-xl bg-zinc-950/20 p-8 text-center space-y-4">
      <div className="mx-auto w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800 text-zinc-400">
        <span>🏗️</span>
      </div>
      <h2 className="text-xl font-bold text-zinc-200">Architecture Graph Visualizer</h2>
      <p className="text-sm text-zinc-400 max-w-md mx-auto">
        This view will load the NetworkX knowledge graph and allow visual browsing of modules, classes, and imported dependencies.
      </p>
    </div>
  </div>
);

const ChatPlaceholder: React.FC = () => (
  <div className="space-y-6 animate-fade-in">
    <div className="border border-zinc-900 rounded-xl bg-zinc-950/20 p-8 text-center space-y-4">
      <div className="mx-auto w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800 text-zinc-400">
        <span>💬</span>
      </div>
      <h2 className="text-xl font-bold text-zinc-200">AI Code Companion</h2>
      <p className="text-sm text-zinc-400 max-w-md mx-auto">
        Chat with your codebase using Ollama LLM embeddings and direct retrieval-augmented generation (RAG) vector store queries.
      </p>
    </div>
  </div>
);

const SettingsPlaceholder: React.FC = () => (
  <div className="space-y-6 animate-fade-in">
    <div className="border border-zinc-900 rounded-xl bg-zinc-950/20 p-8 text-center space-y-4">
      <div className="mx-auto w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center border border-zinc-800 text-zinc-400">
        <span>⚙️</span>
      </div>
      <h2 className="text-xl font-bold text-zinc-200">System Settings</h2>
      <p className="text-sm text-zinc-400 max-w-md mx-auto">
        Configure Ollama models, FastAPI backend connection port, tree-sitter language parses, and indexing parameters.
      </p>
    </div>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="architecture" element={<ArchitecturePlaceholder />} />
          <Route path="chat" element={<ChatPlaceholder />} />
          <Route path="settings" element={<SettingsPlaceholder />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
