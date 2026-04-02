// === 서비스 정의 ===
const SERVICES = [
  // Trade (Laptop)
  { id: 'binance-ws', name: 'Binance WebSocket', node: 'external', domain: 'trade', type: 'source', desc: 'USDT-M Futures 전종목 실시간 ticker' },
  { id: 'trade-ingest', name: 'Trade Ingest', node: 'laptop', domain: 'trade', type: 'ingestion', desc: 'WebSocket → Kafka 브릿지. 정규화 6필드 추출.', cpu: '0.3', mem: '256M' },
  { id: 'kafka-laptop', name: 'Kafka (Laptop)', node: 'laptop', domain: 'infra', type: 'messaging', desc: 'KRaft 모드. Trade 토픽 (raw.ticker.usdtm)', cpu: '0.5', mem: '768M' },
  { id: 'trade-movers', name: 'Trade Movers', node: 'laptop', domain: 'trade', type: 'streaming', desc: 'Spark local[*]. 5m/10m 슬라이딩 윈도우 급등/급락 감지.', cpu: '1.0', mem: '1G' },
  { id: 'whale-monitor', name: 'Whale Monitor', node: 'laptop', domain: 'trade', type: 'streaming', desc: 'BTC 에피소드 축적형 분석. aggTrade($1M+), forceOrder, 호가/OI/펀딩비.', cpu: '0.3', mem: '256M' },
  { id: 'listing-monitor', name: 'Listing Monitor', node: 'laptop', domain: 'trade', type: 'polling', desc: '업비트/빗썸 신규 상장 1분 폴링 → 텔레그램 알림.', cpu: '0.1', mem: '64M' },
  { id: 'trade-backend', name: 'Trade Backend', node: 'laptop', domain: 'trade', type: 'serving', desc: 'FastAPI. 11 Router, 30+ 엔드포인트.', cpu: '1.0', mem: '512M' },
  { id: 'trade-frontend', name: 'Trade Frontend', node: 'laptop', domain: 'trade', type: 'serving', desc: 'React 19 + Vite + nginx. 6개 페이지 + Agent.', cpu: '0.5', mem: '256M' },
  { id: 'postgres', name: 'PostgreSQL + pgvector', node: 'laptop', domain: 'infra', type: 'storage', desc: '단일 DB. Trade + Shop + Agent 테이블. 벡터 검색.', cpu: '1.0', mem: '1G' },
  { id: 'journal-bot', name: 'Journal Bot', node: 'laptop', domain: 'agent', type: 'bot', desc: '텔레그램 저널 봇. Voyage AI 임베딩 → pgvector.', cpu: '0.1', mem: '64M' },
  { id: 'investment-agent', name: 'Investment Agent', node: 'local', domain: 'agent', type: 'agent', desc: 'MCP 서버. 투자 기준 CRUD, 메모 벡터 검색, 종목 스크리닝.' },
  { id: 'grafana', name: 'Grafana', node: 'laptop', domain: 'infra', type: 'monitoring', desc: '4개 대시보드. 컨테이너/노드/파이프라인/Trade 모니터링.', cpu: '0.5', mem: '256M' },
  { id: 'cloudflared', name: 'Cloudflare Tunnel', node: 'laptop', domain: 'infra', type: 'network', desc: '9개 서브도메인 → 내부 서비스 라우팅. QUIC.' },
  // Shop (Desktop)
  { id: 'kafka-desktop', name: 'Kafka (Desktop)', node: 'desktop', domain: 'infra', type: 'messaging', desc: 'KRaft 모드. Shop 토픽 5개.', cpu: '1.0', mem: '768M' },
  { id: 'shop-generator', name: 'Shop Generator', node: 'laptop', domain: 'shop', type: 'source', desc: '3 persona × 5 category 이벤트 생성. TPS 10~2000. Chaos Mode.', cpu: '0.2', mem: '256M' },
  { id: 'analytics-streaming', name: 'Shop Streaming', node: 'laptop', domain: 'shop', type: 'streaming', desc: 'Spark local. 6개 병렬 쿼리. 매출/퍼널/DQ 1h 윈도우 집계.', cpu: '0.5', mem: '1G' },
  { id: 'spark-cluster', name: 'Spark Cluster', node: 'desktop', domain: 'infra', type: 'compute', desc: 'Master + Worker×2 (7cores/7GB). Standalone.', cpu: '6.5', mem: '8.5G' },
  { id: 'airflow', name: 'Airflow', node: 'desktop', domain: 'infra', type: 'orchestrator', desc: 'LocalExecutor. 12 DAG. parallelism=4.', cpu: '1.0', mem: '1.5G' },
  { id: 'minio', name: 'MinIO', node: 'desktop', domain: 'infra', type: 'storage', desc: 'S3 호환. raw/checkpoints/iceberg-warehouse.', cpu: '0.5', mem: '512M' },
  { id: 'shop-backend', name: 'Shop Backend', node: 'laptop', domain: 'shop', type: 'serving', desc: 'FastAPI. Analytics + DQ + Mart API. 20+ 엔드포인트.', cpu: '0.3', mem: '256M' },
  { id: 'shop-frontend', name: 'Shop Analytics', node: 'laptop', domain: 'shop', type: 'serving', desc: 'React 19. Overview + DQ + Mart 대시보드. DoD/WoW 비교, 퍼널 전환율.', cpu: '0.2', mem: '128M' },
];

