"""Idempotent schema bootstrap.

Runs at container startup. Uses `CREATE ... IF NOT EXISTS` everywhere so it's
safe to re-run on every boot. The canonical DDL is also duplicated in
infra/postgres-init/90_rag.sql for the initial docker-compose bring-up — but
pg init scripts only run once per volume, so we need this runtime path for
existing Postgres volumes.
"""
from __future__ import annotations

import logging

from rag_server.config import settings
from rag_server.db import execute

logger = logging.getLogger(__name__)


_DDL = [
    # 1. Schema + pgvector extension (extension is already installed on jdp-postgres)
    "CREATE SCHEMA IF NOT EXISTS rag",
    "CREATE EXTENSION IF NOT EXISTS vector",
    # 2. Sources table — one row per ingestable unit (a JSONL session, a markdown file, a manual note, ...)
    """
    CREATE TABLE IF NOT EXISTS rag.sources (
        id          BIGSERIAL PRIMARY KEY,
        kind        TEXT NOT NULL,
        origin      TEXT NOT NULL,
        title       TEXT,
        metadata    JSONB DEFAULT '{}'::jsonb,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        updated_at  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (kind, origin)
    )
    """,
    # 3. Chunks — the searchable unit. Has embedding + tsvector for hybrid retrieval.
    f"""
    CREATE TABLE IF NOT EXISTS rag.chunks (
        id          BIGSERIAL PRIMARY KEY,
        source_id   BIGINT NOT NULL REFERENCES rag.sources(id) ON DELETE CASCADE,
        chunk_index INT NOT NULL,
        text        TEXT NOT NULL,
        token_count INT,
        embedding   vector({settings.voyage_dim}),
        tsv         tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED,
        metadata    JSONB DEFAULT '{{}}'::jsonb,
        created_at  TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE (source_id, chunk_index)
    )
    """,
    # 4. Indexes — ivfflat for vector cosine, GIN for tsv, btree for source_id lookups
    "CREATE INDEX IF NOT EXISTS chunks_embedding_ivfflat ON rag.chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)",
    "CREATE INDEX IF NOT EXISTS chunks_tsv ON rag.chunks USING GIN (tsv)",
    "CREATE INDEX IF NOT EXISTS chunks_source_id ON rag.chunks (source_id)",
    # 5. OAuth clients — populated by Dynamic Client Registration in Phase 3
    """
    CREATE TABLE IF NOT EXISTS rag.oauth_clients (
        client_id                   TEXT PRIMARY KEY,
        client_name                 TEXT NOT NULL,
        client_secret_hash          TEXT,
        redirect_uris               TEXT[] NOT NULL,
        grant_types                 TEXT[] DEFAULT ARRAY['authorization_code', 'refresh_token'],
        token_endpoint_auth_method  TEXT DEFAULT 'none',
        created_at                  TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # 6. OAuth authorization codes — short-lived, consumed once
    """
    CREATE TABLE IF NOT EXISTS rag.oauth_auth_codes (
        code                  TEXT PRIMARY KEY,
        client_id             TEXT NOT NULL REFERENCES rag.oauth_clients(client_id) ON DELETE CASCADE,
        user_sub              TEXT NOT NULL,
        redirect_uri          TEXT NOT NULL,
        code_challenge        TEXT NOT NULL,
        code_challenge_method TEXT NOT NULL,
        scope                 TEXT,
        expires_at            TIMESTAMPTZ NOT NULL
    )
    """,
    # 7. Access + refresh tokens — stored as hashes so leaking the table doesn't grant access
    """
    CREATE TABLE IF NOT EXISTS rag.oauth_tokens (
        access_token_hash   TEXT PRIMARY KEY,
        refresh_token_hash  TEXT UNIQUE,
        client_id           TEXT NOT NULL REFERENCES rag.oauth_clients(client_id) ON DELETE CASCADE,
        user_sub            TEXT NOT NULL,
        scope               TEXT,
        expires_at          TIMESTAMPTZ NOT NULL,
        created_at          TIMESTAMPTZ DEFAULT NOW()
    )
    """,
]


def ensure_schema() -> None:
    """Apply DDL idempotently. Raises on error so startup fails loud."""
    logger.info("ensuring rag schema")
    for stmt in _DDL:
        execute(stmt)
    logger.info("rag schema ready")
