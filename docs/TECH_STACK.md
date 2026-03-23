# Technical Stack & Decision Rationale

---

## Core Infrastructure

### Docker Compose
- **선택 이유**: 2노드 환경에서 K8s는 오버엔지니어링. Docker Compose로 laptop/desktop 분리 운영
- **이점**: 리소스 효율, 환경 일관성, 서비스별 독립 빌드/재시작

### Apache Kafka (KRaft)
- **선택 이유**: Zookeeper 제거로 단일 프로세스. 2노드에서 JVM 하나 줄이는 것이 메모리에 유의미 (768M 제한)
- **구성**: 랩탑 Kafka (Trade 토픽) + 데스크톱 Kafka (Shop 토픽) — 도메인별 장애 격리

### PostgreSQL 16 + pgvector
- **선택 이유**: 두 도메인의 Speed/Mart Layer를 단일 DB에서 관리하여 교차 검증(Reconciliation) 가능
- **pgvector**: 투자 인사이트 메모의 벡터 유사도 검색 (Voyage AI voyage-3-lite 512dim)
- **JSONB**: timeseries 데이터 저장 (1~60분 수익률)

---

## Data Processing

### Apache Spark Structured Streaming
- **선택 이유**: 윈도우 집계 + 워터마크 네이티브 지원
- **Trade**: 5m/10m 슬라이딩 윈도우, local[*] 모드 (랩탑)
- **Shop**: 1h 텀블링 윈도우, 6개 병렬 쿼리, Standalone 클러스터 (데스크톱)
- **AQE**: skewJoin, coalescePartitions 활성화

### Apache Airflow (LocalExecutor)
- **선택 이유**: DAG 12개, 동시 태스크 4개 수준. Celery는 오버엔지니어링
- **배치**: Trade 성능 분석, 신호 검증, 테마 클러스터링, 잡코인 스크리너, DQ 스코어링

---

## AI / Agent

### MCP (Model Context Protocol)
- **선택 이유**: Claude Code 대화 중에 DB/투자 데이터에 직접 접근하는 도구 확장
- **구현**: investment-agent MCP 서버 — 투자 기준 CRUD, 메모 벡터 검색, 종목 스크리닝
- **실행**: 로컬 Python 프로세스 (stdio transport)

### Voyage AI (voyage-3-lite)
- **선택 이유**: Anthropic 생태계 임베딩 API. 무료 티어 월 200M 토큰. 512차원
- **용도**: investment_memo 벡터 임베딩 → pgvector cosine 검색

---

## Frontend

### React 19 + Vite
- **선택 이유**: 프론트엔드 3개(Trade, Shop Analytics, Shop Admin)를 동일 스택으로 통일
- **빌드**: Vite로 빠른 HMR + 프로덕션 빌드, nginx 정적 서빙

### Recharts
- **선택 이유**: React 컴포넌트 모델에 맞는 선언적 차트 라이브러리
- **사용**: 에피소드 아웃컴, TP/SL 시뮬레이션, DQ 트렌드, 호가 깊이 등

---

## Backend & Serving

### FastAPI
- **선택 이유**: Async I/O, Pydantic 자동 검증, Swagger 자동 생성
- **구성**: Trade Backend (7+ Router, 20+ 엔드포인트) + Shop Backend

---

## Monitoring

### Binance WebSocket (whale-monitor)
- **websocket-client**: aggTrade($1M+ 필터), forceOrder(청산), 자동 재연결
- **REST 폴링**: 호가 깊이(30초), OI/펀딩비/롱숏비율(1분)
- **에피소드**: 15분 윈도우 ±1% 감지 → 프로파일 스냅샷 → 5m/15m/1h/4h/24h 아웃컴 추적

### Cloudflare Tunnel
- **선택 이유**: 랩탑에서 외부 접근 제공. 9개 서브도메인 라우팅
- **QUIC**: WSL2 UDP 버퍼 7MB 설정 필요 (sysctl)

### Prometheus + Grafana + cAdvisor + node-exporter
- **선택 이유**: 컨테이너/노드 리소스 모니터링. 15초 간격 수집
