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
