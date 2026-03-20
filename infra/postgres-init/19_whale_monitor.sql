-- Whale Monitor: 에피소드 축적형 가격 움직임 분석
-- 원시 데이터 + 에피소드 테이블

-- === 원시 데이터 테이블 ===

CREATE TABLE IF NOT EXISTS orderbook_depth (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    mid_price NUMERIC NOT NULL,
    bid_depth_1pct NUMERIC,
    ask_depth_1pct NUMERIC,
    bid_depth_5pct NUMERIC,
    ask_depth_5pct NUMERIC,
    depth_imbalance NUMERIC,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS whale_trade (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price NUMERIC NOT NULL,
    quantity NUMERIC NOT NULL,
    notional_usd NUMERIC NOT NULL,
    trade_time TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS liquidation_event (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    price NUMERIC NOT NULL,
    quantity NUMERIC NOT NULL,
    notional_usd NUMERIC NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS whale_transfer (
    id BIGSERIAL PRIMARY KEY,
    chain TEXT NOT NULL,
    tx_hash TEXT,
    amount NUMERIC NOT NULL,
    amount_usd NUMERIC,
    from_label TEXT,
    to_label TEXT,
    direction TEXT NOT NULL,
    block_time TIMESTAMPTZ,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- === 핵심: 에피소드 테이블 ===

CREATE TABLE IF NOT EXISTS move_episode (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,

    -- 감지 시점
    detected_at TIMESTAMPTZ NOT NULL,
    trigger_price NUMERIC NOT NULL,
    price_change_pct NUMERIC NOT NULL,
    direction TEXT NOT NULL,

    -- 프로파일 (감지 시점 시장 상태)
    oi_change_pct NUMERIC,
    short_liq_count INT DEFAULT 0,
    short_liq_usd NUMERIC DEFAULT 0,
    long_liq_count INT DEFAULT 0,
    long_liq_usd NUMERIC DEFAULT 0,
    depth_imbalance NUMERIC,
    bid_depth_1pct NUMERIC,
    ask_depth_1pct NUMERIC,
    funding_rate NUMERIC,
    funding_rate_delta NUMERIC,
    whale_net_buy_usd NUMERIC,
    ls_ratio NUMERIC,
    volume_surge_ratio NUMERIC,

    -- 아웃컴 (비동기 기록, 처음엔 NULL)
    return_5m NUMERIC,
    return_15m NUMERIC,
    return_1h NUMERIC,
    return_4h NUMERIC,
    return_24h NUMERIC,
    max_return NUMERIC,
    max_drawdown NUMERIC,

    -- 라벨 (아웃컴 완료 후 자동 분류)
    label TEXT,

    -- 메타
    profile_json JSONB,
    similar_episodes JSONB
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_orderbook_depth_time ON orderbook_depth(symbol, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_whale_trade_time ON whale_trade(symbol, trade_time DESC);
CREATE INDEX IF NOT EXISTS idx_liquidation_time ON liquidation_event(symbol, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_whale_transfer_time ON whale_transfer(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_move_episode_time ON move_episode(symbol, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_move_episode_label ON move_episode(label) WHERE label IS NOT NULL;
