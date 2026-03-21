-- Investment Agent: 투자 기준 + 인사이트 메모 + 질의 로그
-- pgvector 확장 필요 (pgvector/pgvector:pg16 이미지 사용)

CREATE EXTENSION IF NOT EXISTS vector;

-- 투자 기준
CREATE TABLE IF NOT EXISTS investment_criteria (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인사이트 메모
CREATE TABLE IF NOT EXISTS investment_memo (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'mcp',
    tags TEXT[],
    embedding vector(1024),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 질의 로그
CREATE TABLE IF NOT EXISTS agent_query_log (
    id BIGSERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_type TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'mcp',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_memo_embedding
    ON investment_memo USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
CREATE INDEX IF NOT EXISTS idx_memo_created ON investment_memo(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_criteria_category ON investment_criteria(category);
CREATE INDEX IF NOT EXISTS idx_agent_query_log_created ON agent_query_log(created_at DESC);
