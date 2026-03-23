# Data Lineage

Generator → Kafka → Spark → Storage → Mart 전체 데이터 흐름.

---

## Shop Domain

```
shopping_event.py (Generator, 100 TPS)
  │
  ▼
Kafka [shopping-events]
  │
  ▼
analytics_streaming.py (Spark Structured Streaming)
  │
  ├──▶ PostgreSQL (Serving Layer — append log + DISTINCT ON view)
  │      ├── shop_hourly_sales_log  →  shop_hourly_sales (View)
  │      ├── shop_brand_stats_log   →  shop_brand_stats  (View)
  │      └── shop_funnel_stats_log  →  shop_funnel_stats  (View)
  │
  ├──▶ PostgreSQL (DQ Monitoring)
  │      ├── dq_category_hourly
  │      └── dq_payment_hourly
  │
  └──▶ MinIO / S3  (Data Lake)
         └── s3a://raw/shop_events (Parquet, date/hour partitioned)
                │
                ├──▶ batch_product_affinity.py (Airflow, FP-Growth)
                │      └── mart_product_association (PostgreSQL)
                │
                └──▶ batch_user_rfm.py (Airflow, NTILE scoring)
                       └── mart_user_rfm (PostgreSQL)
                              │
                              └──▶ rfm_alert_dag.py (Airflow)
                                     └── Telegram Alert (Risk > 30% or VIP < 5%)
```

## Trade Domain

```
Binance WebSocket (trade_ingest)
  │
  ▼
Kafka [raw.ticker.usdtm]
  │
  ▼
movers_streaming.py (Spark Structured Streaming, 5m/10m 슬라이딩 윈도우)
  │
  ├──▶ PostgreSQL
  │      ├── movers_latest  (급등락 종목)
  │      └── market_snapshot (시장 스냅샷)
  │
  └──▶ Telegram Alert (급등락 감지 시 자동 발송)
         │
         ▼
[Airflow 배치]
  ├── trade_performance_analysis (09:00 KST) → timeseries + snapshot + TP/SL
  ├── signal_validation (10:00 KST) → 랜덤 재검증
  ├── dynamic_theme (06:00 KST) → 상관 클러스터링
  ├── coin_screener (14:00 KST) → 3거래소 잡코인 분류
  └── trade_performance_mart → 신호×TP/SL 사전집계
```

## Whale Monitor Domain

```
Binance WebSocket (whale-monitor)
  ├── btcusdt@aggTrade ($1M+ 필터) ──→ whale_trade
  └── !forceOrder@arr ──→ liquidation_event
  │
Binance REST (whale-monitor, 폴링)
  ├── /fapi/v1/depth (30초) ──→ orderbook_depth
  ├── /fapi/v1/openInterest (1분) ──→ 메모리 (oi_history)
  ├── /fapi/v1/fundingRate (1분) ──→ 메모리
  ├── /futures/data/globalLongShortAccountRatio (5분) ──→ 메모리
  └── /fapi/v1/ticker/price (10초) ──→ 메모리 (price_history)
  │
에피소드 감지 (10초마다 체크)
  15분 내 ±1% 움직임 → 프로파일 스냅샷 → move_episode
  │
  ├── 아웃컴 추적: 5m/15m/1h/4h/24h 후 가격 기록 (비동기)
  ├── 자동 라벨링: squeeze_reversal, genuine_rally, fakeout 등
  ├── 유사 에피소드 매칭 (프로파일 가중 유사도)
  └── Telegram Alert (에피소드 감지 + 1h 업데이트)
```

## Listing Monitor

```
Upbit API + Bithumb API (1분 폴링)
  │
  └── listing-monitor
        ├── coin_listing (UPSERT)
        ├── listing_event (INSERT)
        └── Telegram Alert (신규 상장 감지)
```

## Investment Agent (MCP + Telegram)

```
Claude Code 대화 (MCP)  ──→ investment-agent
Telegram (journal-bot) ──→ journal-bot
  │
  ├── investment_criteria (투자 기준 CRUD)
  ├── investment_memo (메모 + Voyage AI 임베딩 → pgvector)
  └── agent_query_log (질의 로그)
  │
  └── 시장 데이터 조회 (movers_latest, coin_screener_latest, orderbook_depth 등)
```

---

## Table → Source Mapping

| Table | Writer | Source | Update 주기 |
|-------|--------|-------|:-----------:|
| `movers_latest` | movers_streaming | Kafka → Spark | 10초 |
| `market_snapshot` | movers_streaming | Kafka → Spark | 10초 |
| `trade_performance_timeseries` | trade_performance_analysis | Binance API | Daily |
| `signal_raw_snapshot` | trade_performance_analysis | Binance API | Daily |
| `signal_validation_log` | signal_validation_dag | Binance API | Daily |
| `whale_trade` | whale-monitor | Binance WS aggTrade | 실시간 ($1M+) |
| `orderbook_depth` | whale-monitor | Binance REST | 30초 |
| `liquidation_event` | whale-monitor | Binance WS forceOrder | 실시간 |
| `move_episode` | whale-monitor | 에피소드 감지 | 이벤트 기반 |
| `coin_listing` | listing-monitor | Upbit/Bithumb API | 1분 |
| `listing_event` | listing-monitor | Upbit/Bithumb API | 이벤트 기반 |
| `investment_memo` | journal-bot / MCP / Web | 사용자 입력 | 수동 |
| `investment_criteria` | MCP / Web | 사용자 입력 | 수동 |
| `shop_hourly_sales_log` | analytics_streaming | Kafka → Spark | 1h 윈도우 |
| `shop_funnel_stats_log` | analytics_streaming | Kafka → Spark | 1h 윈도우 |
| `dq_category_hourly` | analytics_streaming | Kafka → Spark | 1h 윈도우 |
| `dq_payment_hourly` | analytics_streaming | Kafka → Spark | 1h 윈도우 |
| `mart_product_association` | batch_product_affinity | MinIO Parquet | Daily |
| `mart_user_rfm` | batch_user_rfm | MinIO Parquet | Daily |
| `mart_trade_optimize_daily` | trade_performance_mart | Iceberg/Postgres | Daily |

## Storage Layers

| Layer | Technology | 용도 |
|-------|-----------|------|
| **Raw** | MinIO `s3a://raw/` | Parquet 원본 이벤트, Iceberg |
| **Serving** | PostgreSQL | 대시보드 / API 조회용 집계 테이블 |
| **Mart** | PostgreSQL | 배치 분석 결과 (RFM, TP/SL, DQ) |
| **Vector** | PostgreSQL + pgvector | 투자 메모 임베딩 벡터 검색 |
