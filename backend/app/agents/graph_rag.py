"""
GraphRAG chat agent.
Pipeline:
  1. Vector search (Qdrant) → top-5 semantically similar functions
  2. Graph traversal (Neo4j) → neighbors of each hit (callers/callees)
  3. Merge + deduplicate context
  4. LLM (Ollama or Groq) → synthesize answer

This is what makes it "GraphRAG" vs plain RAG:
the graph layer surfaces related functions that pure
vector search would miss.
"""

from ..embeddings.vector_store import search
from ..graph.neo4j_client import GraphDB
from ..llm import chat

_db = GraphDB()

SYSTEM_PROMPT = """You are a senior software engineer helping a developer understand a codebase.

You have been given context retrieved via GraphRAG — a combination of:
1. Semantic search (functions most similar to the question by meaning)
2. Knowledge graph traversal (callers and callees of those functions from Neo4j)

Use this rich context to give a detailed, accurate answer about the codebase architecture.
Reference specific function names and file paths when relevant.
If you are unsure, say so — do not make things up."""


def graphrag_chat(question: str) -> dict:
    """
    Answer a question about the codebase using GraphRAG.
    Returns: answer string, vector sources, and count of graph-expanded nodes.
    """

    # Step 1 — semantic vector search
    vector_hits = search(question, top_k=5)

    if not vector_hits:
        return {
            "answer": "No codebase has been analyzed yet. Please submit a GitHub URL first.",
            "sources": [],
            "graph_expanded": 0,
        }

    # Step 2 — graph traversal to expand context
    all_context = list(vector_hits)
    seen_names: set[str] = {r.get("name", "") for r in vector_hits}

    for hit in vector_hits:
        fn_name = hit.get("name", "")
        if not fn_name:
            continue
        try:
            neighbors = _db.get_neighbors(fn_name, depth=2)
            for neighbor in neighbors:
                name = neighbor.get("name", "")
                if name and name not in seen_names:
                    all_context.append(neighbor)
                    seen_names.add(name)
        except Exception:
            # Graph traversal failure is non-fatal — fall back to vector-only
            pass

    graph_expanded = len(all_context) - len(vector_hits)

    # Step 3 — build context string
    context_lines = []
    for node in all_context[:15]:  # cap at 15 to keep prompt size manageable
        name = node.get("name", "?")
        file_ = node.get("file", "?")
        calls = node.get("calls", [])
        line = f"  fn: {name}  |  file: {file_}"
        if calls:
            line += f"  |  calls: {', '.join(calls[:5])}"
        context_lines.append(line)

    context = "\n".join(context_lines)

    # Step 4 — call LLM
    user_message = (
        f"Codebase context (GraphRAG — {len(all_context)} functions, "
        f"{graph_expanded} found via graph expansion):\n\n"
        f"{context}\n\n"
        f"Question: {question}"
    )

    answer = chat(SYSTEM_PROMPT, user_message)

    return {
        "answer": answer,
        "sources": vector_hits,
        "graph_expanded": graph_expanded,
        "total_context": len(all_context),
    }
