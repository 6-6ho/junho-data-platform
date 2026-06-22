"""Personal RAG — FastMCP entrypoint.

Phase 3: FastMCP with PersonalAuthProvider (OAuth 2.1 + PKCE + DCR).
Phase 5: real tools replace `_ping`.

The `mcp` object is the ASGI application. `python -m rag_server.main` starts
the server via `mcp.run(transport="streamable-http")`.
"""
from __future__ import annotations

import logging

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from rag_server.config import settings
from rag_server.mcp_tools import (
    tool_add_note,
    tool_delete_note,
    tool_get_document,
    tool_list_sources,
    tool_search,
)
from rag_server.personal_auth import PersonalAuthProvider
from rag_server.schema import ensure_schema
from rag_server.db import query_one
from starlette.concurrency import run_in_threadpool

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("rag_server")

# --- boot: ensure DB schema before anything else ---
logger.info("rag-server boot, issuer=%s", settings.oauth_issuer)
ensure_schema()

# --- OAuth provider ---
# Security model (Phase 3):
# 1. `allowed_redirect_domains` — only claude.ai / claude.com / localhost can
#    complete the flow. Any other OAuth client is rejected at /authorize.
# 2. Obscure URL — `rag.6-6ho.com` is not published anywhere; the security
#    perimeter is "anyone who knows the URL + has claude.ai".
# 3. `password` — stored in env as RAG_LOGIN_TOKEN. If set, personal_auth
#    uses it as an extra layer (but auto-approves when redirect domain matches).
auth = PersonalAuthProvider(
    base_url=settings.oauth_issuer,
    password=settings.rag_login_token,
    allowed_redirect_domains=["claude.ai", "claude.com", "localhost"],
    state_dir="/data/oauth-state",
)

mcp = FastMCP(
    name="personal-rag",
    instructions=(
        "Personal RAG over Junho's Claude conversations, notes, and project docs. "
        "Use `search` to find past context, `add_note` to save new memories, and "
        "`list_sources` to browse what's stored. Korean or English queries both work."
    ),
    auth=auth,
)


# --- public healthcheck (no OAuth) for docker + tunnel probes ---
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Liveness + readiness. Pings DB so a dropped postgres connection surfaces as
    unhealthy → autoheal restarts the container (fresh connection)."""
    try:
        await run_in_threadpool(query_one, "SELECT 1")
    except Exception as e:  # noqa: BLE001
        logger.warning("health: DB check failed: %s", e)
        return JSONResponse({"status": "db_error", "service": "rag-server"}, status_code=503)
    return JSONResponse({"status": "ok", "service": "rag-server"})


# --- RAG tools (Phase 5) ---
# Each tool is a thin wrapper around rag_server.mcp_tools — the heavy logic
# lives there so the decorator registration here stays easy to scan.

@mcp.tool
def search(query: str, limit: int = 10, source_kind: str | None = None) -> str:
    """Semantic search across Junho's personal knowledge base.

    Use whenever the user asks about their past work, previous conversations,
    notes, or project context — things Claude wouldn't know unless they were
    stored here. Korean or English queries both work.

    Args:
        query: Natural-language search query.
        limit: Max results (1..50, default 10).
        source_kind: Optional filter — one of 'claude_session', 'manual_note',
                     'plan', 'project_doc', 'idea_harness'. None = all.
    """
    return tool_search(query=query, limit=limit, source_kind=source_kind)  # type: ignore[arg-type]


@mcp.tool
def get_document(source_id: int) -> str:
    """Fetch the full source document (all chunks) for a matched source.

    Use AFTER `search` when the user wants surrounding context around a match.
    Don't call speculatively — can return a lot of text for long sessions.
    """
    return tool_get_document(source_id=source_id)


@mcp.tool
def add_note(content: str, tags: list[str] | None = None, title: str | None = None) -> str:
    """Save a manual note to the knowledge base.

    Use when the user says "remember this", "save this", "add to my RAG",
    "이거 기억해둬", or explicitly asks to store info for later retrieval.
    Do NOT use for auto-summaries of the current conversation unless the user
    explicitly asks — Claude session ingestion captures that automatically.
    """
    return tool_add_note(content=content, tags=tags, title=title)


@mcp.tool
def list_sources(source_kind: str | None = None, limit: int = 20) -> str:
    """Browse what's in the knowledge base.

    Use when the user wants an inventory (`what's in my RAG?`, `recent notes?`).
    NOT a substitute for `search` when the user wants specific content.
    """
    return tool_list_sources(source_kind=source_kind, limit=limit)  # type: ignore[arg-type]


@mcp.tool
def delete_note(source_id: int) -> str:
    """Delete a manual note. Only works for `manual_note` sources.

    Other source kinds are re-ingested from files so deletion would be
    pointless — next re-ingest would recreate them.
    """
    return tool_delete_note(source_id=source_id)


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
