"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  chart: string;
}

export default function MermaidDiagram({ chart }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "done" | "error">("loading");

  useEffect(() => {
    if (!ref.current || !chart) return;

    let cancelled = false;
    setStatus("loading");

    async function render() {
      const mermaid = (await import("mermaid")).default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        themeVariables: {
          primaryColor: "#1d9e75",
          primaryTextColor: "#e8e8ed",
          primaryBorderColor: "#2a2d3a",
          lineColor: "#8b8fa8",
          secondaryColor: "#1a1d27",
          tertiaryColor: "#0f1117",
          fontSize: "13px",
        },
        flowchart: {
          // More breathing room between nodes/ranks so dense call graphs
          // don't collapse into a tangle of crossing edges.
          curve: "basis",
          nodeSpacing: 45,
          rankSpacing: 90,
          padding: 20,
          htmlLabels: true,
        },
      });

      try {
        const id = `mermaid-${Date.now()}`;
        const { svg } = await mermaid.render(id, chart);
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
          setStatus("done");
        }
      } catch (err) {
        if (!cancelled && ref.current) {
          ref.current.innerHTML = `<p class="text-red-400 text-sm p-4">Diagram render error. Check the Mermaid syntax.</p>`;
          setStatus("error");
        }
      }
    }

    render();
    return () => { cancelled = true; };
  }, [chart]);

  return (
    <div
      className="mermaid-wrap w-full overflow-auto rounded-lg bg-[#1a1d27] p-4 min-h-[200px] max-h-[70vh]"
    >
      {status === "loading" && (
        <p className="text-[#8b8fa8] text-sm">Rendering diagram…</p>
      )}
      <div ref={ref} />
    </div>
  );
}