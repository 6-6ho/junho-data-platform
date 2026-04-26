"""Ingestion CLI.

Examples (inside jdp-rag container):
    python -m ingest.run --kind claude_session --glob '/mnt/host/claude-projects/**/*.jsonl'
    python -m ingest.run --kind claude_session --glob '...' --since 2026-03-14
    python -m ingest.run --kind project_doc --path /mnt/host/jdp/CLAUDE.md --path /mnt/host/jdp/INFRA.md
    python -m ingest.run --kind plan --glob '/mnt/host/jdp/.claude/plans/*.md'
    python -m ingest.run --stats
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import sys
from pathlib import Path

from ingest import claude_jsonl as ingest_claude
from ingest import markdown as ingest_md
from ingest.common import stats as rag_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("ingest")


def main() -> int:
    p = argparse.ArgumentParser(prog="ingest")
    p.add_argument("--kind", choices=["claude_session", "project_doc", "plan"], help="source kind")
    p.add_argument("--path", action="append", default=[], help="explicit file path (repeatable)")
    p.add_argument("--glob", action="append", default=[], help="glob pattern (repeatable)")
    p.add_argument("--since", help="only files mtime >= this ISO date (claude_session only)")
    p.add_argument("--dry-run", action="store_true", help="parse + chunk only; no DB writes, no embeddings")
    p.add_argument("--stats", action="store_true", help="print DB stats and exit")
    p.add_argument("--limit", type=int, default=0, help="cap number of files processed (0 = no cap)")
    args = p.parse_args()

    if args.stats:
        print(json.dumps(rag_stats(), indent=2, default=str, ensure_ascii=False))
        return 0

    if not args.kind:
        log.error("--kind is required unless --stats")
        return 2

    files: list[Path] = []
    for pstr in args.path:
        files.append(Path(pstr))
    for pat in args.glob:
        files.extend(Path(m) for m in glob.glob(pat, recursive=True))

    # de-dup + keep only existing files
    seen = set()
    unique: list[Path] = []
    for f in files:
        r = f.resolve()
        if r in seen or not r.is_file():
            continue
        seen.add(r)
        unique.append(r)
    files = unique

    if args.limit > 0:
        files = files[: args.limit]

    if not files:
        log.warning("no matching files found")
        return 1

    log.info("ingesting %d file(s) as kind=%s dry_run=%s", len(files), args.kind, args.dry_run)

    total_chunks = 0
    total_redacted = 0
    embedded_files = 0
    failed: list[tuple[str, str]] = []

    for i, f in enumerate(files, 1):
        if args.kind == "claude_session":
            r = ingest_claude.ingest_file(f, since=args.since, dry_run=args.dry_run)
        else:
            r = ingest_md.ingest_file(f, kind=args.kind, dry_run=args.dry_run)

        if r.error:
            failed.append((str(f), r.error))
            continue

        total_chunks += r.chunks_inserted
        total_redacted += r.secrets_redacted
        if r.embedded:
            embedded_files += 1

        log.info(
            "[%d/%d] %s chunks=%d redacted=%d embedded=%s%s",
            i, len(files), f.name, r.chunks_inserted, r.secrets_redacted,
            r.embedded, " SKIPPED" if r.skipped else "",
        )

    log.info(
        "done. files=%d chunks_inserted=%d redacted=%d embedded_files=%d failed=%d",
        len(files), total_chunks, total_redacted, embedded_files, len(failed),
    )
    if failed:
        for path, err in failed[:10]:
            log.error("failed: %s — %s", path, err)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
