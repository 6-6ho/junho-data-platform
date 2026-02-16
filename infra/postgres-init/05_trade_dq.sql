CREATE TABLE IF NOT EXISTS mart_trade_stats (
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    total_volume DOUBLE PRECISION,
    trade_count BIGINT,
    symbol_count INT,
    batch_processed_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (window_start, window_end)
);

CREATE INDEX IF NOT EXISTS idx_trade_stats_time ON mart_trade_stats(window_start);
