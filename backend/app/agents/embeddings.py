"""Shared embeddings client for vector search memory.

Model: nomic-ai/nomic-embed-text-v1.5 → 768-dimensional cosine vectors.
Falls back gracefully (returns []) if the Fireworks key is missing or the
call fails, so the rest of the system keeps running without embeddings.
"""
import logging
import os

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 768

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_fireworks import FireworksEmbeddings
        _embeddings = FireworksEmbeddings(
            model="nomic-ai/nomic-embed-text-v1.5",
            api_key=os.environ.get("FIREWORKS_API_KEY", ""),
        )
    return _embeddings


async def embed_text(text: str) -> list[float]:
    """Return a 768-dim embedding vector, or [] on failure."""
    try:
        emb = get_embeddings()
        # aembed_query runs embed_query in a thread executor internally
        return await emb.aembed_query(text)
    except Exception as e:
        logger.error(f"embed_text failed: {e}")
        return []
