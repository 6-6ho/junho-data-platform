-- BTC 온체인 메트릭 (mempool.space 기반)
CREATE TABLE IF NOT EXISTS onchain_btc_metrics (
    id SERIAL PRIMARY KEY,
    block_height INT,
    mempool_tx_count INT,
    mempool_vsize BIGINT,
    mempool_total_fee DECIMAL(20,8),
    fee_fastest INT,
    fee_half_hour INT,
    fee_hour INT,
    fee_economy INT,
    difficulty_progress DECIMAL(10,4),
    difficulty_remaining_blocks INT,
    difficulty_estimated_retarget DECIMAL(10,4),
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_onchain_btc_time ON onchain_btc_metrics(collected_at DESC);

-- BTC 온체인 시간 집계 (DQ 드리프트 연동용)
CREATE TABLE IF NOT EXISTS onchain_btc_hourly (
    hour TIMESTAMPTZ PRIMARY KEY,
    avg_mempool_tx INT,
    avg_mempool_vsize BIGINT,
    avg_fee_fastest INT,
    avg_fee_economy INT,
    block_count INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_onchain_btc_hourly_time ON onchain_btc_hourly(hour DESC);
