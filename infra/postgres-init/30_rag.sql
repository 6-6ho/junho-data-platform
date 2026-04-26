-- Personal RAG schema — runs only on fresh Postgres volume init.
-- For existing volumes, the rag-server container idempotently applies
-- the same DDL at startup via rag_server/schema.py.

CREATE SCHEMA IF NOT EXISTS rag;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rag.sources (
    id          BIGSERIAL PRIMARY KEY,
    kind        TEXT NOT NULL,
    origin      TEXT NOT NULL,
    title       TEXT,
    metadata    JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (kind, origin)
);

CREATE TABLE IF NOT EXISTS rag.chunks (
    id          BIGSERIAL PRIMARY KEY,
    source_id   BIGINT NOT NULL REFERENCES rag.sources(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    text        TEXT NOT NULL,
    token_count INT,
    embedding   vector(1024),
    tsv         tsvector GENERATED ALWAYS AS (to_tsvector('simple', text)) STORED,
    metadata    JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_ivfflat
    ON rag.chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS chunks_tsv ON rag.chunks USING GIN (tsv);
CREATE INDEX IF NOT EXISTS chunks_source_id ON rag.chunks (source_id);

CREATE TABLE IF NOT EXISTS rag.oauth_clients (
    client_id                   TEXT PRIMARY KEY,
    client_name                 TEXT NOT NULL,
    client_secret_hash          TEXT,
    redirect_uris               TEXT[] NOT NULL,
    grant_types                 TEXT[] DEFAULT ARRAY['authorization_code', 'refresh_token'],
    token_endpoint_auth_method  TEXT DEFAULT 'none',
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag.oauth_auth_codes (
    code                  TEXT PRIMARY KEY,
    client_id             TEXT NOT NULL REFERENCES rag.oauth_clients(client_id) ON DELETE CASCADE,
    user_sub              TEXT NOT NULL,
    redirect_uri          TEXT NOT NULL,
    code_challenge        TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL,
    scope                 TEXT,
    expires_at            TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS rag.oauth_tokens (
    access_token_hash   TEXT PRIMARY KEY,
    refresh_token_hash  TEXT UNIQUE,
    client_id           TEXT NOT NULL REFERENCES rag.oauth_clients(client_id) ON DELETE CASCADE,
    user_sub            TEXT NOT NULL,
    scope               TEXT,
    expires_at          TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
