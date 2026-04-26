"""Shared ingestion helpers: upsert sources, bulk insert chunks.

All ingest scripts (`claude_jsonl`, `markdown`, manual notes) use these so
the DB write path is consistent and transactional.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from psycopg2.extras import execute_values

from rag_server.chunking import Chunk
from rag_server.db import get_conn, query_one
from rag_server.embedding import embed_batch

logger = logging.getLogger(__name__)


def upsert_source(kind: str, origin: str, title: str | None, metadata: dict[str, Any] | None) -> int:
    """Return source_id, inserting or updating the (kind, origin) row."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO rag.sources (kind, origin, title, metadata)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (kind, origin) DO UPDATE
                SET title = EXCLUDED.title,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            RETURNING id
            """,
            (kind, origin, title, json.dumps(metadata or {})),
        )
        row = cur.fetchone()
        return int(row[0])


def delete_existing_chunks(source_id: int) -> int:
    """Wipe chunks for a source before re-inserting (idempotent re-ingestion)."""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM rag.chunks WHERE source_id = %s", (source_id,))
        return cur.rowcount


def bulk_insert_chunks(
    source_id: int,
    chunks: list[Chunk],
    embeddings: list[list[float]] | None,
) -> int:
    """Insert chunks with embeddings (or NULL embedding if Voyage was unreachable).

    When embeddings is None we still insert rows so BM25 fallback works and a
    later re-embedding pass can fill them in.
    """
    if not chunks:
        return 0
    rows = []
    for idx, chunk in enumerate(chunks):
        emb = embeddings[idx] if embeddings is not None else None
        rows.append(
            (
                source_id,
                idx,
                chunk.text,
                len(chunk.text),  # rough token estimate; replace with tiktoken later if needed
                emb,
                json.dumps(chunk.metadata),
            )
        )

    conn = get_conn()
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO rag.chunks (source_id, chunk_index, text, token_count, embedding, metadata)
            VALUES %s
            ON CONFLICT (source_id, chunk_index) DO UPDATE
                SET text = EXCLUDED.text,
                    token_count = EXCLUDED.token_count,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
            """,
            rows,
            template="(%s, %s, %s, %s, %s::vector, %s::jsonb)",
        )
    return len(rows)


def embed_and_insert(source_id: int, chunks: list[Chunk]) -> tuple[int, bool]:
    """Full path: scrub → embed → insert. Returns (count, embedded).

    `embedded=False` means the row was inserted without embeddings (Voyage
    unreachable or key missing). BM25 still works; a re-embed pass can fix it.
    """
    texts = [c.text for c in chunks]
    embeddings = embed_batch(texts, input_type="document")
    inserted = bulk_insert_chunks(source_id, chunks, embeddings)
    return inserted, embeddings is not None


def stats() -> dict[str, Any]:
    return {
        "sources_total": query_one("SELECT COUNT(*)::int AS n FROM rag.sources")["n"],
        "chunks_total": query_one("SELECT COUNT(*)::int AS n FROM rag.chunks")["n"],
        "chunks_embedded": query_one(
            "SELECT COUNT(*)::int AS n FROM rag.chunks WHERE embedding IS NOT NULL"
        )["n"],
        "by_kind": query_one(
            """
            SELECT json_object_agg(kind, cnt) AS by_kind FROM (
                SELECT kind, COUNT(*)::int AS cnt FROM rag.sources GROUP BY kind
            ) t
            """
        )
        or {"by_kind": {}},
    }
