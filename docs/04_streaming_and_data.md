# Streaming & Data Design

## Kafka Topics
- `raw.ticker.usdtm` : 원천 가격/거래량 스트림
- `movers.events` : Top Movers 이벤트 로그
- `movers.latest.snapshot` : UI 서빙용 최신 스냅샷(옵션, 또는 DB upsert로 대체)
- `alerts.config` : 라인 설정 upsert/delete
- `alerts.events` : 알럿 이벤트 로그

## Movers Logic (공식 조건)
### 1) Rise
- window: `5m`, `2h`
- thresholds:
  - Small: 3% ≤ r < 7%
  - Mid: 7% ≤ r < 11%
  - High: r ≥ 11%

### 2) Price up with High Vol (HighVolUp)
- window: `15m`
- price thresholds:
  - Small: 7% ≤ r < 11%
  - Mid: 11% ≤ r < 15%
  - High: r ≥ 15%
- volume condition:
  - `vol_15m >= avg_vol_15m_prev_24h * 50`
  - `avg_vol_15m_prev_24h` = rolling mean of 96 buckets (15m * 96 = 24h)
- 업데이트 주기 목표: 10초

## Alert Engine (v1)
- 기준: close-only
- 트리거: crossing 이벤트
  - up-cross: prev_close <= prev_line_price*(1+buffer) AND curr_close > curr_line_price*(1+buffer)
  - down-cross: prev_close >= prev_line_price*(1-buffer) AND curr_close < curr_line_price*(1-buffer)
- 중복 방지: cooldown per (symbol, line_id, direction)

## Storage
### MinIO(S3) + Parquet
- raw
  - `raw/ticker/dt=YYYY-MM-DD/..`
- curated
  - `curated/movers_events/dt=...`
  - `curated/alerts_events/dt=...`

### Postgres (권장)
- `trendlines` (라인 설정)
- `movers_latest` (UI용 최신 이벤트)
- `alerts_events` (알럿 피드/조회)
