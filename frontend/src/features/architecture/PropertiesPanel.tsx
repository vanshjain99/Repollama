import React, { useState } from "react";
import type { Node } from "reactflow";
import {
  X,
  Code2,
  Box,
  FileText,
  Layers,
  ChevronDown,
  ChevronRight,
  ArrowUpRight,
  ArrowDownLeft,
  Info,
} from "lucide-react";
import type { CustomNodeData } from "../../utils/graphTransformer";

interface PropertiesPanelProps {
  selectedNode: Node<CustomNodeData> | null;
  onSelectNodeById: (id: string) => void;
  onClose: () => void;
}

export const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  selectedNode,
  onSelectNodeById,
  onClose,
}) => {
  const [showRawJson, setShowRawJson] = useState(false);

  if (!selectedNode) {
    return (
      <div className="w-full md:w-80 bg-white dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-900 rounded-xl p-6 flex flex-col items-center justify-center text-center shadow-sm">
        <Info className="w-10 h-10 text-zinc-400 dark:text-zinc-600 mb-3" />
        <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200 mb-1">
          Properties Panel
        </h3>
        <p className="text-xs text-zinc-500 max-w-[200px]">
          Click any node on the graph canvas to inspect its AST metadata,
          imports, and defined code elements.
        </p>
      </div>
    );
  }

  const { data } = selectedNode;
  const meta = data.astMetadata;

  return (
    <div className="w-full md:w-80 bg-white dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-900 rounded-xl flex flex-col overflow-hidden shadow-sm flex-shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-zinc-200 dark:border-zinc-900 bg-zinc-50/80 dark:bg-zinc-900/50 flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/20 font-mono">
            {data.nodeType}
          </span>
          {data.repo_name && (
            <span className="text-[10px] font-mono text-zinc-500 truncate">
              @{data.repo_name}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
          title="Close Properties Panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Main Content */}
      <div className="p-4 flex-1 overflow-y-auto space-y-5 text-xs">
        {/* Node Title & Description */}
        <div>
          <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100 break-all">
            {data.name}
          </h2>
          {meta.relativePath && (
            <div className="mt-1 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 break-all flex items-start gap-1">
              <FileText className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>{meta.relativePath}</span>
            </div>
          )}
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 gap-2 bg-zinc-50 dark:bg-zinc-900/40 p-2.5 rounded-lg border border-zinc-200 dark:border-zinc-900">
          <div>
            <span className="text-[10px] text-zinc-400 uppercase font-mono block">
              Language
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200">
              {data.language || "Unknown"}
            </span>
          </div>
          <div>
            <span className="text-[10px] text-zinc-400 uppercase font-mono block">
              Dependencies
            </span>
            <span className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-2">
              <span className="flex items-center text-emerald-500">
                <ArrowDownLeft className="w-3 h-3 mr-0.5" /> {meta.incomingCount}
              </span>
              <span className="flex items-center text-sky-500">
                <ArrowUpRight className="w-3 h-3 mr-0.5" /> {meta.outgoingCount}
              </span>
            </span>
          </div>
        </div>

        {/* Parent File Link if present */}
        {meta.parentFile && (
          <div className="space-y-1">
            <span className="font-semibold text-zinc-700 dark:text-zinc-300 block">
              Parent File Node
            </span>
            <button
              onClick={() => onSelectNodeById(meta.parentFile!)}
              className="w-full text-left p-2 rounded-lg bg-violet-50 dark:bg-violet-950/30 text-violet-600 dark:text-violet-400 hover:bg-violet-100 dark:hover:bg-violet-900/40 border border-violet-200 dark:border-violet-800/50 flex items-center justify-between transition-colors font-mono text-[11px] truncate cursor-pointer"
            >
              <span className="truncate">{meta.parentFile}</span>
              <ArrowUpRight className="w-3.5 h-3.5 flex-shrink-0 ml-1" />
            </button>
          </div>
        )}

        {/* Functions Section */}
        {meta.functions.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between font-semibold text-zinc-800 dark:text-zinc-200">
              <span className="flex items-center gap-1.5 text-pink-500">
                <Code2 className="w-4 h-4" /> Functions
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-pink-500/10 text-pink-500 rounded border border-pink-500/20">
                {meta.functions.length}
              </span>
            </div>
            <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
              {meta.functions.map((fnName, idx) => (
                <div
                  key={idx}
                  className="p-1.5 rounded bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-900 font-mono text-[11px] text-zinc-700 dark:text-zinc-300 truncate"
                >
                  {fnName}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Classes Section */}
        {meta.classes.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between font-semibold text-zinc-800 dark:text-zinc-200">
              <span className="flex items-center gap-1.5 text-blue-500">
                <Box className="w-4 h-4" /> Classes
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-blue-500/10 text-blue-500 rounded border border-blue-500/20">
                {meta.classes.length}
              </span>
            </div>
            <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
              {meta.classes.map((clsName, idx) => (
                <div
                  key={idx}
                  className="p-1.5 rounded bg-zinc-50 dark:bg-zinc-900/60 border border-zinc-200 dark:border-zinc-900 font-mono text-[11px] text-zinc-700 dark:text-zinc-300 truncate"
                >
                  {clsName}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Imports & Modules Section */}
        {meta.imports.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between font-semibold text-zinc-800 dark:text-zinc-200">
              <span className="flex items-center gap-1.5 text-sky-500">
                <Layers className="w-4 h-4" /> Imports / Dependencies
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 bg-sky-500/10 text-sky-500 rounded border border-sky-500/20">
                {meta.imports.length}
              </span>
            </div>
            <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
              {meta.imports.map((imp, idx) => (
                <button
                  key={idx}
                  onClick={() => onSelectNodeById(imp)}
                  className="w-full text-left p-1.5 rounded bg-zinc-50 dark:bg-zinc-900/60 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-900 font-mono text-[11px] text-sky-600 dark:text-sky-400 truncate block transition-colors cursor-pointer"
                  title={imp}
                >
                  {imp}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Raw Metadata Accordion */}
        <div className="border-t border-zinc-200 dark:border-zinc-900 pt-3">
          <button
            onClick={() => setShowRawJson(!showRawJson)}
            className="flex items-center justify-between w-full text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 font-medium text-xs cursor-pointer py-1"
          >
            <span>Raw Node ID & JSON</span>
            {showRawJson ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>

          {showRawJson && (
            <pre className="mt-2 p-2.5 rounded bg-zinc-900 text-zinc-300 font-mono text-[10px] overflow-x-auto border border-zinc-800 leading-relaxed max-h-48 scrollbar-thin">
              {JSON.stringify(
                {
                  id: data.rawId,
                  name: data.name,
                  nodeType: data.nodeType,
                  language: data.language,
                  file_path: data.file_path,
                  astMetadata: meta,
                },
                null,
                2
              )}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default PropertiesPanel;
