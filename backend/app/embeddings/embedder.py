"""
Local embedding model using sentence-transformers.
Model: all-MiniLM-L6-v2
- Size: ~80MB (downloads once to ~/.cache/huggingface)
- Dimension: 384
- Runs on CPU, completely free, no API key needed
"""

from sentence_transformers import SentenceTransformer

# Loaded once at module import — subsequent calls are instant
_model = SentenceTransformer("all-MiniLM-L6-v2")

# Vector dimension — must match the Qdrant collection config
DIM = 384


def embed(text: str) -> list[float]:
    """Embed a single string. Returns a normalized float list of length DIM."""
    vec = _model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of strings in one batch.
    Much faster than calling embed() in a loop.
    """
    vecs = _model.encode(texts, normalize_embeddings=True, batch_size=32)
    return vecs.tolist()
