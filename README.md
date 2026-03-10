# Junho Data Platform

End-to-end data platform that ingests, processes, and serves real-time and batch analytics across two domains — crypto trading signals and e-commerce analytics.

## What it does

### Trade — 암호화폐 실시간 시그널 탐지

Binance Futures 558개 USDT-M 심볼의 ticker를 WebSocket으로 수집하고, Spark Structured Streaming으로 5분/10분 슬라이딩 윈도우 급등/급락을 감지합니다. 시그널 발생 시 텔레그램으로 실시간 알림을 보내고, 발생 후 5~240분간 수익률 타임시리즈를 추적하여 시그널의 실제 성과를 검증합니다. 시장 중립 상관관계 기반으로 코인을 동적 테마 클러스터로 묶어 섹터 흐름을 파악합니다.

### Shop — 이커머스 분석 플랫폼

이벤트 생성기가 구매/장바구니 이벤트를 Kafka로 발행하면, Spark Streaming이 시간별 매출과 퍼널(View → Cart → Purchase), DQ 메트릭을 실시간 집계하고 MinIO에 Parquet로 아카이빙합니다. Chaos Mode로 카테고리/결제 장애와 이상 가격을 주입하면 DQ 파이프라인이 6개 차원(Completeness, Validity, Timeliness, Consistency, Accuracy, Uniqueness)으로 품질을 측정하고, Airflow DAG가 일일 DQ Score를 산출합니다.

## Architecture

```
┌─────────────────── Data Sources ───────────────────┐
│  Binance WebSocket (558 symbols)                   │
│  Shop Event Generator (purchases, carts, reviews)  │
└──────────────────────┬─────────────────────────────┘
                       ▼
┌─────────────────── Ingestion ──────────────────────┐
│  Kafka (KRaft)                                     │
│  Topics: raw.ticker.usdtm, shopping-events,        │
│          reviews, search-queries, session-events    │
└──────────────────────┬─────────────────────────────┘
                       ▼
┌─────────────────── Processing ─────────────────────┐
│  Spark Structured Streaming                        │
│    - Trade: 5m/10m sliding window, 10s trigger     │
│    - Shop: hourly sales, funnel, DQ metrics        │
│                                                    │
│  Airflow Batch (8 DAGs)                            │
│    - Trade: signal validation, performance, themes │
│    - Shop: DQ scoring, RFM, basket analysis        │
└──────────────────────┬─────────────────────────────┘
                       ▼
┌─────────────────── Storage ────────────────────────┐
│  PostgreSQL 16 — 15 schema files, 20+ tables       │
│  MinIO — Spark checkpoint, intermediate data       │
└──────────────────────┬─────────────────────────────┘
                       ▼
┌─────────────────── Serving ────────────────────────┐
│  FastAPI (Trade API, Shop API)                     │
│  React 19 Dashboards (Trade, Shop, Admin)          │
│  Grafana (인프라 메트릭)                               │
│  Telegram Bot (시그널 알림)                          │
└────────────────────────────────────────────────────┘
```

### 데이터 흐름

| 도메인 | 파이프라인 |
|--------|-----------|
| **Trade** | `Binance WS → Kafka(raw.ticker.usdtm) → Spark Streaming(5m/10m 윈도우) → movers_latest → API → Frontend` |
| **Shop** | `Generator → Kafka(shopping-events) → Spark Streaming → Speed Layer(매출/퍼널/DQ) / MinIO → Airflow DQ 스코어링 → API → Dashboard` |

### 노드 구성

랩탑(상시 가동)과 데스크톱(고사양 처리) 2대로 운영합니다. 데스크톱의 Spark/Airflow/Shop API는 랩탑 Postgres(`${LAPTOP_IP}:5432`)로 연결됩니다.

| 노드 | 역할 | Compose 파일 |
|------|------|-------------|
| **랩탑** | Postgres, Kafka, Trade 파이프라인, Nginx, Grafana, Cloudflare Tunnel | `docker-compose.laptop.yml` |
| **데스크톱** | Kafka, Spark Cluster, Airflow, MinIO, Shop 전체, Prometheus | `docker-compose.desktop.yml` |

## Key Engineering

### Market-Neutral Correlation Clustering

BTC 수익률을 차감한 시장 중립 수익률로 상관행렬을 계산하여 거짓 상관(시장 전체 동조)을 제거합니다. AgglomerativeClustering(distance_threshold=0.35)으로 3~7개 코인 그룹을 형성하고, 클러스터 내 평균 pairwise correlation이 가장 높은 코인을 대장주로 선정합니다.

### Signal Validation Pipeline

시그널 발생 후 실제로 수익이 났는지 검증합니다. Airflow DAG가 매일 시그널을 랜덤 샘플링하여 Binance 1분봉 데이터로 재검증하고, TP/SL 도달률, 최대 수익률, 드로우다운을 분석하여 `signal_validation_log`에 기록합니다.

