# Task Plan (체크리스트)

## 1) Infra (docker-compose)
- [ ] frontend-nginx (외부 노출 포트 1개)
- [ ] backend-fastapi
- [ ] kafka
- [ ] spark streaming
- [ ] minio
- [ ] postgres

## 2) Ingest (WS -> Kafka)
- [ ] Binance Futures WS 구독(USDT-M Perp 전체)
- [ ] 메시지 정규화(심볼, 가격, 24h change, 24h volume, event_time)
- [ ] `raw.ticker.usdtm` publish

## 3) Spark Streaming Jobs
### 3.1 Movers 계산
- [ ] Rise(5m/2h) 이벤트 생성 -> `movers.events`
- [ ] HighVolUp(15m + vol spike) 이벤트 생성 -> `movers.events`
- [ ] UI 서빙용 최신 Top20 저장
  - [ ] Option A: Postgres `movers_latest` upsert (권장)
  - [ ] Option B: `movers.latest.snapshot` 토픽 운영

### 3.2 Trendline Alert 계산
- [ ] 라인 설정 상태 유지(토픽 or DB pull)
- [ ] close-only crossing 판정 + buffer + cooldown
- [ ] `alerts.events` publish + Postgres `alerts_events` 저장(권장)

## 4) Backend API
- [ ] Movers 최신 조회 API
- [ ] Klines API
- [ ] Trendlines CRUD
- [ ] Alerts feed API

## 5) Frontend
- [ ] /movers: 2컬럼 Top20 + auto refresh
- [ ] /chart: lightweight chart + drawing + line panel + alerts feed

## 6) Demo/Acceptance
- [ ] 외부 접속 포트 1개(`:3000`)만
- [ ] 1시간 이상 연속 실행 안정성
- [ ] 새로고침 후 라인/알럿 설정 유지
