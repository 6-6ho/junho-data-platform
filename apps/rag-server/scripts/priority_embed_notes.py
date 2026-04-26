"""Embed all manual_note chunks with NULL embedding — priority fill.

Run right after `add_note` calls to avoid waiting for the background reembed
loop to reach them (which processes in id order and notes are at the end).

Usage (inside container):
    VOYAGE_API_KEY=... PYTHONPATH=/app python /app/scripts/priority_embed_notes.py
"""
from __future__ import annotations

import logging
import sys

from psycopg2.extras import execute_batch

from rag_server.db import get_conn
from rag_server.embedding import get_client
from rag_server.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("priority-embed")


def main() -> int:
    client = get_client()
    if client is None:
        log.error("VOYAGE_API_KEY not configured")
        return 2

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.text
            FROM rag.chunks c
            JOIN rag.sources s ON s.id = c.source_id
            WHERE c.embedding IS NULL
              AND s.kind = 'manual_note'
            ORDER BY c.id
            """
        )
        rows = cur.fetchall()

    if not rows:
        log.info("no manual_note chunks need embedding")
        return 0

    log.info("found %d manual_note chunks to embed", len(rows))
    ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]

    try:
        r = client.embed(texts, model=settings.voyage_model, input_type="document")
        embeddings = r.embeddings
    except Exception as e:
        log.error("voyage embed failed: %s", e)
        return 1

    with conn.cursor() as cur:
        execute_batch(
            cur,
            "UPDATE rag.chunks SET embedding = %s::vector WHERE id = %s",
            list(zip(embeddings, ids)),
            page_size=len(ids),
        )
    conn.commit()

    log.info("embedded %d manual_note chunks (ids=%s)", len(rows), ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
