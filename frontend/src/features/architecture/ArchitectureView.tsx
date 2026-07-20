import { useEffect, useState, useMemo, useCallback } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Search,
  Share2,
  RefreshCw,
  AlertTriangle,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Filter,
} from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";
import {
  transformNetworkXToReactFlow,
  type CustomNodeData,
  type NetworkXGraphData,
} from "../../utils/graphTransformer";
import CustomNode from "./CustomNode";
import PropertiesPanel from "./PropertiesPanel";

const nodeTypes = {
  customNode: CustomNode,
};

// Mock NetworkX Graph for Demo fallback
const DEMO_GRAPH_DATA: NetworkXGraphData = {
  nodes: [
    {
      id: "frontend/src/App.tsx",
      name: "App.tsx",
      type: "file",
      language: "TypeScript",
      relative_path: "frontend/src/App.tsx",
      repo_name: "Repollama",
    },
    {
      id: "backend/repollama/main.py",
      name: "main.py",
      type: "file",
      language: "Python",
      relative_path: "backend/repollama/main.py",
      repo_name: "Repollama",
    },
    {
      id: "backend/repollama/engines/macro_compiler.py",
      name: "macro_compiler.py",
      type: "file",
      language: "Python",
      relative_path: "backend/repollama/engines/macro_compiler.py",
      repo_name: "Repollama",
    },
    {
      id: "backend/repollama/engines/macro_compiler.py::MacroCompiler",
      name: "MacroCompiler",
      type: "class",
      file_path: "backend/repollama/engines/macro_compiler.py",
      repo_name: "Repollama",
    },
    {
      id: "backend/repollama/engines/macro_compiler.py::compile",
      name: "compile",
      type: "function",
      file_path: "backend/repollama/engines/macro_compiler.py",
      repo_name: "Repollama",
    },
    {
      id: "fastapi",
      name: "fastapi",
      type: "module",
      repo_name: "Repollama",
    },
    {
      id: "chromadb",
      name: "chromadb",
      type: "database",
      repo_name: "Repollama",
    },
  ],
  links: [
    {
      source: "frontend/src/App.tsx",
      target: "backend/repollama/main.py",
      type: "IMPORTS",
    },
    {
      source: "backend/repollama/main.py",
      target: "backend/repollama/engines/macro_compiler.py",
      type: "IMPORTS",
    },
    {
      source: "backend/repollama/main.py",
      target: "fastapi",
      type: "IMPORTS",
    },
    {
      source: "backend/repollama/main.py",
      target: "chromadb",
      type: "IMPORTS",
    },
    {
      source: "backend/repollama/engines/macro_compiler.py",
      target: "backend/repollama/engines/macro_compiler.py::MacroCompiler",
      type: "CONTAINS",
    },
    {
      source: "backend/repollama/engines/macro_compiler.py",
      target: "backend/repollama/engines/macro_compiler.py::compile",
      type: "CONTAINS",
    },
  ],
};

