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

-- 일별 모닝 브리핑. run_date(KST 오늘) 기준 한 행.
--   geeknews: 어제자 GeekNews Top N (요약 포함) JSONB 배열
--   github:   오늘자 GitHub Trending(Python) Top N JSONB 배열
CREATE TABLE IF NOT EXISTS brief.daily (
    run_date       DATE PRIMARY KEY,
    geeknews_date  DATE,
    geeknews       JSONB NOT NULL DEFAULT '[]'::jsonb,
    github         JSONB NOT NULL DEFAULT '[]'::jsonb,
    status         TEXT,
    error          TEXT,
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS brief_daily_date_idx ON brief.daily (run_date DESC);
"""


async def init_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_DDL)
