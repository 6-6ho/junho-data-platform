"""Re-embed chunks that have NULL embedding — rate-limit tolerant.

Used after bulk ingestion runs with no/partial embeddings. Walks
`rag.chunks` where `embedding IS NULL` and fills them in. Designed to
survive Voyage free-tier rate limits (3 RPM / 10K TPM) and run for hours
in the background.

Free-tier math:
    3 RPM  → wait ≥20s between successful calls
    10K TPM → batch ≤ 15 chunks (~7.5k tokens at 500/chunk)
    → ~45 chunks/minute → ~2700/hour → 36k chunks in ~13 hours

Usage (inside container, background):
    docker exec -d -e VOYAGE_API_KEY=... -e PYTHONPATH=/app jdp-rag \
        bash -c 'nohup python /app/scripts/reembed_missing.py \
            > /tmp/reembed.log 2>&1 &'

    tail -f /tmp/reembed.log   # monitor

    # to stop:
    docker exec jdp-rag pkill -f reembed_missing.py
"""
from __future__ import annotations

import logging
import os
import random
import sys
import time

from psycopg2.extras import execute_batch

from rag_server.config import settings
from rag_server.db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("reembed")

BATCH_SIZE = int(os.getenv("REEMBED_BATCH", "15"))
MIN_SLEEP_BETWEEN_BATCHES = float(os.getenv("REEMBED_SLEEP", "22"))  # 3 RPM = 20s, margin
MAX_RETRIES = int(os.getenv("REEMBED_MAX_RETRIES", "20"))
INITIAL_RETRY_SLEEP = float(os.getenv("REEMBED_RETRY_SLEEP", "60"))


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "rate limit" in msg
        or "429" in msg
        or "payment" in msg
        or "tpm" in msg
        or "rpm" in msg
    )


def _embed_with_retry(client, texts: list[str]) -> list[list[float]] | None:
    """Call client.embed(...) with explicit backoff on rate-limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            r = client.embed(texts, model=settings.voyage_model, input_type="document")
            return r.embeddings
        except Exception as e:
            if _is_rate_limit_error(e):
                wait = INITIAL_RETRY_SLEEP * (1.3**attempt) + random.uniform(0, 10)
                wait = min(wait, 600)  # cap at 10 min
                log.warning(
                    "rate-limited (attempt %d/%d), sleeping %.1fs",
                    attempt + 1, MAX_RETRIES, wait,
                )
                time.sleep(wait)
                continue
            log.error("non-rate-limit error on embed: %s", e)
            return None
    log.error("exhausted retries")
    return None


def main() -> int:
    # lazy import so we can adjust batch size before voyage client construction
    from rag_server.embedding import get_client  # noqa: E402

    client = get_client()
    if client is None:
        log.error("VOYAGE_API_KEY not configured; cannot reembed")
        return 2

    conn = get_conn()
    total_processed = 0
    total_failed = 0
    start = time.time()

    log.info(
        "reembed starting: batch=%d sleep=%.1fs model=%s",
        BATCH_SIZE, MIN_SLEEP_BETWEEN_BATCHES, settings.voyage_model,
    )

    while True:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*)::int FROM rag.chunks WHERE embedding IS NULL"
            )
            remaining = cur.fetchone()[0]

        if remaining == 0:
            log.info("all chunks embedded; exiting normally")
            break

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, text FROM rag.chunks WHERE embedding IS NULL "
                "ORDER BY id LIMIT %s",
                (BATCH_SIZE,),
            )
            rows = cur.fetchall()

        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]

        call_start = time.time()
        embeddings = _embed_with_retry(client, texts)

        if embeddings is None:
            log.error(
                "batch failed permanently (ids=%s..%s); skipping and sleeping",
                ids[0], ids[-1],
            )
            total_failed += len(ids)
            # Mark these rows with a sentinel so we don't infinite-loop on them.
            # Use a zero-vector: retrieval will score them 0 (~no match) but they
            # survive as BM25-searchable rows. Operator can re-run after fixing.
            # For now just sleep and try again with the NEXT batch (which skips these).
            # Actually we re-query NULL each loop so they'll re-appear. Break out
            # after too many consecutive failures instead.
            if total_failed > 200:
                log.error("too many failures (%d), giving up", total_failed)
                return 1
            time.sleep(MIN_SLEEP_BETWEEN_BATCHES)
            continue

        with conn.cursor() as cur:
            execute_batch(
                cur,
                "UPDATE rag.chunks SET embedding = %s::vector WHERE id = %s",
                list(zip(embeddings, ids)),
                page_size=BATCH_SIZE,
            )
        conn.commit()

        total_processed += len(rows)
        elapsed_total = time.time() - start
        rate = total_processed / elapsed_total if elapsed_total > 0 else 0
        eta_sec = (remaining - len(rows)) / rate if rate > 0 else float("inf")

        log.info(
            "ok +%d  total %d  remaining ~%d  rate %.1f/min  ETA %.0fm",
            len(rows),
            total_processed,
            remaining - len(rows),
            rate * 60,
            eta_sec / 60 if eta_sec != float("inf") else -1,
        )

        # Pace the next call to stay under RPM. Account for elapsed call time.
        elapsed_call = time.time() - call_start
        sleep_for = MIN_SLEEP_BETWEEN_BATCHES - elapsed_call
        if sleep_for > 0:
            time.sleep(sleep_for)

    log.info(
        "reembed done. processed=%d failed=%d elapsed=%.1fs",
        total_processed, total_failed, time.time() - start,
    )
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
