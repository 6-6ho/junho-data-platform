-- ================================================
-- Shop DQ (Data Quality) 모니터링 테이블
-- 장애 감지 및 데이터 품질 추적용
-- ================================================

-- 카테고리별 시간당 이벤트 건수 (누락 감지용)
CREATE TABLE IF NOT EXISTS dq_category_hourly (
    hour TIMESTAMPTZ NOT NULL,
    category VARCHAR(50) NOT NULL,
    event_count INT NOT NULL DEFAULT 0,
    purchase_count INT NOT NULL DEFAULT 0,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (hour, category)
);

CREATE INDEX IF NOT EXISTS idx_dq_category_hourly_time 
    ON dq_category_hourly(hour DESC);

-- 결제수단별 시간당 건수 (결제 장애 감지용)
CREATE TABLE IF NOT EXISTS dq_payment_hourly (
    hour TIMESTAMPTZ NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    purchase_count INT NOT NULL DEFAULT 0,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (hour, payment_method)
);

CREATE INDEX IF NOT EXISTS idx_dq_payment_hourly_time 
    ON dq_payment_hourly(hour DESC);

-- DQ 이상 탐지 로그
CREATE TABLE IF NOT EXISTS dq_anomaly_log (
    id SERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    anomaly_type VARCHAR(100) NOT NULL,  -- 'category_missing', 'payment_drop', 'abnormal_price'
    dimension VARCHAR(100) NOT NULL,      -- 어떤 카테고리/결제수단
    expected_value DECIMAL(15,2),
    actual_value DECIMAL(15,2),
    severity VARCHAR(20) NOT NULL,        -- 'warning', 'critical'
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_dq_anomaly_log_type 
    ON dq_anomaly_log(anomaly_type, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_dq_anomaly_log_unresolved 
    ON dq_anomaly_log(resolved, detected_at DESC) WHERE resolved = FALSE;

-- DQ 일별 스코어 (대시보드용)
CREATE TABLE IF NOT EXISTS dq_daily_score (
    date DATE PRIMARY KEY,
    completeness_score INT NOT NULL DEFAULT 100,   -- 데이터 완전성 (100점 만점)
    validity_score INT NOT NULL DEFAULT 100,       -- 데이터 유효성
    timeliness_score INT NOT NULL DEFAULT 100,     -- 데이터 적시성
    total_score INT NOT NULL DEFAULT 100,          -- 종합 점수
    critical_count INT NOT NULL DEFAULT 0,
    warning_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 이상 가격 데이터 격리 테이블
CREATE TABLE IF NOT EXISTS dq_anomaly_raw (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100),
    event_type VARCHAR(50),
    user_id VARCHAR(100),
    product_id VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(15,2),
    total_amount DECIMAL(15,2),
    timestamp TIMESTAMPTZ,
    anomaly_reason VARCHAR(100),  -- 'negative_price', 'zero_price', 'extreme_price'
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_anomaly_raw_time 
    ON dq_anomaly_raw(detected_at DESC);
