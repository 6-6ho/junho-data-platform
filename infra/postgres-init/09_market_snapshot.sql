-- Create market_snapshot table for Theme RS calculation
CREATE TABLE IF NOT EXISTS market_snapshot (
    symbol VARCHAR(20) PRIMARY KEY,
    price DOUBLE PRECISION,
    change_pct_24h DOUBLE PRECISION,
    volume_24h DOUBLE PRECISION,
    change_pct_window DOUBLE PRECISION,
    event_time TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for performance (though symbol is primary key)
CREATE INDEX IF NOT EXISTS idx_market_snapshot_updated_at ON market_snapshot(updated_at);
