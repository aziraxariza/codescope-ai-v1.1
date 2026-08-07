"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import HeroGraph from "../components/HeroGraph";

const GITHUB_URL = "https://github.com/aziraxariza/codescope-ai";

const LANGUAGES = [
  "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C/C++", "Ruby", "PHP",
];

const PIPELINE = [
  {
    n: "01",
    title: "Clone",
    body: "CodeScope pulls any public GitHub repo with a shallow clone — no upload, no setup on your end.",
  },
  {
    n: "02",
    title: "Parse",
    body: "Every file is walked with tree-sitter. Nine language grammars turn source into functions, classes, and call sites.",
  },
  {
    n: "03",
    title: "Graph",
    body: "Functions and classes become nodes in Neo4j. Calls between them become edges — a queryable map of the codebase.",
  },
  {
    n: "04",
    title: "Ask",
    body: "Chat runs GraphRAG: Qdrant finds semantically relevant functions, Neo4j expands to their callers and callees, then the LLM answers from that grounded context.",
  },
];

const FEATURES = [
  {
    title: "Architecture diagrams",
    body: "A Mermaid diagram generated straight from the call graph, grouped by directory so it reads like the project's actual folder structure — not a tangle of arrows.",
    accent: "teal",
  },
  {
    title: "Codebase chat",
    body: "Ask what a function does or how a request flows through the system. Answers cite real function names and file paths, not guesses.",
    accent: "purple",
  },
  {
    title: "Security scan",
    body: "Flags SQL injection, hardcoded secrets, command injection, and path traversal, then asks the LLM to explain the risk and the fix in plain English.",
    accent: "teal",
  },
  {
    title: "Multi-language parsing",
    body: "One AST pipeline across Python, JS/TS, Java, Go, Rust, C/C++, Ruby, and PHP — so it holds up on real, mixed-language repos.",
    accent: "purple",
  },
];

const STACK = [
  "FastAPI", "Next.js 14", "Neo4j", "Qdrant", "tree-sitter", "Groq / Ollama",
];

export default function Landing() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");

  function goAnalyze() {
    const url = repoUrl.trim();
    router.push(url ? `/app?repo=${encodeURIComponent(url)}` : "/app");
  }

  return (
    <div className="min-h-screen bg-[#0f1117] text-[#e8e8ed]">
      {/* Header */}
      <header className="border-b border-[#2a2d3a] px-6 py-4 flex items-center gap-3 max-w-6xl mx-auto">
        <div className="w-8 h-8 rounded-lg bg-[#1d9e75] flex items-center justify-center text-white font-bold text-sm font-mono">
          CS
        </div>
        <span className="text-lg font-semibold">CodeScope AI</span>
        <nav className="ml-auto flex items-center gap-6 text-sm">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="text-[#8b8fa8] hover:text-[#e8e8ed] transition-colors"
          >
            GitHub
          </a>
          <Link
            href="/app"
            className="px-4 py-2 rounded-lg bg-[#1a1d27] border border-[#2a2d3a] hover:border-[#1d9e75] text-sm transition-colors"
          >
            Open app →
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-20 grid md:grid-cols-2 gap-12 items-center">
        <div>
          <p className="font-mono text-xs tracking-[0.2em] text-[#1d9e75] mb-4 fade-up">
            GRAPHRAG CODE INTELLIGENCE
          </p>
          <h1 className="text-4xl sm:text-5xl font-semibold font-mono leading-[1.1] mb-5 fade-up" style={{ animationDelay: "0.1s" }}>
            Point it at a repo.
            <br />
            Get back its architecture.
          </h1>
          <p className="text-[#8b8fa8] text-base leading-relaxed mb-8 max-w-md fade-up" style={{ animationDelay: "0.2s" }}>
            CodeScope clones a public GitHub repository, parses it with tree-sitter, and
            builds a knowledge graph of every function, class, and call. Then you can ask
            it questions — and the answers are grounded in that graph, not a guess.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 mb-4 fade-up" style={{ animationDelay: "0.3s" }}>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && goAnalyze()}
              placeholder="https://github.com/tiangolo/fastapi"
              className="flex-1 bg-[#1a1d27] border border-[#2a2d3a] rounded-xl px-4 py-3 text-sm font-mono
                         text-[#e8e8ed] placeholder-[#4a4d5a] focus:outline-none focus:border-[#1d9e75]"
            />
            <button
              onClick={goAnalyze}
              className="px-6 py-3 bg-[#1d9e75] hover:bg-[#17855f] text-white rounded-xl text-sm font-medium
                         transition-colors whitespace-nowrap"
            >
              Analyze a repo
            </button>
          </div>

          <p className="text-[#4a4d5a] text-xs fade-up" style={{ animationDelay: "0.4s" }}>
            {LANGUAGES.join(" · ")}
          </p>
        </div>

        <div className="flex justify-center md:justify-end">
          <HeroGraph />
        </div>
      </section>

      {/* Pipeline */}
      <section className="border-t border-[#2a2d3a]">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-xl font-semibold mb-1">How it works</h2>
          <p className="text-[#8b8fa8] text-sm mb-10">
            Four deterministic steps, in order — the LLM only enters at the last one.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {PIPELINE.map((step) => (
              <div key={step.n} className="border-l-2 border-[#2a2d3a] pl-4">
                <span className="font-mono text-xs text-[#1d9e75]">{step.n}</span>
                <h3 className="font-semibold mt-1 mb-2">{step.title}</h3>
                <p className="text-[#8b8fa8] text-sm leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-[#2a2d3a]">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-xl font-semibold mb-1">What you get</h2>
          <p className="text-[#8b8fa8] text-sm mb-10">
            Four views into the same underlying graph.
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-6 hover:border-[#3a3d4a] transition-colors"
              >
                <div
                  className="w-2 h-2 rounded-full mb-4"
                  style={{ background: f.accent === "purple" ? "#7f77dd" : "#1d9e75" }}
                />
                <h3 className="font-semibold mb-2">{f.title}</h3>
                <p className="text-[#8b8fa8] text-sm leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="border-t border-[#2a2d3a]">
        <div className="max-w-6xl mx-auto px-6 py-12 flex flex-wrap items-center gap-x-3 gap-y-2">
          <span className="text-[#4a4d5a] text-xs font-mono tracking-widest mr-2">BUILT WITH</span>
          {STACK.map((s, i) => (
            <span key={s} className="text-[#8b8fa8] text-sm font-mono">
              {s}
              {i < STACK.length - 1 && <span className="text-[#2a2d3a] ml-3">/</span>}
            </span>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-[#2a2d3a]">
        <div className="max-w-6xl mx-auto px-6 py-16 text-center">
          <h2 className="text-2xl font-semibold font-mono mb-3">Try it on your own repo</h2>
          <p className="text-[#8b8fa8] text-sm mb-8">Public GitHub repos only. Takes 30–90 seconds.</p>
          <Link
            href="/app"
            className="inline-block px-6 py-3 bg-[#1d9e75] hover:bg-[#17855f] text-white rounded-xl text-sm font-medium transition-colors"
          >
            Open CodeScope →
          </Link>
        </div>
      </section>

      <footer className="border-t border-[#2a2d3a] px-6 py-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-2 text-xs text-[#4a4d5a]">
          <span>CodeScope AI — GraphRAG-powered code intelligence</span>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="hover:text-[#8b8fa8] transition-colors">
            {GITHUB_URL.replace("https://", "")}
          </a>
        </div>
      </footer>
    </div>
  );
}
