# Service & Port Map

## 공개 엔드포인트 (Cloudflare Tunnel)

| Service | Hostname | 설명 |
|---------|----------|------|
| Landing Page | `6-6ho.com` / `www.6-6ho.com` | 포트폴리오 랜딩 |
| Trade App | `trade.6-6ho.com` | 코인 트레이딩 대시보드 |
| Shop Analytics | `shop.6-6ho.com` / `analytics.6-6ho.com` | 쇼핑몰 분석 대시보드 |
| Shop Admin | `admin.6-6ho.com` | Generator 제어 |
| Grafana | `monitor.6-6ho.com` | 시스템 모니터링 |
| Airflow | `airflow.6-6ho.com` | 배치 워크플로우 |
| Web Terminal | `code.6-6ho.com` | ttyd 웹 터미널 |

## 랩탑 서비스 (docker-compose.laptop.yml)

| Service | Port | CPU/Mem | 설명 |
|---------|------|---------|------|
| kafka | 9092 | 0.5/768M | 메시지 브로커 (KRaft) |
| ingest | - | 0.3/256M | Binance WS → Kafka |
| trade-movers | - | 1.0/1G | Spark local, 5m/10m 윈도우 |
| api (trade-backend) | 8000 | 1.0/512M | Trade FastAPI |
| frontend (nginx) | 3000 | 0.5/256M | React SPA + API 프록시 |
| postgres | 5432 | 1.0/1G | PostgreSQL + pgvector |
| whale-monitor | - | 0.3/256M | BTC 에피소드 분석 (WS + 폴링) |
| listing-monitor | - | 0.1/64M | 업비트/빗썸 상장 감지 |
| journal-bot | - | 0.1/64M | 텔레그램 저널 봇 |
| infra-monitor | - | 0.1/64M | 컨테이너 장애 알림 |
| grafana | 3002 | 0.5/256M | Grafana |
| prometheus | 9090 | - | 메트릭 수집 |
| node-exporter | 9100 | - | 노드 메트릭 |
| cadvisor | 8080 | - | 컨테이너 메트릭 |
| cloudflared | - | - | Cloudflare Tunnel |

## 데스크톱 서비스 (docker-compose.desktop.yml)

| Service | Port | CPU/Mem | 설명 |
|---------|------|---------|------|
| kafka | 9092 | 1.0/768M | Shop 토픽 브로커 |
| spark-master | 7077/8081 | 0.5/512M | Spark 마스터 |
| spark-worker-1 | - | 3.0/4G | Spark 워커 |
| spark-worker-2 | - | 3.0/4G | Spark 워커 |
| airflow | 8080 | 1.0/1.5G | 배치 오케스트레이션 |
| minio | 9000/9001 | 0.5/512M | 오브젝트 스토리지 |
| shop-api | 8000 | 0.5/256M | Shop FastAPI |
| shop-analytics | 3001 | 0.5/256M | Shop 대시보드 |
| shop-admin | 3003 | 0.5/256M | Generator 제어 UI |
| shop-generator | - | - | 이벤트 생성기 |
| shop-analytics-job | - | 1.0/2G | Shop Spark Streaming |

## 로컬 프로세스 (Docker 외)

| Service | 방식 | 설명 |
|---------|------|------|
| investment-agent | MCP (stdio) | Claude Code에서 투자 기준/메모/스크리닝 도구 제공 |

## Trade API 엔드포인트

| Router | 주요 엔드포인트 |
|--------|----------------|
| Data | `GET /api/movers/latest` |
| Analysis | `GET /api/analysis/oi/{symbol}`, `market-overview`, `exchange-rate` |
| Klines | `GET /api/klines` |
| SMC | `GET /api/smc/analysis/{symbol}` |
| Theme | `GET /api/theme/rs`, `dynamic` |
| System | `GET /api/system/performance/optimize`, `time-based`, `profit-targets` |
| Screener | `GET /api/screener/overview`, `coins` |
| Listing | `GET /api/listing/recent`, `stats` |
| Whale | `GET /api/whale/dashboard`, `episodes`, `episodes/active`, `stats` |
| Agent | `GET /api/agent/stats`, `criteria`, `memos/recent` (공개), `POST /api/agent/memo`, `memo/search`, `screen` (인증) |

## Troubleshooting

### 1. Cloudflare Tunnel QUIC 타임아웃
- **증상**: Bad Gateway (502/530)
- **원인**: WSL2 UDP 버퍼 208KB 제한
- **해결**: `sudo sysctl -w net.core.rmem_max=7340032 net.core.wmem_max=7340032` + `/etc/sysctl.conf`에 영구 설정

### 2. Spark Job Fail (OOM)
- **증상**: 스트리밍 잡이 137 코드로 종료
- **해결**: docker-compose에서 Spark 워커 메모리 상향

### 3. Airflow DAG 백필 폭주
- **증상**: catchup=True + start_date가 너무 오래됨 → 수백 개 DAG run 생성
- **해결**: start_date를 실제 데이터 시작일로 맞추기
