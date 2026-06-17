import asyncpg

from . import config

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(config.DSN, min_size=1, max_size=5)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS brief;

CREATE TABLE IF NOT EXISTS brief.daily (
    run_date       DATE PRIMARY KEY,
    geeknews_date  DATE,
    geeknews       JSONB NOT NULL DEFAULT '[]'::jsonb,
    github         JSONB NOT NULL DEFAULT '[]'::jsonb,
    reads          JSONB NOT NULL DEFAULT '[]'::jsonb,
    trends         JSONB NOT NULL DEFAULT '[]'::jsonb,
    producthunt    JSONB NOT NULL DEFAULT '[]'::jsonb,
    naver          JSONB NOT NULL DEFAULT '[]'::jsonb,
    ideas          TEXT,
    status         TEXT,
    error          TEXT,
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- 기존 테이블 보강 (통합으로 컬럼 추가)
ALTER TABLE brief.daily ADD COLUMN IF NOT EXISTS reads       JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE brief.daily ADD COLUMN IF NOT EXISTS trends      JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE brief.daily ADD COLUMN IF NOT EXISTS producthunt JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE brief.daily ADD COLUMN IF NOT EXISTS naver       JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE brief.daily ADD COLUMN IF NOT EXISTS ideas       TEXT;

CREATE INDEX IF NOT EXISTS brief_daily_date_idx ON brief.daily (run_date DESC);
"""


async def init_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_DDL)
