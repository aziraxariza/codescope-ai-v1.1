"use client";

// A hand-authored, self-drawing call graph — literally what CodeScope produces
// from a real repo, used as the landing page's signature visual instead of a
// generic hero illustration. Pure SVG/CSS, no dependency on the real Mermaid
// renderer used inside the app.

interface NodeDef {
  id: string;
  x: number;
  y: number;
  label: string;
  focus?: boolean;
  accent?: "teal" | "purple";
}

interface EdgeDef {
  from: string;
  to: string;
  delay: number;
}

const NODES: NodeDef[] = [
  { id: "main", x: 240, y: 46, label: "main.py", focus: true, accent: "teal" },
  { id: "parser", x: 84, y: 158, label: "repo_parser.py", accent: "teal" },
  { id: "llm", x: 396, y: 158, label: "llm.py", accent: "purple" },
  { id: "graph", x: 60, y: 278, label: "neo4j_client.py", accent: "teal" },
  { id: "agents", x: 240, y: 278, label: "graph_rag.py", accent: "purple" },
  { id: "embed", x: 420, y: 278, label: "vector_store.py", accent: "purple" },
  { id: "chat", x: 240, y: 384, label: "/chat", accent: "teal" },
];

const EDGES: EdgeDef[] = [
  { from: "main", to: "parser", delay: 0.15 },
  { from: "main", to: "llm", delay: 0.25 },
  { from: "main", to: "agents", delay: 0.35 },
  { from: "parser", to: "graph", delay: 0.5 },
  { from: "agents", to: "llm", delay: 0.6 },
  { from: "agents", to: "embed", delay: 0.7 },
  { from: "agents", to: "chat", delay: 0.85 },
  { from: "graph", to: "chat", delay: 1.0 },
];

const nodeMap = Object.fromEntries(NODES.map((n) => [n.id, n]));

function edgePath(from: NodeDef, to: NodeDef): string {
  const midY = (from.y + to.y) / 2;
  return `M ${from.x} ${from.y} C ${from.x} ${midY}, ${to.x} ${midY}, ${to.x} ${to.y}`;
}

export default function HeroGraph() {
  return (
    <svg
      viewBox="0 0 480 420"
      className="w-full h-auto max-w-[480px]"
      role="img"
      aria-label="Animated diagram of files connected by function calls, representing a generated call graph"
    >
      <defs>
        <marker id="dot" viewBox="0 0 4 4" markerWidth="4" markerHeight="4" refX="2" refY="2">
          <circle cx="2" cy="2" r="2" fill="#2a2d3a" />
        </marker>
      </defs>

      {EDGES.map((e, i) => {
        const from = nodeMap[e.from];
        const to = nodeMap[e.to];
        return (
          <path
            key={i}
            d={edgePath(from, to)}
            fill="none"
            stroke="#2a2d3a"
            strokeWidth={1.5}
            className="hero-edge"
            style={{ animationDelay: `${e.delay}s` }}
          />
        );
      })}

      {NODES.map((n, i) => {
        const color = n.accent === "purple" ? "#7f77dd" : "#1d9e75";
        const w = Math.max(76, n.label.length * 7.2 + 20);
        return (
          <g
            key={n.id}
            className="hero-node"
            style={{ animationDelay: `${0.9 + i * 0.08}s`, transformOrigin: `${n.x}px ${n.y}px` }}
          >
            <rect
              x={n.x - w / 2}
              y={n.y - 15}
              width={w}
              height={30}
              rx={8}
              fill="#1a1d27"
              stroke={n.focus ? color : "#2a2d3a"}
              strokeWidth={n.focus ? 1.5 : 1}
            />
            {n.focus && (
              <rect
                x={n.x - w / 2}
                y={n.y - 15}
                width={w}
                height={30}
                rx={8}
                fill="none"
                stroke={color}
                strokeOpacity={0.4}
              >
                <animate attributeName="stroke-width" values="1.5;5;1.5" dur="2.4s" begin="1.6s" repeatCount="indefinite" />
                <animate attributeName="stroke-opacity" values="0.4;0;0.4" dur="2.4s" begin="1.6s" repeatCount="indefinite" />
              </rect>
            )}
            <circle cx={n.x - w / 2 + 12} cy={n.y} r={3} fill={color} />
            <text
              x={n.x + 6}
              y={n.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize="11"
              fontFamily="var(--font-mono), monospace"
              fill="#e8e8ed"
            >
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
