"""Ingestion pipeline.

Modules:
  - common.py          shared upsert + embed helpers
  - secret_scrubber.py regex-based secret redaction
  - claude_jsonl.py    Claude Code session JSONL → turns → chunks
  - markdown.py        .md / .txt → chunks
  - run.py             CLI entrypoint
"""
