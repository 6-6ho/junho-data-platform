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
CREATE SCHEMA IF NOT EXISTS realestate;

CREATE TABLE IF NOT EXISTS realestate.listings (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    item_id         TEXT NOT NULL,
    sales_type      TEXT,
    service_type    TEXT,
    room_type       TEXT,
    deposit         INT,
    rent            INT,
    manage_cost     INT,
    area_m2         NUMERIC(6,2),
    floor           TEXT,
    all_floors      TEXT,
    title           TEXT,
    description     TEXT,
    address_local   TEXT,
    jibun_address   TEXT,
    bjd_code        TEXT,
    lat             NUMERIC(10,7),
    lng             NUMERIC(10,7),
    image_thumbnail TEXT,
    options         JSONB DEFAULT '[]'::jsonb,
    movein_date     TEXT,
    status          TEXT,
    detail_url      TEXT,
    raw             JSONB,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_updated_at TIMESTAMPTZ,
    UNIQUE (source, item_id)
);

CREATE INDEX IF NOT EXISTS listings_first_seen_idx ON realestate.listings (first_seen_at DESC);
CREATE INDEX IF NOT EXISTS listings_bjd_idx ON realestate.listings (bjd_code);
CREATE INDEX IF NOT EXISTS listings_status_idx ON realestate.listings (status);

CREATE TABLE IF NOT EXISTS realestate.scrape_runs (
    id              BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    source          TEXT NOT NULL,
    status          TEXT NOT NULL,
    listed_count    INT,
    new_count       INT,
    seen_count      INT,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS scrape_runs_started_idx ON realestate.scrape_runs (started_at DESC);
"""


async def init_schema() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_DDL)
