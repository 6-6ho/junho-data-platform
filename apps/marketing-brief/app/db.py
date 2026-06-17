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
CREATE SCHEMA IF NOT EXISTS marketing;

-- 일별 마케팅 브리핑. run_date(KST) 기준 한 행.
--   trends:      오늘 한국 검색 트렌드 (Google Trends KR)
--   producthunt: 오늘 뜨는 프로덕트
--   hackernews:  글로벌 테크 화제
--   ideas:       Gemini 가 위를 엮어 만든 콘텐츠 아이디어 (텍스트)
CREATE TABLE IF NOT EXISTS marketing.daily (
    run_date       DATE PRIMARY KEY,
    trends         JSONB NOT NULL DEFAULT '[]'::jsonb,
    producthunt    JSONB NOT NULL DEFAULT '[]'::jsonb,
    hackernews     JSONB NOT NULL DEFAULT '[]'::jsonb,
    ideas          TEXT,
    status         TEXT,
    error          TEXT,
    generated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS marketing_daily_date_idx ON marketing.daily (run_date DESC);
"""


async def init_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_DDL)
