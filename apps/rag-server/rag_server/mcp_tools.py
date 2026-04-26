"""MCP tools exposed to Claude.

Each tool is a thin wrapper around the retrieve/ingest layer. The docstrings
here are what Claude reads when deciding whether to call a tool, so they
describe the trigger conditions in plain user-facing language.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from ingest.common import (
    bulk_insert_chunks,
    delete_existing_chunks,
    upsert_source,
)
from ingest.secret_scrubber import scrub
from rag_server.chunking import Chunk, chunk_text
from rag_server.db import get_conn
from rag_server.retrieve import get_source, list_sources as list_sources_impl, search as search_impl

logger = logging.getLogger(__name__)

SourceKind = Literal["claude_session", "manual_note", "plan", "project_doc", "idea_harness"]


def tool_search(
    query: str,
    limit: int = 10,
    source_kind: SourceKind | None = None,
) -> str:
    """Semantic search across Junho's personal knowledge base.

    Use this whenever the user asks about their past work, previous
    conversations, notes, or project context — things they wouldn't expect
    Claude to know unless it was stored here. Korean or English queries
    both work (the embedding model is multilingual).

    Args:
        query: Natural-language search query.
        limit: Max results (1..50, default 10).
        source_kind: Restrict results to one kind:
            - 'claude_session'  past Claude Code sessions
            - 'manual_note'     notes saved via add_note
            - 'plan'            implementation plans
            - 'project_doc'     junho-data-platform docs
            - 'idea_harness'    (reserved, future)
            Leave None to search everything.

    Returns:
        A JSON array of matching chunks with `source_kind`, `source_origin`,
        `source_title`, `chunk_index`, `text`, and a `fusion_score`. When
        nothing matches, returns an empty array.
    """
    rows = search_impl(query, limit=limit, source_kind=source_kind)
    trimmed = [
        {
            "id": r["id"],
            "source_id": r["source_id"],
            "source_kind": r["source_kind"],
            "source_origin": r["source_origin"],
            "source_title": r["source_title"],
            "chunk_index": r["chunk_index"],
            "text": r["text"],
            "fusion_score": round(float(r["fusion_score"]), 4),
        }
        for r in rows
    ]
    return json.dumps(trimmed, ensure_ascii=False, default=str)


def tool_get_document(source_id: int) -> str:
    """Fetch the full source document (all chunks) for a matched source.

    Use this AFTER `search` when the user wants more context around a
    specific match and you want to see the surrounding chunks instead of
    just the highlighted one. Don't call this speculatively — it can return
    a lot of text for long sessions.

    Args:
        source_id: The `source_id` field from a `search` result.

    Returns:
        JSON with source metadata and an ordered list of chunks. Returns
        `{"error": "not_found"}` if no such source exists.
    """
    src = get_source(source_id)
    if src is None:
        return json.dumps({"error": "not_found", "source_id": source_id})
    return json.dumps(src, ensure_ascii=False, default=str)


def tool_add_note(
    content: str,
    tags: list[str] | None = None,
    title: str | None = None,
) -> str:
    """Save a manual note to the knowledge base.

    Use when the user says "remember this", "save this", "add to my RAG",
    "이거 기억해둬", or explicitly asks to store information for later
    retrieval. Do NOT use for summaries of the current conversation unless
    the user explicitly asks — Claude session ingestion already captures
    that automatically.

    Insert path is synchronous and fast (~50ms): content is scrubbed, chunked,
    and written to Postgres with NULL embedding. A separate background worker
    (`rag-worker` service) fills in the embedding within ~1–2 seconds using a
    priority queue that puts `manual_note` kind first. BM25 full-text search
    works immediately; vector search becomes available once the worker catches
    up.

    Args:
        content: The note body (plain text or Markdown). Scrubbed for
                 secrets before storage.
        tags: Optional tags to categorize the note (e.g., ['postgres',
              'debugging']). Stored in source metadata.
        title: Optional short title (<120 chars). If omitted, the first
               line of `content` is used.

    Returns:
        JSON with `source_id`, `chunk_count`, `redacted_hits`, `title`, and a
        `status` hint. The embedding is handled asynchronously — callers
        should not block on an `embedded: true` flag.
    """
    if not content or not content.strip():
        return json.dumps({"error": "empty_content"})

    scrubbed, redacted = scrub(content)
    if not title:
        title = scrubbed.strip().splitlines()[0][:120]

    pieces = chunk_text(scrubbed)
    chunks = [Chunk(text=p, metadata={"tags": tags or []}) for p in pieces]

    origin = f"note:{title}:{len(scrubbed)}"
    source_id = upsert_source(
        kind="manual_note",
        origin=origin,
        title=title,
        metadata={"tags": tags or [], "redacted_hits": redacted},
    )
    delete_existing_chunks(source_id)
    # Insert with NULL embedding. The rag-worker daemon prioritizes manual_note
    # chunks and will fill them in within seconds. Inline embed was removed to
    # decouple tool response latency from Voyage API stability.
    inserted = bulk_insert_chunks(source_id, chunks, embeddings=None)

    return json.dumps(
        {
            "source_id": source_id,
            "chunk_count": inserted,
            "redacted_hits": redacted,
            "title": title,
            "status": "saved; embedding queued (rag-worker will backfill within ~2s)",
        },
        ensure_ascii=False,
    )


def tool_list_sources(
    source_kind: SourceKind | None = None,
    limit: int = 20,
) -> str:
    """Browse the sources currently in the knowledge base.

    Use when the user wants an inventory ("what's in my RAG?", "recent
    notes?"). Don't use this in place of `search` when the user is looking
    for specific content — `search` is strictly better for that.

    Args:
        source_kind: Filter by kind (same options as `search`). None = all.
        limit: Max entries (1..200, default 20).

    Returns:
        JSON array of `{id, kind, origin, title, created_at, chunk_count}`.
    """
    rows = list_sources_impl(source_kind=source_kind, limit=limit)
    return json.dumps(rows, ensure_ascii=False, default=str)


def tool_delete_note(source_id: int) -> str:
    """Delete a manually-added note.

    Only works for `kind='manual_note'` sources. Other source kinds
    (claude_session, project_doc, plan, idea_harness) are re-ingested
    from files and cannot be deleted through this tool — their deletion
    would be pointless because the next re-ingest would recreate them.

    Args:
        source_id: The id of the manual_note source to remove.

    Returns:
        JSON with `{deleted: bool, reason?: str}`.
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT kind FROM rag.sources WHERE id = %s", (source_id,))
        row = cur.fetchone()
        if not row:
            return json.dumps({"deleted": False, "reason": "not_found"})
        if row[0] != "manual_note":
            return json.dumps(
                {"deleted": False, "reason": f"refuse: kind={row[0]} cannot be deleted via MCP"}
            )
        cur.execute("DELETE FROM rag.sources WHERE id = %s", (source_id,))
    return json.dumps({"deleted": True, "source_id": source_id})
