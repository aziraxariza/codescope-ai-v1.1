"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";

// Mermaid must load client-side only
const MermaidDiagram = dynamic(() => import("../../components/MermaidDiagram"), {
  ssr: false,
  loading: () => <div className="text-[#8b8fa8] text-sm p-4">Loading diagram renderer…</div>,
});

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Stats {
  files_parsed: number;
  functions: number;
  classes: number;
  graph_nodes: number;
  graph_edges: number;
  vectors_stored: number;
  languages?: Record<string, number>;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: { name: string; file: string }[];
  graph_expanded?: number;
}

interface Finding {
  type: string;
  severity: string;
  file: string;
  line: number;
  code: string;
  explanation: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "bg-red-900 text-red-300 border border-red-700",
  HIGH: "bg-orange-900 text-orange-300 border border-orange-700",
  MEDIUM: "bg-yellow-900 text-yellow-300 border border-yellow-700",
  LOW: "bg-blue-900 text-blue-300 border border-blue-700",
};

const TYPE_LABEL: Record<string, string> = {
  sql_injection: "SQL Injection",
  hardcoded_secret: "Hardcoded Secret",
  command_injection: "Command Injection",
  path_traversal: "Path Traversal",
};

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4">
      <p className="text-[#8b8fa8] text-xs uppercase tracking-widest mb-1">{label}</p>
      <p className="text-2xl font-semibold text-white">{value.toLocaleString()}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function Home() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#0f1117]" />}>
      <AnalyzerApp />
    </Suspense>
  );
}

