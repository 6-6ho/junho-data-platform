import asyncpg
from . import config

_pool: asyncpg.Pool | None = None


SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS todo;

-- 공유 칸반 보드: 단일 행(id=1)에 카드 배열을 JSONB 통째로 저장 (팀 3명 공유).
-- rev: 낙관적 동시성 제어용 단조 증가 버전. 저장 시 base_rev 와 비교해 충돌(다른 사람이
--      먼저 저장)을 감지 → 409. 동시 편집 시 조용한 덮어쓰기를 막는다.
CREATE TABLE IF NOT EXISTS todo.board (
    id          INT PRIMARY KEY DEFAULT 1,
    data        JSONB NOT NULL DEFAULT '[]'::jsonb,
    rev         BIGINT NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by  TEXT,
    CONSTRAINT board_singleton CHECK (id = 1)
);
INSERT INTO todo.board (id, data) VALUES (1, '[]'::jsonb) ON CONFLICT (id) DO NOTHING;
-- 기존 보드 행에 rev 컬럼 보강 (이미 있으면 무시).
ALTER TABLE todo.board ADD COLUMN IF NOT EXISTS rev BIGINT NOT NULL DEFAULT 0;
"""


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(config.DSN, min_size=1, max_size=5)
        async with _pool.acquire() as conn:
            await conn.execute(SCHEMA_DDL)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
