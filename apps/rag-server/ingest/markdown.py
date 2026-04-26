"""Markdown / plain-text file → RAG source + chunks.

For `project_doc` and `plan` sources. Reads the whole file, scrubs secrets,
chunks with character-based overlap, inserts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from rag_server.chunking import Chunk, chunk_text

from ingest.common import delete_existing_chunks, embed_and_insert, upsert_source
from ingest.secret_scrubber import scrub

logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    path: str
    chunks_inserted: int
    secrets_redacted: int
    embedded: bool
    skipped: bool = False
    error: str | None = None


def _extract_title(text: str, fallback: str) -> str:
    """First Markdown H1 or first non-blank line."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("# "):
            return line[2:].strip()[:120]
        return line[:120]
    return fallback


def ingest_file(path: Path, kind: str = "project_doc", dry_run: bool = False) -> IngestStats:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return IngestStats(path=str(path), chunks_inserted=0, secrets_redacted=0,
                           embedded=False, skipped=True, error=str(e))

    scrubbed, redacted = scrub(raw)
    pieces = chunk_text(scrubbed)
    chunks = [Chunk(text=p, metadata={}) for p in pieces]
    if not chunks:
        return IngestStats(path=str(path), chunks_inserted=0, secrets_redacted=redacted,
                           embedded=False, skipped=True)

    if dry_run:
        return IngestStats(
            path=str(path), chunks_inserted=len(chunks),
            secrets_redacted=redacted, embedded=False,
        )

    source_id = upsert_source(
        kind=kind,
        origin=str(path),
        title=_extract_title(scrubbed, fallback=path.name),
        metadata={"file_mtime": path.stat().st_mtime, "size": len(scrubbed)},
    )
    delete_existing_chunks(source_id)
    inserted, embedded = embed_and_insert(source_id, chunks)
    return IngestStats(
        path=str(path), chunks_inserted=inserted,
        secrets_redacted=redacted, embedded=embedded,
    )