function AnalyzerApp() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<"repo" | "arch" | "chat">("repo");

  // Repo tab
  const [repoUrl, setRepoUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [analyzeError, setAnalyzeError] = useState("");

  // Arch tab
  const [diagram, setDiagram] = useState("");
  const [loadingDiagram, setLoadingDiagram] = useState(false);

  // Chat tab
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  // Security tab (inside chat tab)
  const [findings, setFindings] = useState<Finding[]>([]);
  const [securityLoading, setSecurityLoading] = useState(false);
  const [securityLoaded, setSecurityLoaded] = useState(false);

  // Prefill + auto-run when arriving from the landing page with ?repo=
  useEffect(() => {
    const fromLanding = searchParams.get("repo");
    if (fromLanding) {
      setRepoUrl(fromLanding);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (repoUrl && searchParams.get("repo") === repoUrl) {
      handleAnalyze();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoUrl]);

  // ------------------------------------------------------------------
  // Analyze repo
  // ------------------------------------------------------------------
  async function handleAnalyze() {
    if (!repoUrl.trim()) return;
    setAnalyzing(true);
    setAnalyzeError("");
    setStats(null);

    try {
      const res = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: repoUrl.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }

      const data = await res.json();
      setStats(data.stats);

      // Pre-load diagram and security in background
      loadDiagram();
      loadSecurity();
    } catch (e: any) {
      setAnalyzeError(e.message);
    } finally {
      setAnalyzing(false);
    }
  }

  // ------------------------------------------------------------------
  // Load diagram
  // ------------------------------------------------------------------
  async function loadDiagram() {
    setLoadingDiagram(true);
    try {
      const res = await fetch(`${API}/diagram/architecture`);
      const data = await res.json();
      setDiagram(data.mermaid);
    } catch {
      setDiagram("graph TD\n  A[Failed to load diagram]");
    } finally {
      setLoadingDiagram(false);
    }
  }

  // ------------------------------------------------------------------
  // Load security findings
  // ------------------------------------------------------------------
  async function loadSecurity() {
    setSecurityLoading(true);
    try {
      const res = await fetch(`${API}/security`);
      const data = await res.json();
      setFindings(data.findings || []);
      setSecurityLoaded(true);
    } catch {
      setFindings([]);
    } finally {
      setSecurityLoading(false);
    }
  }

  // ------------------------------------------------------------------
  // Chat
  // ------------------------------------------------------------------
  async function handleChat() {
    const q = input.trim();
    if (!q || chatLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setInput("");
    setChatLoading(true);

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources,
          graph_expanded: data.graph_expanded,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: Could not reach the backend." },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  const tabs = [
    { id: "repo", label: "Repository" },
    { id: "arch", label: "Architecture" },
    { id: "chat", label: "Chat" },
  ] as const;

  return (
    <div className="min-h-screen bg-[#0f1117] text-[#e8e8ed]">
      {/* Header */}
      <header className="border-b border-[#2a2d3a] px-6 py-4 flex items-center gap-3">
        <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-[#1d9e75] flex items-center justify-center text-white font-bold text-sm">
            CS
          </div>
          <h1 className="text-lg font-semibold">CodeScope AI</h1>
        </Link>
        <span className="text-[#8b8fa8] text-sm hidden sm:inline">GraphRAG-powered code intelligence</span>
        <Link
          href="/"
          className="ml-auto text-[#8b8fa8] hover:text-[#e8e8ed] text-sm transition-colors"
        >
          ← Home
        </Link>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-1 mb-8 bg-[#1a1d27] rounded-xl p-1 w-fit">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t.id
                  ? "bg-[#1d9e75] text-white"
                  : "text-[#8b8fa8] hover:text-[#e8e8ed]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── REPO TAB ── */}
        {tab === "repo" && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold mb-1">Analyze a repository</h2>
              <p className="text-[#8b8fa8] text-sm">
                Paste a public GitHub URL. CodeScope will clone it, parse the AST,
                build a knowledge graph in Neo4j, and embed every function in Qdrant.
              </p>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
                placeholder="https://github.com/tiangolo/fastapi"
                className="flex-1 bg-[#1a1d27] border border-[#2a2d3a] rounded-xl px-4 py-3 text-sm
                           text-[#e8e8ed] placeholder-[#4a4d5a] focus:outline-none focus:border-[#1d9e75]"
              />
              <button
                onClick={handleAnalyze}
                disabled={analyzing || !repoUrl.trim()}
                className="px-6 py-3 bg-[#1d9e75] hover:bg-[#17855f] disabled:opacity-50
                           disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors"
              >
                {analyzing ? "Analyzing…" : "Analyze"}
              </button>
            </div>

            {analyzeError && (
              <div className="bg-red-900/30 border border-red-700 rounded-xl px-4 py-3 text-red-300 text-sm">
                {analyzeError}
              </div>
            )}

            {analyzing && (
              <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl px-4 py-6 text-center space-y-2">
                <div className="w-6 h-6 border-2 border-[#1d9e75] border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-[#8b8fa8] text-sm">
                  Cloning repo · parsing AST · building graph · embedding functions…
                </p>
                <p className="text-[#4a4d5a] text-xs">This takes 30–90 seconds</p>
              </div>
            )}

            {stats && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-[#8b8fa8] uppercase tracking-widest">
                  Analysis complete
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <StatCard label="Files parsed" value={stats.files_parsed} />
                  <StatCard label="Functions" value={stats.functions} />
                  <StatCard label="Classes" value={stats.classes} />
                  <StatCard label="Graph nodes" value={stats.graph_nodes} />
                  <StatCard label="Graph edges" value={stats.graph_edges} />
                  <StatCard label="Vectors stored" value={stats.vectors_stored} />
                </div>
                {stats.languages && Object.keys(stats.languages).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(stats.languages).map(([lang, count]) => (
                      <span
                        key={lang}
                        className="text-xs px-2.5 py-1 rounded-full bg-[#1a1d27] border border-[#2a2d3a] text-[#8b8fa8]"
                      >
                        {lang} · {count}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-[#8b8fa8] text-sm">
                  Switch to the <strong className="text-[#1d9e75]">Architecture</strong> or{" "}
                  <strong className="text-[#1d9e75]">Chat</strong> tab to explore.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ── ARCHITECTURE TAB ── */}
        {tab === "arch" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold mb-1">Architecture diagram</h2>
                <p className="text-[#8b8fa8] text-sm">
                  Auto-generated from Neo4j cross-file CALLS relationships.
                </p>
              </div>
              <button
                onClick={loadDiagram}
                disabled={loadingDiagram}
                className="px-4 py-2 border border-[#2a2d3a] rounded-lg text-sm text-[#8b8fa8]
                           hover:text-[#e8e8ed] hover:border-[#1d9e75] transition-colors disabled:opacity-50"
              >
                {loadingDiagram ? "Loading…" : "Refresh"}
              </button>
            </div>

            {!diagram && !loadingDiagram && (
              <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-8 text-center text-[#8b8fa8] text-sm">
                Analyze a repository first to generate the architecture diagram.
              </div>
            )}

            {loadingDiagram && (
              <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-8 text-center">
                <div className="w-6 h-6 border-2 border-[#1d9e75] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-[#8b8fa8] text-sm">Generating diagram from Neo4j…</p>
              </div>
            )}

            {diagram && !loadingDiagram && (
              <>
                <MermaidDiagram chart={diagram} />
                <details className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl overflow-hidden">
                  <summary className="px-4 py-3 text-sm text-[#8b8fa8] cursor-pointer hover:text-[#e8e8ed]">
                    View Mermaid source
                  </summary>
                  <pre className="px-4 pb-4 text-xs text-[#7f77dd] overflow-x-auto">{diagram}</pre>
                </details>
              </>
            )}
          </div>
        )}

        {/* ── CHAT TAB ── */}
        {tab === "chat" && (
          <div className="space-y-6">
            {/* Chat section */}
            <div>
              <h2 className="text-xl font-semibold mb-1">Chat with the codebase</h2>
              <p className="text-[#8b8fa8] text-sm">
                Powered by GraphRAG — vector search + Neo4j graph traversal.
              </p>
            </div>

            {/* Message list */}
            <div className="space-y-4 min-h-[120px]">
              {messages.length === 0 && (
                <div className="text-[#4a4d5a] text-sm">
                  Try: <em>"How does authentication work?"</em> or{" "}
                  <em>"What does the main router do?"</em>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-[#1d9e75] text-white"
                        : "bg-[#1a1d27] border border-[#2a2d3a] text-[#e8e8ed]"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>

                    {msg.role === "assistant" && msg.graph_expanded !== undefined && (
                      <p className="mt-2 text-[#4a4d5a] text-xs">
                        GraphRAG: {msg.sources?.length || 0} via vector search
                        {msg.graph_expanded > 0 && ` + ${msg.graph_expanded} via graph expansion`}
                      </p>
                    )}

                    {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-[#8b8fa8] cursor-pointer">
                          Sources ({msg.sources.length})
                        </summary>
                        <ul className="mt-1 space-y-1">
                          {msg.sources.map((s, j) => (
                            <li key={j} className="text-xs text-[#7f77dd]">
                              {s.name} — {s.file.split("/").slice(-2).join("/")}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="flex justify-start">
                  <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((n) => (
                        <div
                          key={n}
                          className="w-2 h-2 rounded-full bg-[#8b8fa8] animate-bounce"
                          style={{ animationDelay: `${n * 0.15}s` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Input */}
            <div className="flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleChat()}
                placeholder="Ask anything about the codebase…"
                className="flex-1 bg-[#1a1d27] border border-[#2a2d3a] rounded-xl px-4 py-3 text-sm
                           text-[#e8e8ed] placeholder-[#4a4d5a] focus:outline-none focus:border-[#1d9e75]"
              />
              <button
                onClick={handleChat}
                disabled={chatLoading || !input.trim()}
                className="px-5 py-3 bg-[#1d9e75] hover:bg-[#17855f] disabled:opacity-50
                           text-white rounded-xl text-sm font-medium transition-colors"
              >
                Send
              </button>
            </div>

            {/* Security findings */}
            <div className="border-t border-[#2a2d3a] pt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold">Security scan</h3>
                  <p className="text-[#8b8fa8] text-sm">
                    SQL injection · hardcoded secrets · command injection · path traversal
                  </p>
                </div>
                {!securityLoaded && (
                  <button
                    onClick={loadSecurity}
                    disabled={securityLoading}
                    className="px-4 py-2 border border-[#2a2d3a] rounded-lg text-sm text-[#8b8fa8]
                               hover:text-[#e8e8ed] hover:border-[#1d9e75] transition-colors disabled:opacity-50"
                  >
                    {securityLoading ? "Scanning…" : "Run scan"}
                  </button>
                )}
              </div>

              {securityLoading && (
                <div className="text-[#8b8fa8] text-sm flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-[#1d9e75] border-t-transparent rounded-full animate-spin" />
                  Scanning for vulnerabilities…
                </div>
              )}

              {securityLoaded && findings.length === 0 && (
                <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl px-4 py-4 text-sm text-[#8b8fa8]">
                  No vulnerabilities detected in this repository.
                </div>
              )}

              {findings.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm text-[#8b8fa8]">{findings.length} finding(s)</p>
                  {findings.map((f, i) => (
                    <div key={i} className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-4 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SEVERITY_COLOR[f.severity] || ""}`}>
                          {f.severity}
                        </span>
                        <span className="text-sm font-medium">
                          {TYPE_LABEL[f.type] || f.type}
                        </span>
                        <span className="text-[#8b8fa8] text-xs ml-auto">
                          line {f.line} · {f.file.split("/").slice(-2).join("/")}
                        </span>
                      </div>
                      <pre className="text-xs text-[#7f77dd] bg-[#0f1117] rounded-lg p-3 overflow-x-auto">
                        {f.code}
                      </pre>
                      {f.explanation && (
                        <p className="text-sm text-[#8b8fa8] leading-relaxed">{f.explanation}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
