-- 17: Coin Screener — 잡코인 스크리너 (업비트/빗썸 × 바이낸스 교집합)

-- A: 거래소별 코인 상장 정보
CREATE TABLE IF NOT EXISTS coin_listing (
    exchange TEXT NOT NULL,            -- 'upbit' | 'bithumb'
    symbol TEXT NOT NULL,              -- 'BTC', 'ETH'
    market_code TEXT NOT NULL,         -- 'KRW-BTC' (업비트) | 'BTC_KRW' (빗썸)
    korean_name TEXT,
    english_name TEXT,
    first_seen_date DATE,              -- 최초 발견일 ≈ 상장일 추정
    is_active BOOLEAN DEFAULT TRUE,
    on_binance BOOLEAN DEFAULT FALSE,  -- 바이낸스 상장 여부
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (exchange, symbol)
);

-- B: 일별 스크리닝 결과
CREATE TABLE IF NOT EXISTS coin_screener_daily (
    date DATE NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price_krw DOUBLE PRECISION,
    market_cap_krw BIGINT,
    volume_24h_krw BIGINT,
    weekly_down_count SMALLINT,       -- 최근 12주 중 음봉 수
    listing_age_days INT,
    max_price_since_listing DOUBLE PRECISION,
    listing_price DOUBLE PRECISION,
    is_low_cap BOOLEAN DEFAULT FALSE,
    is_long_decline BOOLEAN DEFAULT FALSE,
    is_no_pump BOOLEAN DEFAULT FALSE,
    had_pump_20pct_30d BOOLEAN DEFAULT FALSE,  -- 최근 30일 일봉 20%+ 상승 여부
    junk_score SMALLINT DEFAULT 0,    -- 0~3
    PRIMARY KEY (date, exchange, symbol)
);
ALTER TABLE coin_screener_daily ADD COLUMN IF NOT EXISTS had_pump_20pct_30d BOOLEAN DEFAULT FALSE;

-- C: 최신 스크리닝 결과 (서빙용)
CREATE TABLE IF NOT EXISTS coin_screener_latest (
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price_krw DOUBLE PRECISION,
    market_cap_krw BIGINT,
    volume_24h_krw BIGINT,
    weekly_down_count SMALLINT,
    listing_age_days INT,
    max_price_since_listing DOUBLE PRECISION,
    listing_price DOUBLE PRECISION,
    is_low_cap BOOLEAN DEFAULT FALSE,
    is_long_decline BOOLEAN DEFAULT FALSE,
    is_no_pump BOOLEAN DEFAULT FALSE,
    had_pump_20pct_30d BOOLEAN DEFAULT FALSE,
    junk_score SMALLINT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (exchange, symbol)
);
ALTER TABLE coin_screener_latest ADD COLUMN IF NOT EXISTS had_pump_20pct_30d BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_screener_latest_junk
    ON coin_screener_latest(junk_score DESC, exchange);
