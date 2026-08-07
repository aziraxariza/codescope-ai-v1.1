"""
CodeScope AI — FastAPI entry point.

Routes:
  GET  /health                 → health check + LLM provider info
  POST /analyze                → clone repo, parse, build graph, embed
  POST /chat                   → GraphRAG codebase Q&A
  GET  /security               → scan for vulnerabilities + LLM explanations
  GET  /diagram/architecture   → file-level Mermaid diagram
  GET  /diagram/classes        → class-level Mermaid diagram
  GET  /stats                  → current graph statistics
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from .parser.repo_parser import clone_repo, parse_repo, detect_languages
from .graph.neo4j_client import GraphDB
from .embeddings.vector_store import store_functions, clear_collection
from .agents.graph_rag import graphrag_chat
from .agents.security_agent import scan_repo, explain_findings
from .agents.diagram_agent import generate_file_diagram, generate_class_diagram

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CodeScope AI",
    description="GraphRAG-powered autonomous code intelligence platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = GraphDB()
REPO_PATH = os.getenv("REPO_PATH", "/tmp/repo")


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    question: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Quick health check. Also confirms which LLM provider is active."""
    return {
        "status": "ok",
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
        "repo_path": REPO_PATH,
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """
    Full pipeline:
    1. Clone the GitHub repo
    2. Parse all .py files with tree-sitter
    3. Load function/class graph into Neo4j
    4. Embed all functions into Qdrant
    Returns stats for the dashboard.
    """
    if not req.url.startswith("https://github.com"):
        raise HTTPException(status_code=400, detail="Please provide a valid GitHub URL")

    try:
        # Step 1 — clone
        path = clone_repo(req.url, REPO_PATH)

        # Step 2 — parse (multi-language: py, js/ts/tsx, java, go, rust, c/cpp, ruby, php)
        languages = detect_languages(path)
        nodes = parse_repo(path)
        if not nodes:
            if languages:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Found source files but couldn't extract any functions or "
                        "classes from them (possibly all empty, generated, or "
                        "minified files)."
                    ),
                )
            raise HTTPException(
                status_code=422,
                detail=(
                    "No supported source files found in this repository. "
                    "CodeScope currently understands Python, JavaScript/TypeScript, "
                    "Java, Go, Rust, C/C++, Ruby, and PHP."
                ),
            )

        # Step 3 — graph
        db.clear()
        db.load_nodes(nodes)

        # Step 4 — embeddings
        clear_collection()
        vectors_stored = store_functions(nodes)

        # Gather stats
        graph_stats = db.stats()
        files_parsed = len(set(n["file"] for n in nodes))

        return {
            "status": "ready",
            "repo_url": req.url,
            "stats": {
                "files_parsed": files_parsed,
                "functions": graph_stats["functions"],
                "classes": graph_stats["classes"],
                "graph_nodes": graph_stats["functions"] + graph_stats["classes"],
                "graph_edges": graph_stats["edges"],
                "vectors_stored": vectors_stored,
                "languages": languages,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    GraphRAG-powered codebase Q&A.
    Combines vector search with Neo4j graph traversal.
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        return graphrag_chat(req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/security")
async def security():
    """
    Scan the cloned repo for security vulnerabilities.
    Returns findings with LLM explanations for the top 5.
    """
    try:
        findings = scan_repo(REPO_PATH)
        findings = explain_findings(findings, max_explanations=5)
        return {
            "findings": findings,
            "total": len(findings),
            "by_type": {
                vtype: sum(1 for f in findings if f["type"] == vtype)
                for vtype in ["sql_injection", "hardcoded_secret", "command_injection", "path_traversal"]
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/diagram/architecture")
async def diagram_architecture():
    """Generate a Mermaid.js file-level architecture diagram."""
    try:
        return {"mermaid": generate_file_diagram()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/diagram/classes")
async def diagram_classes():
    """Generate a Mermaid.js class diagram."""
    try:
        return {"mermaid": generate_class_diagram()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def stats():
    """Return current graph statistics."""
    try:
        return db.stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
