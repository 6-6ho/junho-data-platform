# Junho Data Platform

2-Node 하이브리드 데이터 플랫폼. **Trade**(암호화폐 실시간 시그널 탐지)와 **Shop**(이커머스 분석) 두 도메인을 데스크톱 + 랩탑 인프라에서 운영합니다.

## 아키텍처

```
┌─────────────────────────────────────┐     ┌──────────────────────────────────────────┐
│          Laptop (항상 켜짐)           │     │           Desktop (고사양 처리)             │
│                                     │     │                                          │
│  Binance WS → Kafka → Spark Local   │     │  Kafka → Spark Cluster (Master + 2 Worker)│
│       → movers_latest (Postgres)    │     │       → Shop Streaming → Postgres (Laptop)│
│                                     │     │                                          │
│  Postgres (5432) ◄─────────────────────── Spark / Airflow / Shop API                │
│  Nginx (3000)    → Trade Frontend   │     │  Airflow → Spark Batch → Mart Tables     │
│  Grafana (3002)                     │     │  MinIO (Object Storage)                  │
│  Cloudflare Tunnel                  │     │  Shop Frontend (3001) / Admin (3003)     │
│  Prometheus                         │     │  Prometheus Exporters                    │
└─────────────────────────────────────┘     └──────────────────────────────────────────┘
```

### 데이터 흐름

| 도메인 | 파이프라인 |
|--------|-----------|
| **Trade** | `Binance WS → Kafka(raw.ticker.usdtm) → Spark Streaming(5m/10m 윈도우) → movers_latest → API → Frontend` |
| **Shop** | `Generator → Kafka(shopping-events) → Spark Streaming → Speed Layer / MinIO → Airflow 배치 → Mart Layer → API → Dashboard` |

## 기술 스택

| 영역 | 기술 |
|------|------|
| **Streaming** | Apache Spark Structured Streaming, Apache Kafka (KRaft) |
| **Batch** | Apache Airflow, Spark (spark-submit via BashOperator) |
| **Storage** | PostgreSQL 16, MinIO (S3-compatible) |
| **Backend** | FastAPI (Python) |
| **Frontend** | React 19, Vite, Tailwind CSS, Recharts |
| **Infra** | Docker Compose, Nginx, Cloudflare Tunnel |
| **Monitoring** | Prometheus, Grafana, cAdvisor, Node Exporter |
| **Alerting** | Telegram Bot (시그널 알림 + 인프라 모니터링) |

## 주요 기능

### Trade — 암호화폐 실시간 모니터링
- **Movers 감지**: 5분/10분 슬라이딩 윈도우로 급등/급락 종목 실시간 탐지
- **3-Tier 분류**: High / Mid / Small 시가총액 기반 티어링
- **퍼포먼스 추적**: 시그널 발생 후 5~240분 타임시리즈 수익률 분석
- **테마 분류**: Relative Strength 기반 섹터/테마 동적 분류
- **텔레그램 알림**: 설정 기준 초과 시 실시간 알림

### Shop — 이커머스 분석 플랫폼
- **실시간 대시보드**: 시간별 매출, 퍼널(View → Cart → Purchase), 카테고리별 트래픽
- **Data Quality 모니터링**: 6 Dimensions(Completeness, Validity, Timeliness, Consistency 등) 기반 DQ 스코어링
- **배치 마트**: 일별/주별/월별 매출, RFM 세분화, 상품 연관분석, 코호트 분석
- **Chaos 모드**: 카테고리/결제 장애 + 이상가격 시뮬레이션 (DQ 테스트용)
- **Admin 대시보드**: Generator 제어 (TPS, 모드, Chaos ON/OFF)

## Quick Start

### 1. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값 입력
```

### 2. 랩탑 노드 시작

```bash
docker compose -f docker-compose.laptop.yml up -d
```

### 3. 데스크톱 노드 시작

```bash
export LAPTOP_IP=<랩탑-IP>
./start_desktop.sh
```

### 접속

| 서비스 | URL |
|--------|-----|
| Trade Dashboard | `http://localhost:3000` |
| Shop Dashboard | `http://localhost:3001` |
| Grafana | `http://localhost:3002` |
| Airflow | `http://localhost:8080` |
| Spark Master UI | `http://localhost:8081` |
| MinIO Console | `http://localhost:9001` |

## 프로젝트 구조

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
├── airflow/dags/            # Airflow DAG 정의
├── infra/
│   ├── postgres-init/       # DB 스키마 (01~12 순서 실행)
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

## 노드 구성

| 노드 | 역할 | Compose 파일 |
|------|------|-------------|
| **랩탑** (항상 켜짐) | Postgres, Kafka, Trade 파이프라인, Nginx, Grafana, Tunnel | `docker-compose.laptop.yml` |
| **데스크톱** (고사양) | Kafka, Spark Cluster, Airflow, MinIO, Shop 전체, Monitoring | `docker-compose.desktop.yml` |

데스크톱의 Spark/Airflow/Shop API는 랩탑 Postgres(`${LAPTOP_IP}:5432`)로 연결됩니다.

## 문서

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — 시스템 아키텍처
- [NETWORK_ARCHITECTURE.md](docs/NETWORK_ARCHITECTURE.md) — 네트워크 구성 및 포트 포워딩
- [SERVICE_MAP.md](docs/SERVICE_MAP.md) — 서비스 포트맵 및 트러블슈팅
- [MINIO_GUIDE.md](docs/MINIO_GUIDE.md) — MinIO 데이터 레이크 설정

## License

[MIT](LICENSE)
