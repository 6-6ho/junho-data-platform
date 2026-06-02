import asyncpg
from . import config

_pool: asyncpg.Pool | None = None


SCHEMA_DDL = """
CREATE SCHEMA IF NOT EXISTS todo;

CREATE TABLE IF NOT EXISTS todo.tasks (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    category    TEXT,
    status      TEXT NOT NULL DEFAULT 'todo',
    priority    TEXT,
    due_date    DATE,
    memo        TEXT,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    done_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS tasks_status_idx ON todo.tasks (status, sort_order);
CREATE INDEX IF NOT EXISTS tasks_cat_idx    ON todo.tasks (category);
CREATE INDEX IF NOT EXISTS tasks_due_idx     ON todo.tasks (due_date);

-- 공유 칸반 보드: 단일 행(id=1)에 카드 배열을 JSONB 통째로 저장 (친구 3명 공유, last-write-wins).
CREATE TABLE IF NOT EXISTS todo.board (
    id          INT PRIMARY KEY DEFAULT 1,
    data        JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by  TEXT,
    CONSTRAINT board_singleton CHECK (id = 1)
);
INSERT INTO todo.board (id, data) VALUES (1, '[]'::jsonb) ON CONFLICT (id) DO NOTHING;
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
