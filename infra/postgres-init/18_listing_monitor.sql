-- 신규 상장 이벤트 로그 (listing-monitor 서비스용)
-- coin_listing은 기존 coin_screener_dag와 공유 (상태 테이블)
-- listing_event는 append-only 이벤트 로그 (프론트엔드 서빙용)

CREATE TABLE IF NOT EXISTS listing_event (
    id SERIAL PRIMARY KEY,
    exchange TEXT NOT NULL,         -- 'upbit' | 'bithumb'
    symbol TEXT NOT NULL,
    market_code TEXT NOT NULL,
    korean_name TEXT,
    english_name TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    notified BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_listing_event_detected
    ON listing_event(detected_at DESC);
