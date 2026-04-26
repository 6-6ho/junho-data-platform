"""Quick search smoke test. Runs inside jdp-rag container.

Usage:
    docker exec -e VOYAGE_API_KEY=... jdp-rag python /app/scripts/smoke_search.py
"""
from __future__ import annotations

import sys

from rag_server.retrieve import search

queries = [
    "harness engineering permissions",
    "postgres schema infra init",
    "shop DQ metric completeness",
    "trade movers kafka spark",
    "Claude Code agent team experimental",
]

for q in queries:
    print(f"\n--- query: {q!r} ---")
    rows = search(q, limit=3)
    print(f"  results: {len(rows)}")
    for r in rows:
        title = (r.get("source_title") or "")[:60]
        score = r.get("fusion_score", 0.0)
        preview = (r.get("text") or "")[:120].replace("\n", " ")
        print(f"  [{r['source_kind']}] {title}  score={score:.3f}")
        print(f"    {preview}")

sys.exit(0)
