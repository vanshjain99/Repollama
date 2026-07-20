import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { AlertTriangle, Copy, Check } from "lucide-react";

interface MermaidRendererProps {
  chart: string;
  className?: string;
}

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  securityLevel: "loose",
  themeVariables: {
    fontFamily: "ui-sans-serif, system-ui, sans-serif",
    fontSize: "13px",
    primaryColor: "#4f46e5",
    primaryTextColor: "#f4f4f5",
    primaryBorderColor: "#6366f1",
    lineColor: "#818cf8",
    secondaryColor: "#18181b",
    tertiaryColor: "#09090b",
  },
});

export const MermaidRenderer: React.FC<MermaidRendererProps> = ({ chart, className = "" }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      if (!chart.trim()) return;
      setError(null);

      try {
        const id = `mermaid-svg-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, chart);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err: any) {
        if (isMounted) {
          console.error("Mermaid rendering error:", err);
          setError(err?.message || "Failed to render sequence diagram.");
        }
      }
    };

    renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`relative rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-900 text-zinc-100 p-4 font-sans ${className}`}>
      <div className="flex items-center justify-end mb-2">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors cursor-pointer"
          title="Copy Mermaid source"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy Code</span>
            </>
          )}
        </button>
      </div>

      {error ? (
        <div className="p-4 rounded-lg bg-red-950/40 border border-red-800/40 text-red-300 flex items-start gap-3 text-xs font-mono">
          <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold mb-1">Diagram Render Error</p>
            <p className="opacity-90">{error}</p>
            <pre className="mt-3 p-2 bg-zinc-950/80 rounded border border-zinc-800 overflow-x-auto text-[11px] text-zinc-400">
              {chart}
            </pre>
          </div>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="mermaid-svg-container flex justify-center items-center overflow-x-auto p-2"
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      )}
    </div>
  );
};

export default MermaidRenderer;
