"""Hybrid retrieval: vector cosine + BM25 (Postgres tsvector), merged via RRF.

Pattern reuses the vector SQL from apps/investment-agent/tools/memos.py,
adapted to the rag.* schema and enriched with a BM25 path for robust recall
when the embedding model struggles (rare keywords, acronyms, code snippets).

Reciprocal Rank Fusion (RRF) is stateless, tuning-free, and well-studied — it
just sums 1/(k+rank) across the two rankings and sorts by total. k=60 is the
standard choice.
"""
from __future__ import annotations

import logging
from typing import Any

from rag_server.db import query, query_one
from rag_server.embedding import embed_one

logger = logging.getLogger(__name__)

_RRF_K = 60


def _vector_hits(embedding: list[float], limit: int, source_kind: str | None) -> list[dict[str, Any]]:
    """Cosine similarity via pgvector's `<=>` distance operator."""
    if source_kind:
        sql = """
            SELECT c.id, c.source_id, c.text, c.chunk_index, c.metadata,
                   s.kind AS source_kind, s.origin AS source_origin, s.title AS source_title,
                   1 - (c.embedding <=> %s::vector) AS score
            FROM rag.chunks c
            JOIN rag.sources s ON s.id = c.source_id
            WHERE c.embedding IS NOT NULL AND s.kind = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        return query(sql, (embedding, source_kind, embedding, limit))
    sql = """
        SELECT c.id, c.source_id, c.text, c.chunk_index, c.metadata,
               s.kind AS source_kind, s.origin AS source_origin, s.title AS source_title,
               1 - (c.embedding <=> %s::vector) AS score
        FROM rag.chunks c
        JOIN rag.sources s ON s.id = c.source_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    return query(sql, (embedding, embedding, limit))


def _bm25_hits(query_text: str, limit: int, source_kind: str | None) -> list[dict[str, Any]]:
    """BM25-ish: Postgres `ts_rank` over the `simple`-config tsvector.

    Not true BM25, but close enough for personal scale and works without extra
    deps. The `simple` config doesn't stem, which is a plus for mixed-language
    content where English-stemming would lose Korean tokens.
    """
    ts_query = " | ".join(w for w in query_text.split() if len(w) > 1)
    if not ts_query:
        return []
    if source_kind:
        sql = """
            SELECT c.id, c.source_id, c.text, c.chunk_index, c.metadata,
                   s.kind AS source_kind, s.origin AS source_origin, s.title AS source_title,
                   ts_rank(c.tsv, to_tsquery('simple', %s)) AS score
            FROM rag.chunks c
            JOIN rag.sources s ON s.id = c.source_id
            WHERE c.tsv @@ to_tsquery('simple', %s) AND s.kind = %s
            ORDER BY score DESC
            LIMIT %s
        """
        return query(sql, (ts_query, ts_query, source_kind, limit))
    sql = """
        SELECT c.id, c.source_id, c.text, c.chunk_index, c.metadata,
               s.kind AS source_kind, s.origin AS source_origin, s.title AS source_title,
               ts_rank(c.tsv, to_tsquery('simple', %s)) AS score
        FROM rag.chunks c
        JOIN rag.sources s ON s.id = c.source_id
        WHERE c.tsv @@ to_tsquery('simple', %s)
        ORDER BY score DESC
        LIMIT %s
    """
    return query(sql, (ts_query, ts_query, limit))


def _rrf_merge(lists: list[list[dict[str, Any]]], k: int = _RRF_K) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion — deterministic, tuning-free merge."""
    scores: dict[int, float] = {}
    rowmap: dict[int, dict[str, Any]] = {}
    for hits in lists:
        for rank, row in enumerate(hits):
            cid = row["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            if cid not in rowmap:
                rowmap[cid] = row
    merged = []
    for cid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        row = dict(rowmap[cid])
        row["fusion_score"] = score
        merged.append(row)
    return merged


def search(query_text: str, limit: int = 10, source_kind: str | None = None) -> list[dict[str, Any]]:
    """Top-`limit` chunks by hybrid (vector + BM25) ranking.

    Args:
        query_text: natural-language query (KR or EN)
        limit: max results (1..50)
        source_kind: optional filter ('claude_session'|'manual_note'|'plan'|'project_doc'|'idea_harness')
    """
    limit = max(1, min(limit, 50))
    fetch = limit * 2  # over-fetch then RRF-merge

    vec_hits: list[dict[str, Any]] = []
    emb = embed_one(query_text, input_type="query")
    if emb is not None:
        vec_hits = _vector_hits(emb, fetch, source_kind)
    else:
        logger.warning("search(): embedding unavailable, falling back to BM25 only")

    bm25 = _bm25_hits(query_text, fetch, source_kind)
    merged = _rrf_merge([vec_hits, bm25])
    return merged[:limit]


def get_source(source_id: int) -> dict[str, Any] | None:
    """Full source metadata + joined chunks count."""
    src = query_one(
        """
        SELECT s.id, s.kind, s.origin, s.title, s.metadata, s.created_at, s.updated_at,
               COUNT(c.id) AS chunk_count
        FROM rag.sources s
        LEFT JOIN rag.chunks c ON c.source_id = s.id
        WHERE s.id = %s
        GROUP BY s.id
        """,
        (source_id,),
    )
    if not src:
        return None
    src["chunks"] = query(
        "SELECT id, chunk_index, text, metadata FROM rag.chunks WHERE source_id = %s ORDER BY chunk_index",
        (source_id,),
    )
    return src


def list_sources(source_kind: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Recent sources with chunk counts."""
    limit = max(1, min(limit, 200))
    if source_kind:
        sql = """
            SELECT s.id, s.kind, s.origin, s.title, s.created_at, COUNT(c.id) AS chunk_count
            FROM rag.sources s
            LEFT JOIN rag.chunks c ON c.source_id = s.id
            WHERE s.kind = %s
            GROUP BY s.id
            ORDER BY s.created_at DESC
            LIMIT %s
        """
        return query(sql, (source_kind, limit))
    sql = """
        SELECT s.id, s.kind, s.origin, s.title, s.created_at, COUNT(c.id) AS chunk_count
        FROM rag.sources s
        LEFT JOIN rag.chunks c ON c.source_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
        LIMIT %s
    """
    return query(sql, (limit,))
