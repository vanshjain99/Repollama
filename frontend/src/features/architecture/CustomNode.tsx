import React, { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import {
  FileText,
  Box,
  Code2,
  Layers,
  Database,
  Cpu,
  HelpCircle,
} from "lucide-react";
import type { CustomNodeData } from "../../utils/graphTransformer";

const NODE_CONFIG: Record<
  string,
  {
    icon: React.ElementType;
    borderColor: string;
    bgColor: string;
    badgeBg: string;
    textColor: string;
    glowColor: string;
  }
> = {
  file: {
    icon: FileText,
    borderColor: "border-violet-500",
    bgColor: "bg-violet-950/80 dark:bg-violet-950/90",
    badgeBg: "bg-violet-500/20 text-violet-300 border-violet-500/30",
    textColor: "text-violet-200",
    glowColor: "shadow-violet-500/30",
  },
  class: {
    icon: Box,
    borderColor: "border-blue-500",
    bgColor: "bg-blue-950/80 dark:bg-blue-950/90",
    badgeBg: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    textColor: "text-blue-200",
    glowColor: "shadow-blue-500/30",
  },
  function: {
    icon: Code2,
    borderColor: "border-pink-500",
    bgColor: "bg-pink-950/80 dark:bg-pink-950/90",
    badgeBg: "bg-pink-500/20 text-pink-300 border-pink-500/30",
    textColor: "text-pink-200",
    glowColor: "shadow-pink-500/30",
  },
  module: {
    icon: Layers,
    borderColor: "border-amber-500",
    bgColor: "bg-amber-950/80 dark:bg-amber-950/90",
    badgeBg: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    textColor: "text-amber-200",
    glowColor: "shadow-amber-500/30",
  },
  database: {
    icon: Database,
    borderColor: "border-emerald-500",
    bgColor: "bg-emerald-950/80 dark:bg-emerald-950/90",
    badgeBg: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    textColor: "text-emerald-200",
    glowColor: "shadow-emerald-500/30",
  },
  system: {
    icon: Cpu,
    borderColor: "border-cyan-500",
    bgColor: "bg-cyan-950/80 dark:bg-cyan-950/90",
    badgeBg: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
    textColor: "text-cyan-200",
    glowColor: "shadow-cyan-500/30",
  },
};

const DEFAULT_CONFIG = {
  icon: HelpCircle,
  borderColor: "border-zinc-500",
  bgColor: "bg-zinc-900",
  badgeBg: "bg-zinc-800 text-zinc-300 border-zinc-700",
  textColor: "text-zinc-200",
  glowColor: "shadow-zinc-500/20",
};

export const CustomNode: React.FC<NodeProps<CustomNodeData>> = memo(
  ({ data, selected }) => {
    const typeKey = (data.nodeType || "file").toLowerCase();
    const config = NODE_CONFIG[typeKey] || DEFAULT_CONFIG;
    const IconComponent = config.icon;

    const fnCount = data.astMetadata?.functions?.length || 0;
    const classCount = data.astMetadata?.classes?.length || 0;

    return (
      <div
        className={`min-w-[180px] max-w-[240px] rounded-xl border-2 ${
          config.borderColor
        } ${config.bgColor} backdrop-blur-md p-3 shadow-lg transition-all duration-200 ${
          selected
            ? `ring-4 ring-violet-500/50 shadow-xl ${config.glowColor} scale-[1.03]`
            : "hover:scale-[1.01]"
        }`}
      >
        {/* Handles for edges */}
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-violet-400 !border-2 !border-zinc-950 hover:!scale-125 transition-transform"
        />
        <Handle
          type="source"
          position={Position.Right}
          className="!w-3 !h-3 !bg-violet-400 !border-2 !border-zinc-950 hover:!scale-125 transition-transform"
        />

        {/* Node Header */}
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-1.5 min-w-0">
            <IconComponent className={`w-4 h-4 flex-shrink-0 ${config.textColor}`} />
            <span
              className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border font-mono truncate ${config.badgeBg}`}
            >
              {data.nodeType}
            </span>
          </div>

          {data.language && (
            <span className="text-[9px] font-mono text-zinc-400 bg-zinc-800/80 px-1.5 py-0.5 rounded border border-zinc-700/50">
              {data.language}
            </span>
          )}
        </div>

        {/* Node Name */}
        <div
          className={`font-semibold text-xs tracking-tight break-words line-clamp-2 ${config.textColor}`}
          title={data.name}
        >
          {data.name}
        </div>

        {/* Node Footer Badges (e.g. AST function/class counters) */}
        {(fnCount > 0 || classCount > 0) && (
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-zinc-800/60 text-[10px] font-mono text-zinc-400">
            {classCount > 0 && (
              <span className="flex items-center gap-1 bg-blue-950/60 text-blue-300 px-1.5 py-0.5 rounded border border-blue-800/40">
                <Box className="w-3 h-3" /> {classCount}
              </span>
            )}
            {fnCount > 0 && (
              <span className="flex items-center gap-1 bg-pink-950/60 text-pink-300 px-1.5 py-0.5 rounded border border-pink-800/40">
                <Code2 className="w-3 h-3" /> {fnCount}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
);

CustomNode.displayName = "CustomNode";
export default CustomNode;
