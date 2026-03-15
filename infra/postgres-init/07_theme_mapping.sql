-- Theme master table
CREATE TABLE IF NOT EXISTS theme_master (
    theme_id SERIAL PRIMARY KEY,
    theme_name TEXT UNIQUE NOT NULL,
    exclude_from_rs BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Coin-theme mapping (many-to-many)
CREATE TABLE IF NOT EXISTS coin_theme_mapping (
    symbol TEXT NOT NULL,
    theme_id INTEGER REFERENCES theme_master(theme_id) ON DELETE CASCADE,
    name_kr TEXT,
    listed_period TEXT,
    note TEXT,
    PRIMARY KEY (symbol, theme_id)
);

CREATE INDEX IF NOT EXISTS idx_coin_theme_symbol ON coin_theme_mapping(symbol);
CREATE INDEX IF NOT EXISTS idx_coin_theme_theme ON coin_theme_mapping(theme_id);

-- Theme RS snapshots (time-series)
CREATE TABLE IF NOT EXISTS theme_rs_snapshot (
    snapshot_time TIMESTAMPTZ NOT NULL,
    theme_id INTEGER REFERENCES theme_master(theme_id) ON DELETE CASCADE,
    avg_change_pct DOUBLE PRECISION,
    market_avg_pct DOUBLE PRECISION,
    rs_score DOUBLE PRECISION,
    coin_count INTEGER,
    top_coin TEXT,
    top_coin_pct DOUBLE PRECISION,
    PRIMARY KEY (snapshot_time, theme_id)
);

CREATE INDEX IF NOT EXISTS idx_theme_rs_theme_time
  ON theme_rs_snapshot(theme_id, snapshot_time DESC);