// === Kafka 토픽 ===
const TOPICS = [
  { id: 'topic-ticker', name: 'raw.ticker.usdtm', domain: 'trade', broker: 'laptop', desc: 'Binance USDT-M 전종목 ticker' },
  { id: 'topic-shopping', name: 'shopping-events', domain: 'shop', broker: 'desktop', desc: '구매/장바구니/조회 이벤트' },
  { id: 'topic-reviews', name: 'reviews', domain: 'shop', broker: 'desktop', desc: '리뷰 이벤트' },
  { id: 'topic-search', name: 'search-queries', domain: 'shop', broker: 'desktop', desc: '검색 이벤트' },
  { id: 'topic-session', name: 'session-events', domain: 'shop', broker: 'desktop', desc: '세션 이벤트' },
  { id: 'topic-control', name: 'generator-control', domain: 'shop', broker: 'desktop', desc: 'Admin → Generator 제어' },
];

// === DAG 정의 ===
const DAGS = [
  {
    id: 'trade_performance_analysis', name: 'Trade Performance Analysis',
    schedule: '0 0 * * *', scheduleKr: '매일 09:00 KST', catchup: true, tags: ['trade', 'analysis'],
    desc: '전날 급등 신호를 Binance 1분 봉으로 후속 추적. 1~60분 수익률 JSONB 저장 + TP/SL 24조합 시뮬레이션.',
    reads: ['movers_latest', 'Binance API'], writes: ['trade_performance_timeseries', 'signal_raw_snapshot'],
  },
  {
    id: 'trade_performance_mart', name: 'Trade Performance Mart',
    schedule: '30 0 * * *', scheduleKr: '매일 09:30 KST', catchup: true, tags: ['trade', 'mart', 'spark'],
    desc: '신호 × TP/SL 24조합 승률·PnL을 Tier별 사전 집계. optimize API 응답 84배 개선.',
    reads: ['Iceberg', 'signal_validation_log'], writes: ['mart_trade_signal_detail', 'mart_trade_strategy_result', 'mart_trade_time_performance', 'mart_trade_optimize_daily'],
  },
  {
    id: 'signal_validation', name: 'Signal Validation',
    schedule: '0 1 * * *', scheduleKr: '매일 10:00 KST', catchup: true, tags: ['trade', 'dq'],
    desc: '7일 내 신호 10개 랜덤 샘플링 → Binance API 재검증 (±1% 오차).',
    reads: ['trade_performance_timeseries', 'Binance API'], writes: ['signal_validation_log'],
  },
  {
    id: 'dynamic_theme', name: 'Dynamic Theme Discovery',
    schedule: '0 21 * * *', scheduleKr: '매일 06:00 KST', catchup: true, tags: ['trade', 'analysis'],
    desc: 'BTC 수익률 차감 후 Pearson 상관 → Agglomerative Clustering (14일 평균, 거리≤0.35).',
    reads: ['market_snapshot', 'Binance API'], writes: ['daily_correlation', 'dynamic_theme_cluster', 'dynamic_theme_member'],
  },
  {
    id: 'coin_screener', name: 'Coin Screener',
    schedule: '0 5 * * *', scheduleKr: '매일 14:00 KST', catchup: true, tags: ['trade', 'screener'],
    desc: '업비트/빗썸/바이낸스 교집합 301종목 4가지 위험신호 자동 분류. junk_score 0~3.',
    reads: ['Upbit/Bithumb/CoinGecko API', 'coin_listing'], writes: ['coin_listing', 'coin_screener_daily', 'coin_screener_latest'],
  },
  {
    id: 'theme_rs_calculator', name: 'Theme RS Calculator',
    schedule: '*/10 * * * *', scheduleKr: '10분마다', catchup: false, tags: ['trade'],
    desc: 'market_snapshot 기반 테마별 RS Score 계산.',
    reads: ['coin_theme_mapping', 'market_snapshot'], writes: ['theme_rs_snapshot'],
  },
  {
    id: 'trade_lake', name: 'Trade Historical Lake',
    schedule: '0 7 * * *', scheduleKr: '매일 16:00 KST', catchup: false, tags: ['trade', 'lake', 'iceberg'],
    desc: 'Postgres 서빙 테이블 → Iceberg 히스토리컬 아카이브. market_history/movers_history/dq_history.',
    reads: ['market_snapshot', 'movers_latest', 'dq_trade_symbol_hourly'], writes: ['MinIO Iceberg'],
  },
  {
    id: 'trade_dq_scoring', name: 'Trade DQ Scoring',
    schedule: '0 6 * * *', scheduleKr: '매일 15:00 KST', catchup: false, tags: ['trade', 'dq'],
    desc: 'Trade 3차원 DQ 스코어링(C/V/T) + 심볼 드롭 탐지 + 소스 교차검증.',
    reads: ['dq_trade_symbol_hourly', 'dq_trade_source_hourly', 'dq_trade_anomaly_raw', 'market_snapshot'], writes: ['dq_trade_daily_score', 'dq_trade_anomaly_log'],
  },
  {
    id: 'shop_mart', name: 'Shop Mart Build',
    schedule: '0 6 * * *', scheduleKr: '매일 15:00 KST', catchup: false, tags: ['shop', 'mart'],
    desc: 'shop_hourly_sales_log → 일별/주별 마트 빌드. DoD/WoW 비교 데이터 생성.',
    reads: ['shop_hourly_sales_log'], writes: ['mart_daily_sales', 'mart_daily_summary', 'mart_weekly_sales'],
  },
  {
    id: 'basket_analysis', name: 'Basket Analysis (FP-Growth)',
    schedule: '0 3 * * *', scheduleKr: '매일 12:00 KST', catchup: false, tags: ['shop', 'analysis'],
    desc: 'FP-Growth 연관규칙. minSupport=0.001, minConfidence=0.05, lift>1.0.',
    reads: ['MinIO raw/shop_events'], writes: ['mart_product_association'],
  },
  {
    id: 'user_rfm', name: 'User RFM Segmentation',
    schedule: '30 3 * * *', scheduleKr: '매일 12:30 KST', catchup: false, tags: ['shop', 'analysis'],
    desc: 'R/F/M NTILE(5) → 5 세그먼트 (VIP/Loyal/Risk/New/Regular).',
    reads: ['MinIO raw/shop_events'], writes: ['mart_user_rfm'],
  },
  {
    id: 'rfm_alert', name: 'RFM Alert',
    schedule: '0 4 * * *', scheduleKr: '매일 13:00 KST', catchup: false, tags: ['shop'],
    desc: 'Risk>30% or VIP<5% → Telegram 알림.',
    reads: ['mart_user_rfm'], writes: ['Telegram'],
  },
  {
    id: 'dq_scoring', name: 'DQ Scoring',
    schedule: '0 5 * * *', scheduleKr: '매일 14:00 KST', catchup: false, tags: ['shop', 'dq'],
    desc: 'Completeness(40%) + Validity(30%) + Timeliness(30%). 7일 평균 대비 이상 탐지.',
    reads: ['dq_category_hourly', 'dq_payment_hourly', 'dq_anomaly_raw'], writes: ['dq_daily_score', 'dq_anomaly_log'],
  },
  {
    id: 'product_expansion', name: 'Product Expansion',
    schedule: '0 4 * * *', scheduleKr: '매일 13:00 KST', catchup: false, tags: ['shop'],
    desc: '(stub) 상품 카탈로그 확장.',
    reads: [], writes: [],
  },
  {
    id: 'benchmark', name: 'Benchmark',
    schedule: 'manual', scheduleKr: '수동 트리거', catchup: false, tags: ['infra'],
    desc: 'Single vs Multi-executor 성능 비교. 5.3M rows, 47~83% 개선.',
    reads: ['MinIO'], writes: ['spark_benchmark_results'],
  },
];

