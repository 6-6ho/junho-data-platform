"""Voyage AI embedding wrapper.

Pattern lifted from apps/investment-agent/embedding.py, upgraded to
voyage-3-large (1024-dim) for better retrieval quality on mixed
Korean/English content.

The client is lazy so missing VOYAGE_API_KEY doesn't crash startup —
endpoints that need embeddings will error clearly when called.
"""
from __future__ import annotations

import logging
from typing import Any

from rag_server.config import settings

logger = logging.getLogger(__name__)

_client: Any | None = None
_MAX_BATCH = 64  # Voyage supports up to 128; keep margin


def get_client():
    """Lazy voyageai.Client singleton."""
    global _client
    if _client is None:
        if not settings.voyage_api_key:
            logger.warning("VOYAGE_API_KEY unset — embedding disabled")
            return None
        import voyageai
        _client = voyageai.Client(api_key=settings.voyage_api_key)
        logger.info("voyage client ready, model=%s dim=%d", settings.voyage_model, settings.voyage_dim)
    return _client


def embed_one(text: str, input_type: str = "query") -> list[float] | None:
    """Single-text embedding. input_type='query' for search, 'document' for indexing."""
    client = get_client()
    if client is None:
        return None
    try:
        r = client.embed([text], model=settings.voyage_model, input_type=input_type)
        return r.embeddings[0]
    except Exception as e:
        logger.error("embed_one error: %s", e)
        return None


def embed_batch(texts: list[str], input_type: str = "document") -> list[list[float]] | None:
    """Batched embeddings. Auto-chunks into <=_MAX_BATCH sub-batches.

    Returns None on any failure (doesn't try to partially succeed — ingestion
    should fail loud so the caller can retry/resume).
    """
    if not texts:
        return []
    client = get_client()
    if client is None:
        return None
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), _MAX_BATCH):
            batch = texts[i : i + _MAX_BATCH]
            r = client.embed(batch, model=settings.voyage_model, input_type=input_type)
            out.extend(r.embeddings)
        return out
    except Exception as e:
        logger.error("embed_batch error at offset %d: %s", i, e)
        return None
