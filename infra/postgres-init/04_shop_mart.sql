-- ================================================
-- Shop Data Mart (Gold Layer) 테이블
-- Batch 처리로 생성되는 분석용 테이블
-- ================================================

-- ================================================
-- DAILY AGGREGATIONS
-- ================================================

-- 일별 매출 요약 (카테고리별)
CREATE TABLE IF NOT EXISTS mart_daily_sales (
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    order_count INT NOT NULL DEFAULT 0,
    avg_order_value DECIMAL(10,2),
    unique_users INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (date, category)
);

CREATE INDEX IF NOT EXISTS idx_mart_daily_sales_date 
    ON mart_daily_sales(date DESC);

-- 일별 Funnel 분석
CREATE TABLE IF NOT EXISTS mart_daily_funnel (
    date DATE PRIMARY KEY,
    total_sessions INT NOT NULL DEFAULT 0,
    view_count INT NOT NULL DEFAULT 0,
    cart_count INT NOT NULL DEFAULT 0,
    purchase_count INT NOT NULL DEFAULT 0,
    view_rate DECIMAL(5,2),      -- view / sessions * 100
    cart_rate DECIMAL(5,2),      -- cart / view * 100
    purchase_rate DECIMAL(5,2),  -- purchase / cart * 100
    overall_conversion DECIMAL(5,2),  -- purchase / sessions * 100
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 일별 전체 요약 (대시보드용)
CREATE TABLE IF NOT EXISTS mart_daily_summary (
    date DATE PRIMARY KEY,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_orders INT NOT NULL DEFAULT 0,
    total_users INT NOT NULL DEFAULT 0,
    avg_order_value DECIMAL(10,2),
    top_category VARCHAR(50),
    dod_revenue_change DECIMAL(5,2),  -- Day over Day 변화율
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================================================
-- WEEKLY AGGREGATIONS
-- ================================================

-- 주별 매출 요약
CREATE TABLE IF NOT EXISTS mart_weekly_sales (
    week_start DATE NOT NULL,  -- 해당 주의 월요일
    week_number INT NOT NULL,  -- ISO 주차
    year INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    order_count INT NOT NULL DEFAULT 0,
    avg_daily_revenue DECIMAL(15,2),
    wow_change DECIMAL(5,2),  -- Week over Week 변화율
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (week_start, category)
);

-- 주별 전체 요약
CREATE TABLE IF NOT EXISTS mart_weekly_summary (
    week_start DATE PRIMARY KEY,
    week_number INT NOT NULL,
    year INT NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_orders INT NOT NULL DEFAULT 0,
    avg_daily_revenue DECIMAL(15,2),
    best_day VARCHAR(20),  -- 가장 매출 높은 요일
    wow_revenue_change DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================================================
-- MONTHLY AGGREGATIONS
-- ================================================

-- 월별 매출 요약
CREATE TABLE IF NOT EXISTS mart_monthly_sales (
    month_start DATE NOT NULL,  -- 해당 월의 1일
    year INT NOT NULL,
    month INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    order_count INT NOT NULL DEFAULT 0,
    avg_daily_revenue DECIMAL(15,2),
    mom_change DECIMAL(5,2),  -- Month over Month 변화율
    yoy_change DECIMAL(5,2),  -- Year over Year 변화율
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (month_start, category)
);

-- 월별 전체 요약
CREATE TABLE IF NOT EXISTS mart_monthly_summary (
    month_start DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_orders INT NOT NULL DEFAULT 0,
    total_users INT NOT NULL DEFAULT 0,
    avg_order_value DECIMAL(10,2),
    top_category VARCHAR(50),
    mom_revenue_change DECIMAL(5,2),
    yoy_revenue_change DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ================================================
-- COHORT ANALYSIS (사용자 분석)
-- ================================================

-- 사용자 코호트 (첫 구매 월 기준)
CREATE TABLE IF NOT EXISTS mart_user_cohort (
    first_purchase_month DATE NOT NULL,
    months_since_first INT NOT NULL,
    user_count INT NOT NULL DEFAULT 0,
    total_revenue DECIMAL(15,2) NOT NULL DEFAULT 0,
    avg_revenue_per_user DECIMAL(10,2),
    retention_rate DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (first_purchase_month, months_since_first)
);

-- ================================================
-- EXPORT HISTORY (감사 추적)
-- ================================================

-- 데이터 Export 이력
CREATE TABLE IF NOT EXISTS mart_export_history (
    id SERIAL PRIMARY KEY,
    export_type VARCHAR(50) NOT NULL,  -- 'daily', 'weekly', 'minio', 'market'
    export_date DATE NOT NULL,
    record_count INT NOT NULL,
    file_path TEXT,  -- MinIO 저장 경로
    status VARCHAR(20) NOT NULL,  -- 'success', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_export_history_type_date 
    ON mart_export_history(export_type, export_date DESC);

-- ================================================
-- PRODUCT AFFINITY (장바구니 연관성)
-- ================================================

-- 연관 규칙 (Association Rules)
CREATE TABLE IF NOT EXISTS mart_product_association (
    antecedents TEXT NOT NULL,  -- 선행 상품 (JSON array string)
    consequents TEXT NOT NULL,  -- 후행 상품 (JSON array string)
    confidence DECIMAL(5,4),    -- 신뢰도 (조건부 확률)
    lift DECIMAL(5,2),          -- 향상도 (우연 대비 확률)
    support DECIMAL(5,4),       -- 지지도 (동시 발생 확률)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mart_product_assoc_lift 
    ON mart_product_association(lift DESC);

-- ================================================
-- USER RFM SEGMENTATION (고객 세그먼트)
-- ================================================

-- RFM 점수 및 등급
CREATE TABLE IF NOT EXISTS mart_user_rfm (
    user_id VARCHAR(100) PRIMARY KEY,
    recency INT NOT NULL,       -- 최근 구매 경과일
    frequency INT NOT NULL,     -- 구매 횟수
    monetary DECIMAL(15,2) NOT NULL, -- 총 구매액
    r_score INT NOT NULL,       -- 1~5점
    f_score INT NOT NULL,
    m_score INT NOT NULL,
    rfm_segment VARCHAR(50),    -- VIP, Loyal, Hibernating etc.
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mart_user_rfm_segment 
    ON mart_user_rfm(rfm_segment);