### Data Quality Monitoring

Chaos Mode가 카테고리/결제 장애와 이상 가격을 주입하면, DQ 파이프라인이 6개 차원(Completeness, Validity, Timeliness, Consistency, Accuracy, Uniqueness)으로 품질을 측정합니다. Airflow DAG가 일일 DQ Score를 산출하여 shop-analytics 대시보드에서 모니터링합니다.

### Sliding Window Streaming

Spark Structured Streaming이 10초 트리거 간격으로 5분/10분 윈도우를 동시 처리합니다. 워터마크 기반으로 late data를 허용하고, 시가총액 기반 3-Tier 분류(High/Mid/Small)로 시그널 임계값을 차등 적용합니다.

## Tech Stack

| 영역 | 기술 |
|------|------|
| **Streaming** | Apache Spark Structured Streaming, Apache Kafka (KRaft) |
| **Batch** | Apache Airflow, Spark (spark-submit via BashOperator) |
| **Storage** | PostgreSQL 16, MinIO (S3-compatible) |
| **Backend** | FastAPI (Python) |
| **Frontend** | React 19, Vite, Tailwind CSS (Trade), Recharts, lightweight-charts |
| **Infra** | Docker Compose, Nginx, Cloudflare Tunnel |
| **Monitoring** | Prometheus, Grafana, cAdvisor, Node Exporter |
| **Alerting** | Telegram Bot (시그널 알림 + 인프라 모니터링) |

## Project Structure

```
junho-data-platform/
├── apps/
│   ├── trade-frontend/      # Trade 대시보드 (React 19 + Vite)
│   ├── trade-backend/       # Trade API (FastAPI)
│   ├── trade-ingest/        # Binance WebSocket → Kafka
│   ├── shop-analytics/      # Shop 대시보드 (React 19 + Vite)
│   ├── shop-backend/        # Shop API (FastAPI)
│   ├── shop-admin/          # Generator 제어 어드민 (React + Vite)
│   ├── shop-generator/      # Shop 이벤트 생성기
│   └── infra-monitor/       # 인프라 모니터링 (Telegram 알림)
├── spark/
│   ├── jobs/trade/          # Trade Spark 잡 (movers, backfill, theme 등)
│   ├── jobs/shop/           # Shop Spark 잡 (analytics streaming)
│   └── common/              # 공통 유틸 (DB connection pool, Spark utils)
├── airflow/dags/            # Airflow DAG 정의 (8개 운영)
├── infra/
│   ├── postgres-init/       # DB 스키마 (01~15 순서 실행)
│   ├── nginx/               # Nginx 설정 + 랜딩 페이지
│   ├── prometheus/          # Prometheus 설정
│   ├── grafana/             # Grafana 프로비저닝
│   └── tunnel/              # Cloudflare Tunnel 설정
├── docs/                    # 아키텍처, 서비스맵 등 문서
├── tests/                   # pytest
├── docker-compose.laptop.yml
├── docker-compose.desktop.yml
└── .env.example
```

## Getting Started

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 값 입력

# 2. 랩탑 노드
docker compose -f docker-compose.laptop.yml up -d

# 3. 데스크톱 노드
export LAPTOP_IP=<랩탑-IP>
./start_desktop.sh
```

| 서비스 | URL |
|--------|-----|
| Trade Dashboard | `http://localhost:3000` |
| Shop Dashboard | `http://localhost:3001` |
| Grafana | `http://localhost:3002` |
| Airflow | `http://localhost:8080` |
| Spark Master UI | `http://localhost:8081` |
| MinIO Console | `http://localhost:9001` |

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 아키텍처
- [TECH_STACK.md](docs/TECH_STACK.md) — 기술 스택 상세
- [DATA_LINEAGE.md](docs/DATA_LINEAGE.md) — 데이터 리니지
- [NETWORK_ARCHITECTURE.md](docs/NETWORK_ARCHITECTURE.md) — 네트워크 구성 및 포트 포워딩
- [SERVICE_MAP.md](docs/SERVICE_MAP.md) — 서비스 포트맵 및 트러블슈팅
- [DISTRIBUTED_PROCESSING.md](docs/DISTRIBUTED_PROCESSING.md) — 분산 처리 설계
- [MINIO_GUIDE.md](docs/MINIO_GUIDE.md) — MinIO 데이터 레이크 설정
- [SHOP_DQ_IMPLEMENTATION.md](docs/SHOP_DQ_IMPLEMENTATION.md) — Shop DQ 구현 상세
- [SHOP_BATCH_DESIGN.md](docs/SHOP_BATCH_DESIGN.md) — Shop 배치 설계
- [METRICS_DEFINITION.md](docs/METRICS_DEFINITION.md) — 메트릭 정의
- [PROJECT_RULES.md](docs/PROJECT_RULES.md) — 프로젝트 규칙

## License

[MIT](LICENSE)
