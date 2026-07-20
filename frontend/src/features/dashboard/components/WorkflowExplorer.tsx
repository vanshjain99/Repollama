import React, { useEffect, useState } from "react";
import { GitCommit, Play, RefreshCw, Sparkles, Network } from "lucide-react";
import MermaidRenderer from "../../../components/common/MermaidRenderer";

interface Workflow {
  id: string;
  title: string;
  description: string;
  diagram: string;
}

export const WorkflowExplorer: React.FC = () => {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [customAction, setCustomAction] = useState<string>("");
  const [tracing, setTracing] = useState<boolean>(false);

  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/workflows");
        if (res.ok) {
          const data = await res.json();
          setWorkflows(data.workflows || []);
          if (data.workflows && data.workflows.length > 0) {
            setSelectedWorkflowId(data.workflows[0].id);
          }
        }
      } catch (err) {
        console.error("Failed to load workflows:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkflows();
  }, []);

  const selectedWorkflow = workflows.find((w) => w.id === selectedWorkflowId) || workflows[0];

  const handleTraceCustomAction = async () => {
    if (!customAction.trim()) return;
    setTracing(true);
    try {
      const res = await fetch("http://localhost:8000/api/v1/workflows/trace", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: "http://localhost:8000",
          action: customAction.trim(),
        }),
      });
      const data = await res.json();
      if (data.diagram) {
        const newWorkflow: Workflow = {
          id: `custom-${Date.now()}`,
          title: `Custom Action: ${customAction.trim()}`,
          description: `Generated dynamic browser trace diagram for action "${customAction.trim()}"`,
          diagram: data.diagram,
        };
        setWorkflows((prev) => [newWorkflow, ...prev]);
        setSelectedWorkflowId(newWorkflow.id);
        setCustomAction("");
      }
    } catch (err) {
      console.error("Trace action error:", err);
    } finally {
      setTracing(false);
    }
  };

  return (
    <div className="border border-zinc-200 dark:border-zinc-900 rounded-xl bg-zinc-100/30 dark:bg-zinc-950/40 p-6 space-y-6 shadow-sm hover:border-zinc-300 dark:hover:border-zinc-800/80 transition-all duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-900 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-500">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Workflow Sequence Explorer
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Interactive browser agent trace sequence diagrams & HTTP action flows
            </p>
          </div>
        </div>
      </div>

      {/* Main Content Layout: List View & Mermaid Canvas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Workflow List View */}
        <div className="space-y-3 lg:col-span-1">
          <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 block">
            Select Workflow Action
          </label>

          {loading ? (
            <div className="p-8 text-center text-xs text-zinc-500 flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" /> Loading workflows...
            </div>
          ) : (
            <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
              {workflows.map((wf) => (
                <button
                  key={wf.id}
                  onClick={() => setSelectedWorkflowId(wf.id)}
                  className={`w-full text-left p-3.5 rounded-lg border transition-all duration-200 cursor-pointer ${
                    wf.id === selectedWorkflowId
                      ? "bg-violet-600/10 border-violet-500/50 text-violet-900 dark:text-violet-200 shadow-sm"
                      : "bg-white dark:bg-zinc-900/40 border-zinc-200 dark:border-zinc-900 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-800"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">{wf.title}</span>
                    <GitCommit className="w-3.5 h-3.5 opacity-60" />
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 line-clamp-2">
                    {wf.description}
                  </p>
                </button>
              ))}
            </div>
          )}

          {/* Trace New Action Input */}
          <div className="pt-3 border-t border-zinc-200 dark:border-zinc-900 space-y-2">
            <label className="text-xs font-medium text-zinc-500 dark:text-zinc-400 block flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              Trace Custom Action
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={customAction}
                onChange={(e) => setCustomAction(e.target.value)}
                placeholder='e.g., "Submit Order"'
                className="flex-1 px-3 py-1.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <button
                onClick={handleTraceCustomAction}
                disabled={tracing || !customAction.trim()}
                className="px-3 py-1.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-xs font-medium flex items-center gap-1 cursor-pointer disabled:opacity-50"
              >
                {tracing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
                <span>Trace</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Side: Mermaid Sequence Diagram Canvas */}
        <div className="lg:col-span-2 space-y-2">
          {selectedWorkflow ? (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-zinc-800 dark:text-zinc-100">
                    {selectedWorkflow.title}
                  </h4>
                  <p className="text-[11px] text-zinc-500">
                    {selectedWorkflow.description}
                  </p>
                </div>
              </div>

              <MermaidRenderer chart={selectedWorkflow.diagram} className="min-h-[300px]" />
            </>
          ) : (
            <div className="p-12 text-center text-xs text-zinc-500 border border-dashed border-zinc-300 dark:border-zinc-800 rounded-xl">
              No workflow selected
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowExplorer;
