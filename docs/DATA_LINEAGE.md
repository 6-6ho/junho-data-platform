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
movers_streaming.py (Spark Structured Streaming, 5m sliding window)
  │
  ├──▶ PostgreSQL
  │      ├── movers_latest  (급등락 종목)
  │      └── market_snapshot (시장 스냅샷)
  │
  └──▶ Telegram Alert (급등락 감지 시 자동 발송)
         │
         ▼
trade_performance_analysis.py (Airflow, daily 09:00 KST)
  │  movers_latest에서 새 시그널 수집 → Binance API로 1분봉 60개 조회
  │
  ├──▶ trade_performance_timeseries (JSONB timeseries, 1~60분)
  │      └── TP/SL 최적 전략 분석 → Telegram 리포트
  │
  └──▶ signal_raw_snapshot (원본 캔들 OHLCV 보존)
         │
         ▼
signal_validation_dag.py (Airflow, daily 10:00 KST)
  │  랜덤 10개 샘플 → Binance API로 재검증
  │
  └──▶ signal_validation_log (pass/fail/error)
         └── fail 시 Telegram 알림
```

### Trade Domain — Validation Loop (검증 체계)

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Collection                         │
│  movers_latest → fetch_klines() → timeseries + snapshot     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Daily Validation                        │
│  signal_validation_dag: 랜덤 샘플링 → Binance 재조회       │
│  stored_profit vs recalc_profit → |diff| > 1% = fail       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Historical Replay                       │
│  historical_query.py --date YYYY-MM-DD                      │
│  시그널 + 스냅샷 + 검증로그 + TP/SL 시뮬레이션 재실행      │
└─────────────────────────────────────────────────────────────┘
```

### trade_performance_timeseries — 컬럼 상세

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `symbol` | TEXT | 종목 (e.g., BTCUSDT) |
| `alert_type` | TEXT | 시그널 유형 (rise) |
| `alert_time` | TIMESTAMPTZ | 시그널 발생 시각 |
| `entry_price` | DOUBLE | 진입 시점 close price |
| `timeseries_data` | JSONB | 1~60분 시계열 데이터 |

**timeseries_data JSONB 구조:**
```json
{
  "1":  {"price": 100.5, "profit_pct": 0.12, "is_win": false},
  "2":  {"price": 101.0, "profit_pct": 0.62, "is_win": false},
  ...
  "60": {"price": 103.2, "profit_pct": 2.82, "is_win": true}
}
```

### signal_raw_snapshot — 컬럼 상세

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `symbol` | TEXT | 종목 |
| `alert_time` | TIMESTAMPTZ | 시그널 발생 시각 |
| `entry_price` | DOUBLE | 진입 가격 |
| `klines_1m` | JSONB | 원본 1분봉 OHLCV 데이터 (최대 61개) |

### signal_validation_log — 컬럼 상세

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `symbol` | TEXT | 검증 대상 종목 |
| `alert_time` | TIMESTAMPTZ | 원본 시그널 시각 |
| `stored_profit_pct` | DOUBLE | DB에 저장된 10분 시점 수익률 |
| `recalc_profit_pct` | DOUBLE | Binance에서 재계산한 수익률 |
| `diff_pct` | DOUBLE | 오차 절대값 |
| `status` | TEXT | pass / fail / error |

---

## Table → Source Mapping

| Table | Writer | Source | Update 주기 |
|-------|--------|-------|:-----------:|
| `shop_hourly_sales_log` | analytics_streaming | Kafka → Spark | Real-time (10m window) |
| `shop_brand_stats_log` | analytics_streaming | Kafka → Spark | Real-time (10m window) |
| `shop_funnel_stats_log` | analytics_streaming | Kafka → Spark | Real-time (10m window) |
| `dq_category_hourly` | analytics_streaming | Kafka → Spark | Real-time (1h window) |
| `dq_payment_hourly` | analytics_streaming | Kafka → Spark | Real-time (1h window) |
| `mart_product_association` | batch_product_affinity | MinIO Parquet | Daily (Airflow 03:00 UTC) |
| `mart_user_rfm` | batch_user_rfm | MinIO Parquet | Daily (Airflow 03:30 UTC) |
| `movers_latest` | movers_streaming | Kafka → Spark | Real-time (5m window) |
| `market_snapshot` | movers_streaming | Kafka → Spark | Real-time (5m window) |
| `trade_performance_timeseries` | trade_performance_analysis | Binance API | Daily (Airflow 00:00 UTC) |
| `signal_raw_snapshot` | trade_performance_analysis | Binance API | Daily (Airflow 00:00 UTC) |
| `signal_validation_log` | signal_validation_dag | Binance API | Daily (Airflow 01:00 UTC) |

## Storage Layers

| Layer | Technology | 용도 |
|-------|-----------|------|
| **Raw** | MinIO `s3a://raw/` | Parquet 원본 이벤트 (Iceberg optional) |
| **Serving** | PostgreSQL | 대시보드 / API 조회용 집계 테이블 |
| **Mart** | PostgreSQL | 배치 분석 결과 (RFM, Association Rules) |
