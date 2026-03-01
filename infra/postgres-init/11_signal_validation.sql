-- Signal Validation & Raw Snapshot tables
-- Task 1: Automated sample validation log
-- Task 2: Raw kline snapshot for traceability

CREATE TABLE IF NOT EXISTS signal_validation_log (
    id SERIAL PRIMARY KEY,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    alert_time TIMESTAMPTZ NOT NULL,
    stored_profit_pct DOUBLE PRECISION,
    recalc_profit_pct DOUBLE PRECISION,
    diff_pct DOUBLE PRECISION,
    status TEXT NOT NULL,  -- 'pass' | 'fail' | 'error'
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_validation_time ON signal_validation_log(validated_at);
CREATE INDEX IF NOT EXISTS idx_validation_status ON signal_validation_log(status);

CREATE TABLE IF NOT EXISTS signal_raw_snapshot (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    alert_time TIMESTAMPTZ NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    klines_1m JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, alert_time)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_time ON signal_raw_snapshot(alert_time);
CREATE INDEX IF NOT EXISTS idx_snapshot_symbol ON signal_raw_snapshot(symbol);
