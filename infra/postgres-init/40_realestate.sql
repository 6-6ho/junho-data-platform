-- Realestate monitor schema — Seongbuk-gu daily new listings.
-- Runs only on fresh Postgres volume init.
-- For existing volumes, realestate-monitor container applies the same DDL at startup.

CREATE SCHEMA IF NOT EXISTS realestate;

CREATE TABLE IF NOT EXISTS realestate.listings (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,                  -- 'zigbang' | 'dabang'
    item_id         TEXT NOT NULL,
    sales_type      TEXT,                           -- '월세'
    service_type    TEXT,                           -- '빌라'
    room_type       TEXT,                           -- '투룸' | '쓰리룸'
    deposit         INT,                            -- 만원
    rent            INT,                            -- 만원
    manage_cost     INT,                            -- 만원
    area_m2         NUMERIC(6,2),                   -- 전용면적
    floor           TEXT,
    all_floors      TEXT,
    title           TEXT,
    description     TEXT,
    address_local   TEXT,                           -- "성북구 정릉동"
    jibun_address   TEXT,
    bjd_code        TEXT,                           -- 법정동코드 (성북구 = 11290*)
    lat             NUMERIC(10,7),
    lng             NUMERIC(10,7),
    image_thumbnail TEXT,
    options         JSONB DEFAULT '[]'::jsonb,
    movein_date     TEXT,
    status          TEXT,                           -- 'open' etc.
    detail_url      TEXT,
    raw             JSONB,                          -- full detail snapshot

    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_updated_at TIMESTAMPTZ,                  -- updatedAt from source

    UNIQUE (source, item_id)
);

CREATE INDEX IF NOT EXISTS listings_first_seen_idx
    ON realestate.listings (first_seen_at DESC);
CREATE INDEX IF NOT EXISTS listings_bjd_idx
    ON realestate.listings (bjd_code);
CREATE INDEX IF NOT EXISTS listings_status_idx
    ON realestate.listings (status);

CREATE TABLE IF NOT EXISTS realestate.scrape_runs (
    id              BIGSERIAL PRIMARY KEY,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    source          TEXT NOT NULL,
    status          TEXT NOT NULL,                  -- 'running' | 'ok' | 'error'
    listed_count    INT,                            -- 리스트 endpoint에서 받은 수
    new_count       INT,                            -- 우리 DB에 처음 들어간 수
    seen_count      INT,                            -- 이미 본 매물 수
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS scrape_runs_started_idx
    ON realestate.scrape_runs (started_at DESC);
