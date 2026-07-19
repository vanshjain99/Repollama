import React, { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { Search, Share2, Info, LayoutGrid, CircleDot, HelpCircle, RefreshCw, AlertTriangle, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { useAnalysis } from "../../context/AnalysisContext";

interface GraphNode {
  id: string;
  name?: string;
  type: string;
  language?: string;
  file_path?: string;
  repo_name?: string;
}

interface GraphLink {
  source: string;
  target: string;
  type?: string;
}

// Mock data for demo purposes
const DEMO_NODES: GraphNode[] = [
  { id: "frontend", name: "Tauri / React UI", type: "system" },
  { id: "backend", name: "FastAPI Core", type: "system" },
  { id: "db", name: "ChromaDB Vector Store", type: "database" },
  { id: "git", name: "Git Miner Engine", type: "module" },
  { id: "ast", name: "Tree-sitter AST Parser", type: "module" },
];

const DEMO_LINKS: GraphLink[] = [
  { source: "frontend", target: "backend", type: "HTTP/SSE" },
  { source: "backend", target: "db", type: "Reads/Writes" },
  { source: "backend", target: "git", type: "Orchestrates" },
  { source: "backend", target: "ast", type: "Orchestrates" },
];

export const ArchitectureView: React.FC = () => {
  const { repoPath } = useAnalysis();
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [links, setLinks] = useState<GraphLink[]>([]);
  const [viewType, setViewType] = useState<"c4" | "circular">("c4");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDemo, setIsDemo] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Pan & Zoom state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    setIsDemo(false);
    try {
      const response = await fetch("http://localhost:8000/api/v1/graph");
      if (response.ok) {
        const data = await response.json();
        // Surface backend-reported errors (e.g. graph file not found)
        if (data.error && (!data.nodes || data.nodes.length === 0)) {
          setFetchError(data.error);
          setNodes([]);
          setLinks([]);
        } else if (data.nodes && data.nodes.length > 0) {
          // Format networkx node-link format
          const formattedNodes = data.nodes.map((n: any) => ({
            id: n.id,
            name: n.name || n.id.split("/").pop()?.split("::").pop() || n.id,
            type: n.type || "file",
            language: n.language,
            file_path: n.file_path,
            repo_name: n.repo_name,
          }));

          // networkx json output has link source and target. Normalise to string IDs.
          const formattedLinks = data.links.map((l: any) => ({
            source: typeof l.source === "object" ? l.source.id : l.source,
            target: typeof l.target === "object" ? l.target.id : l.target,
            type: l.type,
          }));

          setNodes(formattedNodes);
          setLinks(formattedLinks);
        } else {
          // Empty graph (no nodes yet)
          setNodes([]);
          setLinks([]);
        }
      } else {
        setFetchError(`Backend returned HTTP ${response.status}. Ensure the FastAPI server is running on port 8000.`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setFetchError(`Cannot reach the backend API: ${msg}. Start the server with: uvicorn repollama.main:app --reload`);
      console.error("Failed to fetch graph:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [repoPath]);

  // --- Pan & Zoom handlers ---
  // Native wheel listener (must be non-passive to call preventDefault)
  // Zoom toward the cursor position so content doesn't jump to origin.
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      // Mouse position relative to the canvas element
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const scaleFactor = e.deltaY < 0 ? 1.12 : 0.9;
      setZoom(prevZoom => {
        const newZoom = Math.min(5.0, Math.max(0.1, prevZoom * scaleFactor));
        // Adjust pan so the point under the cursor stays fixed:
        // newPan = mousePos - (mousePos - oldPan) * (newZoom / oldZoom)
        setPan(prevPan => ({
          x: mouseX - (mouseX - prevPan.x) * (newZoom / prevZoom),
          y: mouseY - (mouseY - prevPan.y) * (newZoom / prevZoom),
        }));
        return newZoom;
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  }, [isDragging, dragStart]);

  const stopDragging = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleZoomIn  = useCallback(() => {
    setZoom(prev => Math.min(5.0, parseFloat((prev * 1.25).toFixed(3))));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom(prev => Math.max(0.1, parseFloat((prev * 0.8).toFixed(3))));
  }, []);

  const handleResetView = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const loadDemo = () => {
    setNodes(DEMO_NODES);
    setLinks(DEMO_LINKS);
    setIsDemo(true);
    setSelectedNodeId("backend");
  };

  // Group nodes by columns for the C4 layered layout
  const layeredPositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    if (nodes.length === 0) return positions;

    // Categorize
    const col1 = nodes.filter(n => n.type === "system" || n.type === "file");
    const col2 = nodes.filter(n => n.type === "class" || n.type === "function");
    const col3 = nodes.filter(n => n.type === "module" || n.type === "database");

    // Limits to fit inside SVG height
    const getSpacing = (count: number) => {
      const maxH = 450;
      if (count <= 1) return maxH / 2;
      return Math.min(100, maxH / (count + 1));
    };

    const sp1 = getSpacing(col1.length);
    col1.forEach((n, i) => {
      positions[n.id] = { x: 120, y: (i + 1) * sp1 };
    });

    const sp2 = getSpacing(col2.length);
    col2.forEach((n, i) => {
      positions[n.id] = { x: 380, y: (i + 1) * sp2 };
    });

    const sp3 = getSpacing(col3.length);
    col3.forEach((n, i) => {
      positions[n.id] = { x: 640, y: (i + 1) * sp3 };
    });

    return positions;
  }, [nodes]);

  // Circular layout positions
  const circularPositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    if (nodes.length === 0) return positions;

    const centerX = 380;
    const centerY = 240;
    const radius = 180;

    nodes.forEach((n, i) => {
      const angle = (i * 2 * Math.PI) / nodes.length;
      positions[n.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    return positions;
  }, [nodes]);

  // Choose positions based on selected view mode
  const nodePositions = viewType === "c4" ? layeredPositions : circularPositions;

  // Filter nodes matching query
  const filteredNodes = useMemo(() => {
    if (!searchQuery.trim()) return nodes;
    const query = searchQuery.toLowerCase();
    return nodes.filter(
      n =>
        n.id.toLowerCase().includes(query) ||
        (n.name && n.name.toLowerCase().includes(query)) ||
        n.type.toLowerCase().includes(query)
    );
  }, [nodes, searchQuery]);

  const filteredNodeIds = useMemo(() => {
    return new Set(filteredNodes.map(n => n.id));
  }, [filteredNodes]);

  // Find selected node details
  const selectedNode = useMemo(() => {
    return nodes.find(n => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Find connections for inspector
  const nodeConnections = useMemo(() => {
    if (!selectedNodeId) return { incoming: [], outgoing: [] };
    const incoming: { node: GraphNode; type?: string }[] = [];
    const outgoing: { node: GraphNode; type?: string }[] = [];

    links.forEach(l => {
      if (l.source === selectedNodeId) {
        const targetNode = nodes.find(n => n.id === l.target);
        if (targetNode) outgoing.push({ node: targetNode, type: l.type });
      }
      if (l.target === selectedNodeId) {
        const sourceNode = nodes.find(n => n.id === l.source);
        if (sourceNode) incoming.push({ node: sourceNode, type: l.type });
      }
    });

    return { incoming, outgoing };
  }, [links, nodes, selectedNodeId]);

  // Drawing curved lines for links
  const getCurvePath = (x1: number, y1: number, x2: number, y2: number) => {
    const dx = Math.abs(x2 - x1) * 0.5;
    const cp1x = x1 + dx;
    const cp1y = y1;
    const cp2x = x2 - dx;
    const cp2y = y2;
    return `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`;
  };



  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] space-y-6 animate-fade-in text-zinc-800 dark:text-zinc-200">
      {/* Header controls */}
      <div className="flex flex-wrap justify-between items-center gap-4 flex-shrink-0">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <span>Architecture Graph Visualizer</span>
            {isDemo && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border border-yellow-500/20 rounded font-mono">
                Demo Mode
              </span>
            )}
          </h2>
          <p className="text-xs text-zinc-500">
            Browse classes, functions, files, and modules extracted from the codebase knowledge graph.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Refresh button */}
          <button
            onClick={fetchGraph}
            disabled={isLoading}
            title="Refresh graph from backend"
            className="p-2 text-zinc-500 hover:text-violet-600 dark:hover:text-violet-400 hover:bg-zinc-100 dark:hover:bg-zinc-900 border border-zinc-200 dark:border-zinc-900 rounded-lg transition-all duration-200 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search nodes..."
              className="w-48 bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-900 rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500/50 text-zinc-800 dark:text-zinc-300"
            />
          </div>

          {/* Toggle buttons */}
          <div className="flex bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-900 rounded-lg p-0.5 text-xs font-semibold">
            <button
              onClick={() => setViewType("c4")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer ${
                viewType === "c4"
                  ? "bg-white text-zinc-900 shadow dark:bg-zinc-800 dark:text-zinc-55"
                  : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Layered</span>
            </button>
            <button
              onClick={() => setViewType("circular")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all duration-200 cursor-pointer ${
                viewType === "circular"
                  ? "bg-white text-zinc-900 shadow dark:bg-zinc-800 dark:text-zinc-55"
                  : "text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-200"
              }`}
            >
              <CircleDot className="w-3.5 h-3.5" />
              <span>Circular</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main visualizer panels */}
      <div className="flex-1 flex flex-col md:flex-row gap-6 min-h-0">
        {/* Canvas area */}
        <div className="flex-1 bg-white dark:bg-zinc-950/20 border border-zinc-200 dark:border-zinc-900 rounded-xl relative overflow-hidden flex items-center justify-center shadow-sm">
          {/* Dotted Grid Background */}
          <div className="absolute inset-0 opacity-40 dark:opacity-10 pointer-events-none bg-[radial-gradient(#3f3f46_1px,transparent_1px)] [background-size:16px_16px]"></div>

          {isLoading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 rounded-full border-2 border-violet-500 border-t-transparent animate-spin"></div>
              <span className="text-xs text-zinc-500">Loading codebase architecture...</span>
            </div>
          ) : fetchError ? (
            <div className="text-center p-8 max-w-sm space-y-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-500 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-200">Graph Fetch Failed</h3>
              <p className="text-xs text-zinc-500 leading-relaxed font-mono bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-3 text-left">
                {fetchError}
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={fetchGraph}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold transition-all duration-200 shadow-md shadow-violet-600/10 active:scale-[0.98] cursor-pointer flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Retry
                </button>
                <button
                  onClick={loadDemo}
                  className="px-4 py-2 bg-zinc-100 dark:bg-zinc-900 hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-[0.98] cursor-pointer"
                >
                  Load Demo
                </button>
              </div>
            </div>
          ) : nodes.length === 0 ? (
            <div className="text-center p-8 max-w-sm space-y-4">
              <div className="mx-auto w-12 h-12 rounded-full bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 flex items-center justify-center shadow-sm">
                <Share2 className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-zinc-850 dark:text-zinc-200">No Graph Data Available</h3>
              <p className="text-xs text-zinc-500 leading-relaxed">
                Analyze your repository on the Dashboard first, or explore a demo graph to see how dependencies are parsed.
              </p>
              <div className="pt-2 flex justify-center gap-3">
                <button
                  onClick={loadDemo}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-semibold transition-all duration-200 shadow-md shadow-violet-600/10 active:scale-[0.98] cursor-pointer"
                >
                  Load Demo Graph
                </button>
              </div>
            </div>
          ) : (
            <div
              ref={canvasRef}
              className="absolute inset-0 flex items-center justify-center"
              style={{ cursor: isDragging ? "grabbing" : "grab", overflow: "hidden" }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={stopDragging}
              onMouseLeave={stopDragging}
            >
              <svg
                ref={svgRef}
                width="100%"
                height="100%"
                viewBox="0 0 760 480"
                className="select-none"
                style={{ display: "block" }}
              >
                <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Edges */}
                <g>
                  {links.map((link, i) => {
                    const fromPos = nodePositions[link.source];
                    const toPos = nodePositions[link.target];
                    if (!fromPos || !toPos) return null;

                    const isDimmed =
                      searchQuery.trim() !== "" &&
                      (!filteredNodeIds.has(link.source) || !filteredNodeIds.has(link.target));

                    const isHighlighted =
                      selectedNodeId !== null &&
                      (link.source === selectedNodeId || link.target === selectedNodeId);

                    return (
                      <path
                        key={i}
                        d={getCurvePath(fromPos.x, fromPos.y, toPos.x, toPos.y)}
                        fill="none"
                        stroke={isHighlighted ? "#8b5cf6" : "#e4e4e7"}
                        className="dark:stroke-zinc-805"
                        style={{
                          strokeWidth: isHighlighted ? 2.5 : 1.2,
                          strokeDasharray: link.type === "CROSS_REPO_LINK" ? "4 4" : undefined,
                          opacity: isDimmed ? 0.15 : isHighlighted ? 1.0 : 0.45,
                        }}
                        transition-all="true"
                      />
                    );
                  })}
                </g>

                {/* Node SVG elements – rendered inside the same <g transform> so zoom/pan applies */}
                {nodes.map((node) => {
                  const pos = nodePositions[node.id];
                  if (!pos) return null;

                  const isSelected = selectedNodeId === node.id;
                  const isDimmedNode = searchQuery.trim() !== "" && !filteredNodeIds.has(node.id);

                  // Colour map (stroke + fill shades)
                  const nodeColorMap: Record<string, { stroke: string; fill: string; text: string; badge: string }> = {
                    system:   { stroke: "#a855f7", fill: "#1e0a2e", text: "#e9d5ff", badge: "#7c3aed" },
                    file:     { stroke: "#8b5cf6", fill: "#170d2a", text: "#ddd6fe", badge: "#6d28d9" },
                    class:    { stroke: "#3b82f6", fill: "#0a1628", text: "#bfdbfe", badge: "#1d4ed8" },
                    function: { stroke: "#ec4899", fill: "#2a0a18", text: "#fbcfe8", badge: "#be185d" },
                    module:   { stroke: "#f97316", fill: "#1c0e00", text: "#fed7aa", badge: "#c2410c" },
                    database: { stroke: "#10b981", fill: "#021c10", text: "#a7f3d0", badge: "#047857" },
                  };
                  const clr = nodeColorMap[node.type] ?? { stroke: "#71717a", fill: "#18181b", text: "#d4d4d8", badge: "#52525b" };

                  const W = 140;
                  const H = 50;
                  const x = pos.x - W / 2;
                  const y = pos.y - H / 2;
                  const label = node.name ?? node.id;
                  // truncate long label for SVG text
                  const maxChars = 18;
                  const displayLabel = label.length > maxChars ? label.slice(0, maxChars - 1) + "…" : label;

                  return (
                    <g
                      key={node.id}
                      style={{ opacity: isDimmedNode ? 0.25 : 1, cursor: "pointer" }}
                      onClick={() => setSelectedNodeId(node.id)}
                    >
                      {/* Glow / selection ring */}
                      {isSelected && (
                        <rect
                          x={x - 3}
                          y={y - 3}
                          width={W + 6}
                          height={H + 6}
                          rx={12}
                          fill="none"
                          stroke="#8b5cf6"
                          strokeWidth={2.5}
                          strokeDasharray="0"
                        />
                      )}
                      {/* Card background */}
                      <rect
                        x={x}
                        y={y}
                        width={W}
                        height={H}
                        rx={9}
                        fill={clr.fill}
                        stroke={clr.stroke}
                        strokeWidth={isSelected ? 1.8 : 1}
                        strokeOpacity={isSelected ? 1 : 0.7}
                      />
                      {/* Type badge strip at top */}
                      <rect x={x + 8} y={y + 7} width={W - 16} height={12} rx={4} fill={clr.badge} fillOpacity={0.35} />
                      <text
                        x={pos.x}
                        y={y + 16}
                        textAnchor="middle"
                        fontSize="8"
                        fontFamily="monospace"
                        letterSpacing="1"
                        fill={clr.text}
                        fillOpacity={0.7}
                        style={{ textTransform: "uppercase", fontWeight: 700, pointerEvents: "none", userSelect: "none" }}
                      >
                        {node.type}
                      </text>
                      {/* Name label */}
                      <text
                        x={pos.x}
                        y={y + 34}
                        textAnchor="middle"
                        fontSize="11"
                        fontFamily="sans-serif"
                        fill={clr.text}
                        fontWeight="600"
                        style={{ pointerEvents: "none", userSelect: "none" }}
                      >
                        {displayLabel}
                      </text>
                    </g>
                  );
                })}
                </g>
              </svg>
            </div>
          )}

          {/* Key Legend on canvas overlay */}
          {nodes.length > 0 && (
            <div className="absolute bottom-4 left-4 bg-white/90 dark:bg-zinc-950/90 backdrop-blur border border-zinc-200 dark:border-zinc-900 rounded-lg p-3 space-y-1.5 shadow-sm">
              <h4 className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">Legend</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {[
                  { label: "File/System", color: "bg-violet-500" },
                  { label: "Class", color: "bg-blue-500" },
                  { label: "Function", color: "bg-pink-500" },
                  { label: "Module", color: "bg-orange-500" },
                  { label: "Database", color: "bg-emerald-500" },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${item.color}`}></span>
                    <span className="text-[10px] text-zinc-650 dark:text-zinc-400">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Zoom controls overlay – top-right of canvas */}
          {nodes.length > 0 && (
            <div className="absolute top-3 right-3 flex items-center gap-1 bg-white/90 dark:bg-zinc-950/90 backdrop-blur border border-zinc-200 dark:border-zinc-800 rounded-lg shadow-sm p-1 z-10">
              <button
                onClick={handleZoomOut}
                title="Zoom out"
                className="p-1.5 rounded text-zinc-500 hover:text-violet-600 dark:hover:text-violet-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all cursor-pointer"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 min-w-[38px] text-center select-none">
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={handleZoomIn}
                title="Zoom in"
                className="p-1.5 rounded text-zinc-500 hover:text-violet-600 dark:hover:text-violet-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all cursor-pointer"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <div className="w-px h-4 bg-zinc-200 dark:bg-zinc-700 mx-0.5" />
              <button
                onClick={handleResetView}
                title="Reset view"
                className="p-1.5 rounded text-zinc-500 hover:text-violet-600 dark:hover:text-violet-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-all cursor-pointer"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Sidebar Inspector details */}
        <div className="w-full md:w-80 bg-white dark:bg-zinc-950/20 border border-zinc-200 dark:border-zinc-900 rounded-xl flex flex-col overflow-hidden shadow-sm flex-shrink-0">
          <div className="p-4 border-b border-zinc-200 dark:border-zinc-900 bg-zinc-50 dark:bg-zinc-950/50">
            <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-2">
              <Info className="w-4 h-4 text-violet-500" />
              <span>Node Inspector</span>
            </h3>
          </div>

          <div className="p-5 flex-1 overflow-y-auto space-y-5 scrollbar-thin">
            {!selectedNode ? (
              <div className="text-center py-12 space-y-2">
                <HelpCircle className="w-10 h-10 text-zinc-400 mx-auto" />
                <p className="text-xs text-zinc-500 max-w-[200px] mx-auto leading-relaxed">
                  Select any node in the architecture graph to inspect its parameters, source location, and linkages.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Node Metadata */}
                <div>
                  <span className="px-2 py-0.5 text-[9px] uppercase font-bold tracking-wider rounded bg-zinc-100 dark:bg-zinc-900 text-zinc-500 dark:text-zinc-450 border border-zinc-200 dark:border-zinc-800">
                    {selectedNode.type}
                  </span>
                  <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 mt-2 break-all">
                    {selectedNode.name}
                  </h3>
                </div>

                {/* Additional Details */}
                <div className="space-y-2 border-t border-zinc-250 dark:border-zinc-900 pt-3 text-xs">
                  {selectedNode.file_path && (
                    <div>
                      <span className="text-zinc-500 block">Relative Path</span>
                      <span className="font-mono break-all text-zinc-800 dark:text-zinc-300">{selectedNode.file_path}</span>
                    </div>
                  )}
                  {selectedNode.language && (
                    <div>
                      <span className="text-zinc-500 block">Language</span>
                      <span className="font-semibold text-zinc-800 dark:text-zinc-300">{selectedNode.language}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-zinc-500 block">Full Node ID</span>
                    <span className="font-mono break-all text-zinc-800 dark:text-zinc-350 bg-zinc-50 dark:bg-zinc-950 p-1.5 rounded border border-zinc-200 dark:border-zinc-900 block mt-0.5">
                      {selectedNode.id}
                    </span>
                  </div>
                </div>

                {/* Dependencies Linkages lists */}
                <div className="space-y-3 border-t border-zinc-250 dark:border-zinc-900 pt-3 text-xs">
                  <div>
                    <span className="font-semibold text-zinc-850 dark:text-zinc-200 block mb-1">
                      Depends On ({nodeConnections.outgoing.length})
                    </span>
                    {nodeConnections.outgoing.length === 0 ? (
                      <span className="text-zinc-500 italic text-[11px]">No outgoing dependencies</span>
                    ) : (
                      <div className="space-y-1.5">
                        {nodeConnections.outgoing.map((conn, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedNodeId(conn.node.id)}
                            className="w-full text-left p-1.5 rounded bg-zinc-50 hover:bg-zinc-100 dark:bg-zinc-900/40 dark:hover:bg-zinc-900 text-[11px] truncate border border-zinc-200 dark:border-zinc-900/60 block text-violet-600 dark:text-violet-400 font-medium active:scale-98 cursor-pointer"
                            title={conn.node.id}
                          >
                            {conn.node.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <span className="font-semibold text-zinc-850 dark:text-zinc-200 block mb-1">
                      Required By ({nodeConnections.incoming.length})
                    </span>
                    {nodeConnections.incoming.length === 0 ? (
                      <span className="text-zinc-500 italic text-[11px]">No incoming dependencies</span>
                    ) : (
                      <div className="space-y-1.5">
                        {nodeConnections.incoming.map((conn, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedNodeId(conn.node.id)}
                            className="w-full text-left p-1.5 rounded bg-zinc-50 hover:bg-zinc-100 dark:bg-zinc-900/40 dark:hover:bg-zinc-900 text-[11px] truncate border border-zinc-200 dark:border-zinc-900/60 block text-violet-600 dark:text-violet-400 font-medium active:scale-98 cursor-pointer"
                            title={conn.node.id}
                          >
                            {conn.node.name}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ArchitectureView;
