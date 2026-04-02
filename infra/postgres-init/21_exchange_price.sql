-- 멀티 거래소 가격 스냅샷 — 교차검증 기반
CREATE TABLE IF NOT EXISTS exchange_price_snapshot (
    exchange VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price_krw DECIMAL(20,2),
    price_usd DECIMAL(20,8),
    volume_24h DECIMAL(20,2),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (exchange, symbol)
);

CREATE INDEX IF NOT EXISTS idx_exchange_price_updated ON exchange_price_snapshot(updated_at DESC);

-- 거래소 간 가격 비교 시간 집계
CREATE TABLE IF NOT EXISTS dq_cross_exchange_hourly (
    hour TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    binance_price DECIMAL(20,8),
    upbit_price_krw DECIMAL(20,2),
    bithumb_price_krw DECIMAL(20,2),
    divergence_pct DECIMAL(10,4),
    PRIMARY KEY (hour, symbol)
);

CREATE INDEX IF NOT EXISTS idx_dq_cross_exchange_time ON dq_cross_exchange_hourly(hour DESC);
