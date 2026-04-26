"""Claude Code session JSONL → RAG sources + chunks.

Each .jsonl file represents one session. Lines are events; we keep only the
user/assistant messages and group consecutive user→assistant pairs into
"turns". The first user message becomes the session title. Content is
scrubbed of secrets before chunking.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag_server.chunking import Turn, chunk_turns

from ingest.common import delete_existing_chunks, embed_and_insert, upsert_source
from ingest.secret_scrubber import scrub

logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    path: str
    turns: int
    chunks_inserted: int
    secrets_redacted: int
    embedded: bool
    skipped: bool = False
    error: str | None = None


def _extract_text(content: Any) -> str:
    """Flatten message.content — can be a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            t = block.get("type")
            if t == "text":
                parts.append(block.get("text", ""))
            elif t == "tool_use":
                name = block.get("name", "")
                inp = block.get("input", {})
                parts.append(f"[tool: {name}({json.dumps(inp, ensure_ascii=False)[:200]})]")
            elif t == "tool_result":
                res = block.get("content", "")
                if isinstance(res, list):
                    res = " ".join(
                        b.get("text", "") if isinstance(b, dict) else str(b) for b in res
                    )
                parts.append(f"[tool-result: {str(res)[:500]}]")
        return "\n".join(p for p in parts if p)
    return ""


def _group_into_turns(events: list[dict[str, Any]]) -> list[Turn]:
    """Build user→assistant turn pairs from a flat event stream."""
    turns: list[Turn] = []
    pending_user: dict[str, Any] | None = None

    for ev in events:
        t = ev.get("type")
        if t not in ("user", "assistant"):
            continue
        msg = ev.get("message", {})
        role = msg.get("role")
        text = _extract_text(msg.get("content", ""))
        if not text.strip():
            continue

        if role == "user":
            # flush any orphan user (user without assistant) as a turn on its own
            if pending_user is not None:
                turns.append(
                    Turn(
                        turn_id=pending_user["uuid"],
                        user_text=pending_user["text"],
                        assistant_text="",
                        timestamp=pending_user.get("ts"),
                    )
                )
            pending_user = {"uuid": ev.get("uuid", ""), "text": text, "ts": ev.get("timestamp")}
        elif role == "assistant":
            if pending_user is not None:
                turns.append(
                    Turn(
                        turn_id=pending_user["uuid"],
                        user_text=pending_user["text"],
                        assistant_text=text,
                        timestamp=pending_user.get("ts"),
                    )
                )
                pending_user = None
            else:
                # orphan assistant — keep as a turn with empty user
                turns.append(
                    Turn(
                        turn_id=ev.get("uuid", ""),
                        user_text="",
                        assistant_text=text,
                        timestamp=ev.get("timestamp"),
                    )
                )

    if pending_user is not None:
        turns.append(
            Turn(
                turn_id=pending_user["uuid"],
                user_text=pending_user["text"],
                assistant_text="",
                timestamp=pending_user.get("ts"),
            )
        )

    return turns


def _guess_title(turns: list[Turn]) -> str:
    for t in turns:
        if t.user_text:
            first_line = t.user_text.strip().splitlines()[0]
            return first_line[:120]
    return "(untitled session)"


def ingest_file(path: Path, since: str | None = None, dry_run: bool = False) -> IngestStats:
    """Ingest one JSONL file.

    Args:
        path: absolute path to a .jsonl session file
        since: optional ISO date; files whose mtime is older are skipped
        dry_run: parse + scrub + chunk without hitting the DB or Voyage
    """
    if since and path.stat().st_mtime_ns // 10**9 < _iso_to_epoch(since):
        return IngestStats(path=str(path), turns=0, chunks_inserted=0, secrets_redacted=0,
                           embedded=False, skipped=True)

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return IngestStats(path=str(path), turns=0, chunks_inserted=0, secrets_redacted=0,
                           embedded=False, skipped=True, error=str(e))

    events: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    turns = _group_into_turns(events)
    if not turns:
        return IngestStats(path=str(path), turns=0, chunks_inserted=0, secrets_redacted=0,
                           embedded=False, skipped=True)

    # scrub each turn's text before chunking
    total_redacted = 0
    for t in turns:
        t.user_text, n1 = scrub(t.user_text)
        t.assistant_text, n2 = scrub(t.assistant_text)
        total_redacted += n1 + n2

    chunks = chunk_turns(turns)
    if not chunks:
        return IngestStats(path=str(path), turns=len(turns), chunks_inserted=0,
                           secrets_redacted=total_redacted, embedded=False, skipped=True)

    if dry_run:
        return IngestStats(
            path=str(path), turns=len(turns), chunks_inserted=len(chunks),
            secrets_redacted=total_redacted, embedded=False,
        )

    source_id = upsert_source(
        kind="claude_session",
        origin=str(path),
        title=_guess_title(turns),
        metadata={"turn_count": len(turns), "file_mtime": path.stat().st_mtime},
    )
    delete_existing_chunks(source_id)
    inserted, embedded = embed_and_insert(source_id, chunks)

    return IngestStats(
        path=str(path), turns=len(turns), chunks_inserted=inserted,
        secrets_redacted=total_redacted, embedded=embedded,
    )


def _iso_to_epoch(iso: str) -> int:
    """'2026-03-14' → unix epoch seconds (UTC midnight)."""
    from datetime import datetime, timezone
    return int(datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp())
