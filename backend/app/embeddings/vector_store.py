"""
Qdrant Cloud Free vector store.
Stores function embeddings for semantic search.
Falls back to in-memory Qdrant if cloud credentials aren't set
(useful for offline development on Day 3-4).
"""

import os
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

from .embedder import embed, embed_batch, DIM

load_dotenv()

COLLECTION = "code_functions"


def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    key = os.getenv("QDRANT_API_KEY")

    if url and key and not url.startswith("https://REPLACE"):
        # Qdrant Cloud — persists data between restarts
        return QdrantClient(url=url, api_key=key)
    else:
        # In-memory fallback — data lost on restart, good for dev
        print("[vector_store] No Qdrant Cloud credentials found — using in-memory mode")
        return QdrantClient(":memory:")


# Module-level client — created once
_client = _get_client()


def _init_collection() -> None:
    """Create the Qdrant collection if it doesn't already exist."""
    existing = [c.name for c in _client.get_collections().collections]
    if COLLECTION not in existing:
        _client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )


def store_functions(nodes: list[dict]) -> int:
    """
    Embed all function nodes and upsert them into Qdrant.
    Returns the number of vectors stored.
    """
    _init_collection()

    fn_nodes = [n for n in nodes if n["type"] == "function"]
    if not fn_nodes:
        return 0

    # Build text representation for each function
    texts = [
        f"Function: {n['name']}\nFile: {n['file']}\n"
        f"Class: {n.get('class', '')}\nCalls: {', '.join(n.get('calls', []))}"
        for n in fn_nodes
    ]

    vectors = embed_batch(texts)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=v,
            payload={
                "name": n["name"],
                "file": n["file"],
                "class": n.get("class", ""),
                "calls": n.get("calls", []),
                "start_line": n.get("start_line", 0),
            },
        )
        for n, v in zip(fn_nodes, vectors)
    ]

    _client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search: find the top_k most relevant functions for a query.
    Returns a list of payload dicts.
    """
    try:
        vector = embed(query)
        hits = _client.search(
            collection_name=COLLECTION,
            query_vector=vector,
            limit=top_k,
        )
        return [h.payload for h in hits]
    except Exception:
        # Collection might not exist yet (no repo analyzed)
        return []


def clear_collection() -> None:
    """Delete and recreate the collection (called before each new repo analysis)."""
    existing = [c.name for c in _client.get_collections().collections]
    if COLLECTION in existing:
        _client.delete_collection(COLLECTION)
    _init_collection()
