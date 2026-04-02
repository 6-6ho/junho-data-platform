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

-- =============================================
-- Trade DQ (Data Quality) Tables
-- Shop DQ와 완전 독립. 암호화폐 거래소 데이터 품질 관리.
-- =============================================

-- 심볼별 시간 집계 — Completeness 기반
CREATE TABLE IF NOT EXISTS dq_trade_symbol_hourly (
    hour TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    tick_count INT NOT NULL DEFAULT 0,
    avg_price DECIMAL(20,8) NOT NULL DEFAULT 0,
    volume DECIMAL(20,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (hour, symbol)
);
CREATE INDEX IF NOT EXISTS idx_dq_trade_symbol_hourly_time ON dq_trade_symbol_hourly(hour DESC);

-- 소스별 시간 집계 — 교차검증 기반
CREATE TABLE IF NOT EXISTS dq_trade_source_hourly (
    hour TIMESTAMPTZ NOT NULL,
    source VARCHAR(20) NOT NULL,
    event_count INT NOT NULL DEFAULT 0,
    symbol_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (hour, source)
);
CREATE INDEX IF NOT EXISTS idx_dq_trade_source_hourly_time ON dq_trade_source_hourly(hour DESC);

-- 이상 틱 격리
CREATE TABLE IF NOT EXISTS dq_trade_anomaly_raw (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    price DECIMAL(20,8),
    volume DECIMAL(20,2),
    change_pct DECIMAL(10,4),
    anomaly_reason VARCHAR(50) NOT NULL,
    raw_data JSONB,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dq_trade_anomaly_raw_time ON dq_trade_anomaly_raw(detected_at DESC);

-- 이상 탐지 로그 (Shop dq_anomaly_log와 완전 독립)
CREATE TABLE IF NOT EXISTS dq_trade_anomaly_log (
    id SERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anomaly_type VARCHAR(100) NOT NULL,
    dimension VARCHAR(100) NOT NULL,
    expected_value DECIMAL(20,4),
    actual_value DECIMAL(20,4),
    severity VARCHAR(20) NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_dq_trade_anomaly_log_type ON dq_trade_anomaly_log(anomaly_type, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_trade_anomaly_log_unresolved ON dq_trade_anomaly_log(resolved, detected_at DESC) WHERE resolved = FALSE;

-- 일별 DQ 스코어
CREATE TABLE IF NOT EXISTS dq_trade_daily_score (
    date DATE PRIMARY KEY,
    completeness_score INT NOT NULL DEFAULT 100,
    validity_score INT NOT NULL DEFAULT 100,
    timeliness_score INT NOT NULL DEFAULT 100,
    total_score INT NOT NULL DEFAULT 100,
    critical_count INT NOT NULL DEFAULT 0,
    warning_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
