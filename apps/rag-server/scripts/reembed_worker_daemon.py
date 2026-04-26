"""Persistent reembed worker — runs forever as a separate docker-compose service.

Picks chunks with NULL embedding and fills them in. Key differences from the
one-shot `reembed_missing.py`:

  - **Runs forever** (daemon-style) instead of exiting when queue empties
  - **Priority ordering**: `manual_note` chunks first (newest id), so notes added
    via `add_note` become semantically searchable within ~1-2 seconds instead of
    waiting for the back of an 8000-chunk queue.
  - **Idle sleep**: when nothing to do, checks every N seconds (default 30).
    Near-zero API usage when queue is empty.
  - **Rate-limit tolerant**: exponential backoff + retry. Survives Voyage outages.

Deployed as its own service (`rag-worker`) in docker-compose, sharing the
jdp-rag-server image. `restart: unless-stopped` handles crashes.

Env vars:
  REEMBED_BATCH        default 32   — chunks per Voyage call
  REEMBED_IDLE_SLEEP   default 30s  — sleep when no NULL chunks to process
  REEMBED_BUSY_SLEEP   default 1s   — sleep between successful batches
  REEMBED_RETRY_SLEEP  default 10s  — base sleep for rate-limit backoff
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time

from psycopg2.extras import execute_batch

from rag_server.config import settings
from rag_server.db import get_conn
from rag_server.embedding import get_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("reembed-daemon")

BATCH_SIZE = int(os.getenv("REEMBED_BATCH", "32"))
IDLE_SLEEP = float(os.getenv("REEMBED_IDLE_SLEEP", "30"))
BUSY_SLEEP = float(os.getenv("REEMBED_BUSY_SLEEP", "1"))
RETRY_SLEEP = float(os.getenv("REEMBED_RETRY_SLEEP", "10"))
MAX_RETRIES = int(os.getenv("REEMBED_MAX_RETRIES", "10"))


_shutdown = False


def _install_signal_handlers() -> None:
    def handler(signum, _frame):
        global _shutdown
        log.info("caught signal %d, shutting down after current batch", signum)
        _shutdown = True

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(t in msg for t in ("rate limit", "429", "payment", "tpm", "rpm"))


def _fetch_next_batch(batch_size: int) -> list[tuple[int, str]]:
    """Priority-ordered fetch:
    1. `manual_note` chunks first (newest id first — user just saved them)
    2. Everything else, oldest id first (background backfill order)
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.text
            FROM rag.chunks c
            JOIN rag.sources s ON s.id = c.source_id
            WHERE c.embedding IS NULL
            ORDER BY
                CASE WHEN s.kind = 'manual_note' THEN 0 ELSE 1 END,
                CASE WHEN s.kind = 'manual_note' THEN -c.id ELSE c.id END
            LIMIT %s
            """,
            (batch_size,),
        )
        return cur.fetchall()


def _embed_with_retry(client, texts: list[str]) -> list[list[float]] | None:
    for attempt in range(MAX_RETRIES):
        try:
            r = client.embed(texts, model=settings.voyage_model, input_type="document")
            return r.embeddings
        except Exception as e:
            if _is_rate_limit_error(e):
                wait = RETRY_SLEEP * (1.5**attempt)
                wait = min(wait, 120)
                log.warning("rate-limited (attempt %d/%d), sleeping %.1fs", attempt + 1, MAX_RETRIES, wait)
                time.sleep(wait)
                continue
            log.error("embed error: %s", str(e)[:200])
            return None
    log.error("exhausted %d retries for batch", MAX_RETRIES)
    return None


def _update_chunks(ids: list[int], embeddings: list[list[float]]) -> None:
    conn = get_conn()
    with conn.cursor() as cur:
        execute_batch(
            cur,
            "UPDATE rag.chunks SET embedding = %s::vector WHERE id = %s",
            list(zip(embeddings, ids)),
            page_size=BATCH_SIZE,
        )
    conn.commit()


def main() -> int:
    log.info(
        "reembed-daemon start: batch=%d idle_sleep=%.1fs busy_sleep=%.1fs retry_sleep=%.1fs model=%s",
        BATCH_SIZE, IDLE_SLEEP, BUSY_SLEEP, RETRY_SLEEP, settings.voyage_model,
    )
    _install_signal_handlers()

    while not _shutdown:
        try:
            client = get_client()
            if client is None:
                log.warning("voyage client unavailable (missing VOYAGE_API_KEY?); idling")
                time.sleep(IDLE_SLEEP)
                continue

            rows = _fetch_next_batch(BATCH_SIZE)
            if not rows:
                time.sleep(IDLE_SLEEP)
                continue

            ids = [r[0] for r in rows]
            texts = [r[1] for r in rows]
            # Determine priority label for log visibility
            priority_label = "queue"
            with get_conn().cursor() as cur:
                cur.execute(
                    "SELECT DISTINCT s.kind FROM rag.chunks c JOIN rag.sources s ON s.id = c.source_id WHERE c.id = ANY(%s)",
                    (ids,),
                )
                kinds = [r[0] for r in cur.fetchall()]
                if "manual_note" in kinds:
                    priority_label = "NOTE"

            embeddings = _embed_with_retry(client, texts)
            if embeddings is None:
                log.error("batch failed permanently (ids %s..%s); sleeping", ids[0], ids[-1])
                time.sleep(RETRY_SLEEP * 3)
                continue

            _update_chunks(ids, embeddings)
            log.info("[%s] +%d chunks embedded (ids %s..%s)", priority_label, len(rows), ids[0], ids[-1])
            time.sleep(BUSY_SLEEP)

        except Exception as e:
            log.exception("unexpected error in main loop: %s", e)
            time.sleep(IDLE_SLEEP)

    log.info("daemon exiting cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