// === 테이블 정의 ===
const TABLES = [
  // Trade Serving
  { id: 'movers_latest', name: 'movers_latest', domain: 'trade', layer: 'serving', pk: '(type, symbol, status, event_time)', writer: 'trade-movers', readers: ['trade-backend', 'trade_performance_analysis'], freq: '10초', desc: '실시간 급등/급락 신호' },
  { id: 'market_snapshot', name: 'market_snapshot', domain: 'trade', layer: 'serving', pk: 'symbol', writer: 'trade-movers', readers: ['trade-backend', 'dynamic_theme', 'theme_rs_calculator'], freq: '10초', desc: '전 심볼 최신 가격' },
  { id: 'trade_perf_ts', name: 'trade_performance_timeseries', domain: 'trade', layer: 'serving', pk: 'id (SERIAL)', writer: 'trade_performance_analysis', readers: ['trade-backend', 'signal_validation'], freq: '매일', desc: '1~60분 수익률 JSONB 시계열' },
  { id: 'signal_raw', name: 'signal_raw_snapshot', domain: 'trade', layer: 'serving', pk: 'UNIQUE(symbol, alert_time)', writer: 'trade_performance_analysis', readers: ['trade-backend'], freq: '매일', desc: '원본 1분 봉 OHLCV 보존' },
  { id: 'signal_val', name: 'signal_validation_log', domain: 'trade', layer: 'dq', pk: 'id (SERIAL)', writer: 'signal_validation', readers: ['trade_performance_mart'], freq: '매일', desc: '신호 재검증 (pass/fail/error)' },
  // Trade Theme
  { id: 'daily_corr', name: 'daily_correlation', domain: 'trade', layer: 'serving', pk: '(date, symbol_a, symbol_b)', writer: 'dynamic_theme', readers: ['dynamic_theme'], freq: '매일', desc: '일일 Pearson 상관계수' },
  { id: 'dyn_cluster', name: 'dynamic_theme_cluster', domain: 'trade', layer: 'serving', pk: 'cluster_id', writer: 'dynamic_theme', readers: ['trade-backend'], freq: '매일', desc: '동적 테마 클러스터' },
  { id: 'theme_rs', name: 'theme_rs_snapshot', domain: 'trade', layer: 'serving', pk: '(snapshot_time, theme_id)', writer: 'theme_rs_calculator', readers: ['trade-backend'], freq: '10분', desc: '테마 상대강도' },
  // Trade Screener
  { id: 'coin_listing', name: 'coin_listing', domain: 'trade', layer: 'serving', pk: '(exchange, symbol)', writer: 'listing-monitor', readers: ['coin_screener', 'trade-backend'], freq: '1분', desc: '업비트/빗썸 상장 종목' },
  { id: 'listing_event', name: 'listing_event', domain: 'trade', layer: 'serving', pk: 'id (SERIAL)', writer: 'listing-monitor', readers: ['trade-backend'], freq: '이벤트', desc: '신규 상장 감지 이벤트' },
  { id: 'screener_latest', name: 'coin_screener_latest', domain: 'trade', layer: 'serving', pk: '(exchange, symbol)', writer: 'coin_screener', readers: ['trade-backend', 'investment-agent'], freq: '매일', desc: '스크리너 서빙 최신값' },
  // Whale Monitor
  { id: 'whale_trade', name: 'whale_trade', domain: 'trade', layer: 'serving', pk: 'id (BIGSERIAL)', writer: 'whale-monitor', readers: ['trade-backend'], freq: '실시간 ($1M+)', desc: '고래 대형 체결' },
  { id: 'orderbook', name: 'orderbook_depth', domain: 'trade', layer: 'serving', pk: 'id (BIGSERIAL)', writer: 'whale-monitor', readers: ['trade-backend'], freq: '30초', desc: '호가 깊이 + 불균형' },
  { id: 'liquidation', name: 'liquidation_event', domain: 'trade', layer: 'serving', pk: 'id (BIGSERIAL)', writer: 'whale-monitor', readers: ['trade-backend'], freq: '실시간', desc: 'BTC 청산 이벤트' },
  { id: 'move_episode', name: 'move_episode', domain: 'trade', layer: 'serving', pk: 'id (SERIAL)', writer: 'whale-monitor', readers: ['trade-backend'], freq: '이벤트 (15분 ±1%)', desc: '가격 에피소드 (프로파일+아웃컴+라벨)' },
  // Trade Mart
  { id: 'mart_optimize', name: 'mart_trade_optimize_daily', domain: 'trade', layer: 'mart', pk: '(date, tier, tp, sl)', writer: 'trade_performance_mart', readers: ['trade-backend'], freq: '매일', desc: 'TP/SL 전략 사전집계 (84배 개선)' },
  { id: 'mart_signal', name: 'mart_trade_signal_detail', domain: 'trade', layer: 'mart', pk: '(signal_date, symbol, alert_time)', writer: 'trade_performance_mart', readers: ['trade-backend'], freq: '매일', desc: '신호별 최대 수익/손실' },
  { id: 'mart_strategy', name: 'mart_trade_strategy_result', domain: 'trade', layer: 'mart', pk: '(signal_date, symbol, alert_time, tp, sl)', writer: 'trade_performance_mart', readers: ['trade-backend'], freq: '매일', desc: '신호×TP/SL 조합 결과' },
  // Agent
  { id: 'inv_criteria', name: 'investment_criteria', domain: 'agent', layer: 'serving', pk: 'id, name UNIQUE', writer: 'investment-agent', readers: ['trade-backend', 'journal-bot'], freq: '수동', desc: '투자 기준 CRUD' },
  { id: 'inv_memo', name: 'investment_memo', domain: 'agent', layer: 'vector', pk: 'id (BIGSERIAL)', writer: 'journal-bot', readers: ['trade-backend', 'investment-agent'], freq: '수동', desc: '인사이트 메모 + vector(512)' },
  // Shop Speed
  { id: 'shop_sales', name: 'shop_hourly_sales_log', domain: 'shop', layer: 'serving', pk: 'id (SERIAL)', writer: 'analytics-streaming', readers: ['shop-backend'], freq: '1h 윈도우', desc: '카테고리별 시간 매출' },
  { id: 'shop_funnel', name: 'shop_funnel_stats_log', domain: 'shop', layer: 'serving', pk: 'id (SERIAL)', writer: 'analytics-streaming', readers: ['shop-backend'], freq: '1h 윈도우', desc: '퍼널 (view→cart→purchase)' },
  // Shop DQ
  { id: 'dq_cat', name: 'dq_category_hourly', domain: 'shop', layer: 'dq', pk: '(hour, category)', writer: 'analytics-streaming', readers: ['dq_scoring'], freq: '1h', desc: '카테고리별 DQ 집계' },
  { id: 'dq_pay', name: 'dq_payment_hourly', domain: 'shop', layer: 'dq', pk: '(hour, payment_method)', writer: 'analytics-streaming', readers: ['dq_scoring'], freq: '1h', desc: '결제수단별 DQ 집계' },
  { id: 'dq_anomaly', name: 'dq_anomaly_raw', domain: 'shop', layer: 'dq', pk: 'id (SERIAL)', writer: 'analytics-streaming', readers: ['dq_scoring'], freq: '실시간', desc: '이상 가격 격리 (≤0 or ≥50M)' },
  { id: 'dq_score', name: 'dq_daily_score', domain: 'shop', layer: 'dq', pk: 'date', writer: 'dq_scoring', readers: ['shop-backend'], freq: '매일', desc: 'C(40%)+V(30%)+T(30%) 종합 점수' },
  // Shop Mart
  { id: 'mart_rfm', name: 'mart_user_rfm', domain: 'shop', layer: 'mart', pk: 'user_id', writer: 'user_rfm', readers: ['shop-backend', 'rfm_alert'], freq: '매일', desc: 'RFM 세그먼테이션 (시뮬레이션)' },
  { id: 'mart_assoc', name: 'mart_product_association', domain: 'shop', layer: 'mart', pk: '(antecedents, consequents)', writer: 'basket_analysis', readers: ['shop-backend'], freq: '매일', desc: 'FP-Growth 연관규칙' },
  { id: 'mart_daily', name: 'mart_daily_sales', domain: 'shop', layer: 'mart', pk: '(date, category)', writer: 'shop_mart', readers: ['shop-backend'], freq: '매일', desc: '일별 카테고리 매출' },
  { id: 'mart_summary', name: 'mart_daily_summary', domain: 'shop', layer: 'mart', pk: 'date', writer: 'shop_mart', readers: ['shop-backend'], freq: '매일', desc: '일별 요약 (매출/주문/AOV/top카테고리)' },
  { id: 'mart_weekly', name: 'mart_weekly_sales', domain: 'shop', layer: 'mart', pk: '(week_start, category)', writer: 'shop_mart', readers: ['shop-backend'], freq: '매일', desc: '주별 카테고리 매출' },
  { id: 'dq_anomaly_log', name: 'dq_anomaly_log', domain: 'shop', layer: 'dq', pk: 'id (SERIAL)', writer: 'dq_scoring', readers: ['shop-backend'], freq: '매일', desc: '이상 탐지 로그 (severity/resolved)' },
  // Trade DQ (Shop과 완전 독립)
  { id: 'dq_trade_symbol', name: 'dq_trade_symbol_hourly', domain: 'trade', layer: 'dq', pk: '(hour, symbol)', writer: 'trade-movers', readers: ['trade_dq_scoring'], freq: '1h', desc: '심볼별 틱 카운트/가격/볼륨' },
  { id: 'dq_trade_source', name: 'dq_trade_source_hourly', domain: 'trade', layer: 'dq', pk: '(hour, source)', writer: 'trade-movers', readers: ['trade_dq_scoring'], freq: '1h', desc: '소스별 이벤트 카운트 (교차검증)' },
  { id: 'dq_trade_anomaly_raw', name: 'dq_trade_anomaly_raw', domain: 'trade', layer: 'dq', pk: 'id (SERIAL)', writer: 'trade-movers', readers: ['trade_dq_scoring'], freq: '실시간', desc: '이상 틱 격리 (price≤0, 극단 변동)' },
  { id: 'dq_trade_anomaly_log', name: 'dq_trade_anomaly_log', domain: 'trade', layer: 'dq', pk: 'id (SERIAL)', writer: 'trade_dq_scoring', readers: ['trade-backend'], freq: '매일', desc: 'Trade 이상 탐지 로그' },
  { id: 'dq_trade_score', name: 'dq_trade_daily_score', domain: 'trade', layer: 'dq', pk: 'date', writer: 'trade_dq_scoring', readers: ['trade-backend'], freq: '매일', desc: 'Trade DQ 3차원 스코어 (C/V/T)' },
];

