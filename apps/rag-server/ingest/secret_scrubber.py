"""Regex-based secret redaction.

Runs before chunking during ingestion — past Claude conversations and local
docs occasionally echo API keys that were visible in the conversation context.
Anything that matches a known secret shape gets replaced with `[REDACTED]`
so the RAG can't resurface it later.

Patterns are conservative: favor false positives (a harmless hex string gets
redacted) over false negatives (a real key leaks into the index).
"""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("voyage", re.compile(r"pa-[A-Za-z0-9_\-]{20,}")),
    ("anthropic", re.compile(r"sk-ant-(?:api\d+|admin\d+)-[A-Za-z0-9_\-]{20,}")),
    ("openai", re.compile(r"sk-proj-[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9_\-]{32,}")),
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}")),
    ("slack_bot", re.compile(r"xoxb-[0-9A-Za-z\-]{20,}")),
    ("slack_app", re.compile(r"xapp-[0-9A-Za-z\-]{20,}")),
    ("aws_access", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("aws_secret", re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9/+]{40}(?![A-Za-z0-9])")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")),
    ("hex_token", re.compile(r"\b[a-f0-9]{40,}\b")),  # generic long hex
]

# Env-like lines: KEY=value where KEY contains password/secret/token/key
_ENV_LINE = re.compile(
    r"(?mi)^([A-Z][A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL)[A-Z0-9_]*)\s*[=:]\s*['\"]?([^\s'\"]+)"
)


def scrub(text: str) -> tuple[str, int]:
    """Return (redacted_text, num_hits). Safe to call on any string, incl. empty."""
    if not text:
        return text, 0
    hits = 0

    def _mask(m: re.Match[str]) -> str:
        nonlocal hits
        hits += 1
        return "[REDACTED]"

    out = text
    for _, pat in _PATTERNS:
        out = pat.sub(_mask, out)

    def _mask_env(m: re.Match[str]) -> str:
        nonlocal hits
        # keep the key name, redact the value only
        hits += 1
        return f"{m.group(1)}=[REDACTED]"

    out = _ENV_LINE.sub(_mask_env, out)
    return out, hits