function GraphFlowCanvas() {
  const { repoPath } = useAnalysis();
  const [nodes, setNodes, onNodesChange] = useNodesState<CustomNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [isLoading, setIsLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const { fitView, zoomIn, zoomOut } = useReactFlow();

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    setIsDemo(false);
    try {
      const response = await fetch("http://localhost:8000/api/v1/graph");
      if (response.ok) {
        const data: NetworkXGraphData & { error?: string } = await response.json();
        if (data.error && (!data.nodes || data.nodes.length === 0)) {
          setFetchError(data.error);
          setNodes([]);
          setEdges([]);
        } else if (data.nodes && data.nodes.length > 0) {
          const { nodes: rfNodes, edges: rfEdges } =
            transformNetworkXToReactFlow(data);
          setNodes(rfNodes);
          setEdges(rfEdges);
          setTimeout(() => fitView({ padding: 0.2 }), 100);
        } else {
          setNodes([]);
          setEdges([]);
        }
      } else {
        setFetchError(
          `Backend returned HTTP ${response.status}. Ensure FastAPI server is running.`
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setFetchError(
        `Cannot connect to backend: ${msg}. Start server: uvicorn repollama.main:app --reload`
      );
    } finally {
      setIsLoading(false);
    }
  }, [setNodes, setEdges, fitView]);

  useEffect(() => {
    fetchGraph();
  }, [repoPath, fetchGraph]);

  const loadDemo = () => {
    const { nodes: rfNodes, edges: rfEdges } =
      transformNetworkXToReactFlow(DEMO_GRAPH_DATA);
    setNodes(rfNodes);
    setEdges(rfEdges);
    setIsDemo(true);
    setFetchError(null);
    setIsLoading(false);
    setSelectedNodeId("backend/repollama/engines/macro_compiler.py");
    setTimeout(() => fitView({ padding: 0.2 }), 100);
  };

  // Filter nodes & highlight matching ones
  const filteredNodes = useMemo(() => {
    return nodes.map((node) => {
      const query = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !query ||
        node.id.toLowerCase().includes(query) ||
        node.data.name.toLowerCase().includes(query) ||
        node.data.nodeType.toLowerCase().includes(query);

      const matchesType =
        typeFilter === "all" ||
        node.data.nodeType.toLowerCase() === typeFilter.toLowerCase();

      const isSelected = node.id === selectedNodeId;

      return {
        ...node,
        selected: isSelected,
        hidden: !(matchesSearch && matchesType),
      };
    });
  }, [nodes, searchQuery, typeFilter, selectedNodeId]);

  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  const handleSelectNodeById = useCallback(
    (id: string) => {
      setSelectedNodeId(id);
      const targetNode = nodes.find((n) => n.id === id);
      if (targetNode) {
        fitView({
          nodes: [{ id: targetNode.id }],
          duration: 600,
          padding: 1.5,
        });
      }
    },
    [nodes, fitView]
  );

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] space-y-4 animate-fade-in text-zinc-800 dark:text-zinc-200">
      {/* Header controls toolbar */}
      <div className="flex flex-wrap justify-between items-center gap-4 flex-shrink-0 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-xl p-3.5 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <span>Interactive Knowledge Graph</span>
            {isDemo && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 rounded font-mono">
                Demo Graph
              </span>
            )}
          </h2>
          <p className="text-xs text-zinc-500">
            NetworkX macro graph visualization powered by React Flow. Inspect files, classes, functions, and imports.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Refresh button */}
          <button
            onClick={fetchGraph}
            disabled={isLoading}
            title="Refresh graph from backend"
            className="p-2 text-zinc-500 hover:text-violet-600 dark:hover:text-violet-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 border border-zinc-200 dark:border-zinc-900 rounded-lg transition-all disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>

          {/* Type Filter dropdown */}
          <div className="flex items-center gap-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-900 rounded-lg px-2.5 py-1.5 text-xs font-mono">
            <Filter className="w-3.5 h-3.5 text-zinc-400" />
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-transparent text-zinc-700 dark:text-zinc-300 focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-zinc-900 text-zinc-200">All Types</option>
              <option value="file" className="bg-zinc-900 text-violet-300">File</option>
              <option value="class" className="bg-zinc-900 text-blue-300">Class</option>
              <option value="function" className="bg-zinc-900 text-pink-300">Function</option>
              <option value="module" className="bg-zinc-900 text-amber-300">Module</option>
              <option value="database" className="bg-zinc-900 text-emerald-300">Database</option>
            </select>
          </div>

          {/* Search box */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search AST nodes..."
              className="w-48 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 text-zinc-800 dark:text-zinc-300"
            />
          </div>
        </div>
      </div>

      {/* Graph Visualizer & Properties Panel Container */}
      <div className="flex-1 flex flex-col md:flex-row gap-4 min-h-0">
        {/* Canvas area */}
        <div className="flex-1 bg-white dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-900 rounded-xl relative overflow-hidden flex items-center justify-center shadow-sm">
          {isLoading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin"></div>
              <span className="text-xs text-zinc-500">Loading NetworkX knowledge graph...</span>
            </div>
          ) : fetchError ? (
            <div className="text-center p-8 max-w-md space-y-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-500 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-200">
                Knowledge Graph Not Available
              </h3>
              <p className="text-xs text-zinc-500 leading-relaxed font-mono bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-3 text-left">
                {fetchError}
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={fetchGraph}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold transition-all shadow-md shadow-violet-600/10 cursor-pointer flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Retry
                </button>
                <button
                  onClick={loadDemo}
                  className="px-4 py-2 bg-zinc-100 dark:bg-zinc-900 hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  Load Demo Graph
                </button>
              </div>
            </div>
          ) : nodes.length === 0 ? (
            <div className="text-center p-8 max-w-sm space-y-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 flex items-center justify-center shadow-sm">
                <Share2 className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                Empty Knowledge Graph
              </h3>
              <p className="text-xs text-zinc-500 leading-relaxed">
                Run repository analysis on the Dashboard to build and visualize the AST graph.
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={loadDemo}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  Load Demo Graph
                </button>
              </div>
            </div>
          ) : (
            <ReactFlow
              nodes={filteredNodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              nodeTypes={nodeTypes}
              onNodeClick={(_evt, node) => setSelectedNodeId(node.id)}
              onPaneClick={() => setSelectedNodeId(null)}
              fitView
              minZoom={0.1}
              maxZoom={2.5}
              defaultEdgeOptions={{ type: "smoothstep" }}
              className="bg-transparent select-none"
            >
              <Background color="#3f3f46" gap={18} size={1} />
              <Controls className="!bg-zinc-900/90 !border-zinc-800 !text-zinc-300 !rounded-lg" />
              <MiniMap
                nodeColor={(node) => {
                  const type = (node.data?.nodeType || "").toLowerCase();
                  if (type === "file") return "#8b5cf6";
                  if (type === "class") return "#3b82f6";
                  if (type === "function") return "#ec4899";
                  if (type === "module") return "#f97316";
                  if (type === "database") return "#10b981";
                  return "#6b7280";
                }}
                maskColor="rgba(24, 24, 27, 0.7)"
                className="!bg-zinc-950 !border-zinc-800 !rounded-lg"
              />

              {/* Overlay Canvas Custom Controls */}
              <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/90 dark:bg-zinc-950/90 backdrop-blur border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-sm p-1 z-10">
                <button
                  onClick={() => zoomOut()}
                  title="Zoom Out"
                  className="p-1.5 rounded text-zinc-500 hover:text-violet-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => zoomIn()}
                  title="Zoom In"
                  className="p-1.5 rounded text-zinc-500 hover:text-violet-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <div className="w-px h-4 bg-zinc-200 dark:bg-zinc-800 mx-0.5" />
                <button
                  onClick={() => fitView({ padding: 0.2, duration: 400 })}
                  title="Fit View"
                  className="p-1.5 rounded text-zinc-500 hover:text-violet-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </ReactFlow>
          )}
        </div>

        {/* Sidebar AST Properties Panel */}
        <PropertiesPanel
          selectedNode={selectedNode}
          onSelectNodeById={handleSelectNodeById}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>
    </div>
  );
}

export function ArchitectureView() {
  return (
    <ReactFlowProvider>
      <GraphFlowCanvas />
    </ReactFlowProvider>
  );
}

export default ArchitectureView;