// === 리니지 엣지 ===
const EDGES = [
  // === 인프라 연결 (Architecture 탭용) ===
  { source: 'kafka-laptop', target: 'trade-movers', label: 'raw.ticker.usdtm' },
  { source: 'kafka-laptop', target: 'analytics-streaming', label: 'shopping-events' },
  { source: 'shop-generator', target: 'kafka-laptop', label: 'produce' },
  { source: 'trade-ingest', target: 'kafka-laptop', label: 'produce' },
  { source: 'trade-movers', target: 'postgres', label: 'movers_latest' },
  { source: 'whale-monitor', target: 'postgres', label: 'whale/depth/episode' },
  { source: 'listing-monitor', target: 'postgres', label: 'coin_listing' },
  { source: 'analytics-streaming', target: 'postgres', label: 'sales/funnel/DQ' },
  { source: 'analytics-streaming', target: 'minio', label: 'Parquet archive' },
  { source: 'postgres', target: 'trade-backend', label: 'SQL' },
  { source: 'postgres', target: 'shop-backend', label: 'SQL' },
  { source: 'trade-backend', target: 'trade-frontend', label: 'REST API' },
  { source: 'airflow', target: 'postgres', label: 'DAG 실행' },
  { source: 'journal-bot', target: 'postgres', label: 'memo insert' },
  { source: 'investment-agent', target: 'postgres', label: 'MCP query' },
  { source: 'trade-frontend', target: 'cloudflared', label: '*.6-6ho.com' },
  { source: 'grafana', target: 'postgres', label: 'dashboard query' },
  // === Trade ingestion (Lineage 탭용) ===
  { source: 'binance-ws', target: 'trade-ingest', label: 'WS ticker' },
  { source: 'trade-ingest', target: 'topic-ticker', label: 'produce' },
  { source: 'topic-ticker', target: 'trade-movers', label: 'consume' },
  { source: 'trade-movers', target: 'movers_latest', label: 'upsert' },
  { source: 'trade-movers', target: 'market_snapshot', label: 'upsert' },
  // Whale monitor
  { source: 'binance-ws', target: 'whale-monitor', label: 'aggTrade + forceOrder + REST' },
  { source: 'whale-monitor', target: 'whale_trade', label: 'insert ($1M+)' },
  { source: 'whale-monitor', target: 'orderbook', label: 'insert (30s)' },
  { source: 'whale-monitor', target: 'liquidation', label: 'insert' },
  { source: 'whale-monitor', target: 'move_episode', label: 'detect (15m ±1%)' },
  // Listing
  { source: 'listing-monitor', target: 'coin_listing', label: 'upsert' },
  { source: 'listing-monitor', target: 'listing_event', label: 'insert' },
  // Trade DAGs
  { source: 'movers_latest', target: 'trade_performance_analysis', label: 'read signals' },
  { source: 'trade_performance_analysis', target: 'trade_perf_ts', label: 'JSONB timeseries' },
  { source: 'trade_performance_analysis', target: 'signal_raw', label: 'OHLCV snapshot' },
  { source: 'trade_perf_ts', target: 'signal_validation', label: 'sample 10' },
  { source: 'signal_validation', target: 'signal_val', label: 'pass/fail/error' },
  { source: 'trade_perf_ts', target: 'trade_performance_mart', label: 'Iceberg flat' },
  { source: 'trade_performance_mart', target: 'mart_optimize', label: 'daily aggregate' },
  { source: 'trade_performance_mart', target: 'mart_signal', label: 'per-signal metrics' },
  { source: 'trade_performance_mart', target: 'mart_strategy', label: 'TP/SL simulation' },
  // Theme
  { source: 'market_snapshot', target: 'dynamic_theme', label: 'correlation input' },
  { source: 'dynamic_theme', target: 'daily_corr', label: 'pearson coeff' },
  { source: 'dynamic_theme', target: 'dyn_cluster', label: 'agglomerative' },
  { source: 'market_snapshot', target: 'theme_rs_calculator', label: 'price input' },
  { source: 'theme_rs_calculator', target: 'theme_rs', label: 'RS score' },
  // Screener
  { source: 'coin_listing', target: 'coin_screener', label: 'listing base' },
  { source: 'coin_screener', target: 'screener_latest', label: 'junk classification' },
  // Serving
  { source: 'movers_latest', target: 'trade-backend', label: 'API' },
  { source: 'mart_optimize', target: 'trade-backend', label: 'API (3ms)' },
  { source: 'whale_trade', target: 'trade-backend', label: 'API' },
  { source: 'move_episode', target: 'trade-backend', label: 'API' },
  { source: 'screener_latest', target: 'trade-backend', label: 'API' },
  { source: 'inv_criteria', target: 'trade-backend', label: 'API (public)' },
  { source: 'inv_memo', target: 'trade-backend', label: 'API (auth)' },
  { source: 'trade-backend', target: 'trade-frontend', label: 'REST' },
  // Agent
  { source: 'investment-agent', target: 'inv_criteria', label: 'MCP CRUD' },
  { source: 'journal-bot', target: 'inv_memo', label: 'Voyage embed' },
  { source: 'investment-agent', target: 'movers_latest', label: 'MCP read' },
  { source: 'investment-agent', target: 'screener_latest', label: 'MCP screen' },
  // Shop
  { source: 'shop-generator', target: 'topic-shopping', label: 'produce (100 TPS)' },
  { source: 'topic-shopping', target: 'analytics-streaming', label: 'consume' },
  { source: 'analytics-streaming', target: 'shop_sales', label: '1h window' },
  { source: 'analytics-streaming', target: 'shop_funnel', label: '1h window' },
  { source: 'analytics-streaming', target: 'dq_cat', label: 'DQ category' },
  { source: 'analytics-streaming', target: 'dq_pay', label: 'DQ payment' },
  { source: 'analytics-streaming', target: 'dq_anomaly', label: 'price quarantine' },
  { source: 'analytics-streaming', target: 'minio', label: 'Parquet archive' },
  { source: 'minio', target: 'basket_analysis', label: 'raw events' },
  { source: 'minio', target: 'user_rfm', label: 'raw events' },
  { source: 'basket_analysis', target: 'mart_assoc', label: 'FP-Growth' },
  { source: 'user_rfm', target: 'mart_rfm', label: 'NTILE(5)' },
  { source: 'dq_cat', target: 'dq_scoring', label: 'completeness' },
  { source: 'dq_pay', target: 'dq_scoring', label: 'reconciliation' },
  { source: 'dq_scoring', target: 'dq_score', label: '3-dim score' },
  { source: 'dq_scoring', target: 'dq_anomaly_log', label: 'anomaly detect' },
  // Shop Mart DAG
  { source: 'shop_sales', target: 'shop_mart', label: 'hourly input' },
  { source: 'shop_mart', target: 'mart_daily', label: 'daily aggregate' },
  { source: 'shop_mart', target: 'mart_summary', label: 'daily summary' },
  { source: 'shop_mart', target: 'mart_weekly', label: 'weekly aggregate' },
  // Shop Serving (mart → API)
  { source: 'mart_summary', target: 'shop-backend', label: 'summary + daily-trend API' },
  { source: 'mart_weekly', target: 'shop-backend', label: 'weekly-summary + category-ranking API' },
  { source: 'mart_daily', target: 'shop-backend', label: 'daily-sales API' },
  { source: 'shop_funnel', target: 'shop-backend', label: 'funnel-trend API' },
  { source: 'dq_anomaly_log', target: 'shop-backend', label: 'dq/overview API' },
  { source: 'shop-backend', target: 'shop-frontend', label: 'REST API' },
  // Trade DQ lineage
  { source: 'trade-movers', target: 'dq_trade_symbol', label: 'DQ symbol hourly' },
  { source: 'trade-movers', target: 'dq_trade_source', label: 'DQ source hourly' },
  { source: 'trade-movers', target: 'dq_trade_anomaly_raw', label: 'anomaly quarantine' },
  { source: 'dq_trade_symbol', target: 'trade_dq_scoring', label: 'completeness input' },
  { source: 'dq_trade_source', target: 'trade_dq_scoring', label: 'reconciliation input' },
  { source: 'dq_trade_anomaly_raw', target: 'trade_dq_scoring', label: 'validity input' },
  { source: 'market_snapshot', target: 'trade_dq_scoring', label: 'expected symbols' },
  { source: 'trade_dq_scoring', target: 'dq_trade_score', label: '3-dim score' },
  { source: 'trade_dq_scoring', target: 'dq_trade_anomaly_log', label: 'anomaly detect' },
  { source: 'dq_trade_score', target: 'trade-backend', label: 'DQ API' },
  { source: 'dq_trade_anomaly_log', target: 'trade-backend', label: 'DQ API' },
];

// 도메인 색상
const DOMAIN_COLORS = {
  trade: '#00E396',
  shop: '#775DD0',
  infra: '#FEB019',
  agent: '#A78BFA',
  external: '#888',
};

const LAYER_LABELS = {
  serving: 'Serving', mart: 'Mart', dq: 'DQ', vector: 'Vector', raw: 'Raw',
};
