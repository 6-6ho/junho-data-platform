# 토스뱅크 정보계 DE 공고 기반 프로젝트 고도화 전략

> **참고 공고**: [토스뱅크 Data Engineer (정보계, 3년이하)](https://www.wanted.co.kr/wd/336406)

---

## 공고 핵심 키워드 분석

| 키워드 | 공고 요구사항 | 우리 프로젝트 현황 | Gap |
|--------|---------------|-------------------|-----|
| **데이터 정합성/DQ** | 신뢰도 높은 데이터 체계, 품질 관리 | 기본 저장만 구현 | 🔴 미구현 |
| **데이터 마트** | 분석용 마트 설계/구축/운영 | Raw 데이터 저장만 | 🔴 미구현 |
| **자동화/시스템화** | 단순 작업 → 구조적 개선 | 수동 빌드/배포 | 🟡 부분적 |
| **Hadoop/오픈소스** | Hadoop 기반 환경 이해 | Spark + Kafka 사용 | 🟢 충족 |
| **SQL 숙련도** | 필수 | Spark SQL 사용 중 | 🟢 충족 |
| **비즈니스 임팩트** | 데이터 기반 의사결정 지원 | 대시보드 존재 | 🟡 발전 필요 |

---

## 1. 데이터 정합성(DQ) 체계 구축 🔴 최우선

### 왜 중요한가?
> "높은 데이터 정합성 기준과 신뢰도를 최우선으로 합니다" - 공고 원문

정보계의 핵심은 **숫자가 맞아야 한다**는 것. 금융 데이터가 1원이라도 틀리면 감사 이슈.

### 구현 계획

#### 1-1. Source-Sink 정합성 체크
```
Kafka(shopping-events) → Spark → Postgres

- Source: Kafka 메시지 건수
- Sink: Postgres 테이블 건수
- 차이가 있으면 Alert!
```

**Airflow DAG 예시:**
```python
# dags/data_quality_check.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta

def check_source_sink_consistency(**context):
    """Source(Kafka offset) vs Sink(Postgres count) 비교"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # 어제 Postgres에 적재된 건수
    result = pg_hook.get_first("""
        SELECT COUNT(*) FROM shop_hourly_sales_log
        WHERE DATE(window_start) = CURRENT_DATE - INTERVAL '1 day'
    """)
    postgres_count = result[0]
    
    # Kafka offset (별도 메타테이블에서 관리 필요)
    kafka_count = get_kafka_offset_for_yesterday()
    
    diff_rate = abs(kafka_count - postgres_count) / kafka_count * 100
    
    if diff_rate > 1:  # 1% 이상 차이
        raise ValueError(f"DQ Alert! Kafka: {kafka_count}, Postgres: {postgres_count}")
    
    return {"kafka": kafka_count, "postgres": postgres_count, "diff_rate": diff_rate}

with DAG('data_quality_daily', schedule='0 5 * * *', ...) as dag:
    dq_check = PythonOperator(
        task_id='source_sink_consistency',
        python_callable=check_source_sink_consistency
    )
```

#### 1-2. 비즈니스 로직 DQ 체크
```python
# 비정상 데이터 탐지
def check_business_rules(**context):
    """비즈니스 규칙 위반 데이터 탐지"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    anomalies = pg_hook.get_records("""
        SELECT * FROM shop_hourly_sales_log
        WHERE 
            total_revenue < 0  -- 음수 매출?
            OR order_count = 0 AND total_revenue > 0  -- 주문 없는데 매출?
            OR avg_order_value > 10000000  -- 1천만원 이상 평균 주문?
        AND DATE(window_start) = CURRENT_DATE - INTERVAL '1 day'
    """)
    
    if anomalies:
        # Slack 알림 전송
        send_slack_alert(f"DQ Alert: {len(anomalies)} anomalies found")
        
        # 이상 데이터 별도 테이블에 격리
        for row in anomalies:
            quarantine_record(row)
```

#### 1-3. DQ 대시보드 (Grafana)
```sql
-- 일별 DQ Score (100점 만점)
SELECT 
    date,
    100 - (
        COALESCE(null_rate, 0) * 30 +  -- NULL 비율 (30점)
        COALESCE(anomaly_rate, 0) * 40 +  -- 이상치 비율 (40점)
        COALESCE(lag_hours, 0) * 3  -- 지연 시간당 3점 감점 (30점)
    ) as dq_score
FROM dq_metrics_daily
ORDER BY date DESC;
```

---

## 2. 데이터 마트 설계 (계층화) 🔴

### 현재 구조
```
Raw Events → Postgres 테이블 (Flat)
```

### 목표 구조 (Medallion Architecture)
```
┌─────────────────────────────────────────────────────────────────┐
│  Bronze Layer (Raw)                                             │
│  - shop_events_raw (Kafka 원본 그대로)                          │
│  - 변환 없음, 감사 추적용                                        │
└───────────────────────┬─────────────────────────────────────────┘
                        │ Spark Streaming
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Silver Layer (Cleansed)                                        │
│  - shop_hourly_sales (시간별 집계)                              │
│  - shop_brand_stats (브랜드별 집계)                             │
│  - 중복 제거, 타입 정리, NULL 처리                              │
└───────────────────────┬─────────────────────────────────────────┘
                        │ Airflow Batch (Daily)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  Gold Layer (Business Ready)                                    │
│  - mart_daily_sales (일별 요약)                                 │
│  - mart_user_cohort (사용자 코호트)                             │
│  - mart_category_trend (카테고리 트렌드)                         │
│  - 비즈니스 의사결정용 최종 마트                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Gold Layer 마트 예시

**일별 매출 마트:**
```sql
-- dags/sql/create_mart_daily_sales.sql
CREATE TABLE IF NOT EXISTS mart_daily_sales (
    date DATE PRIMARY KEY,
    total_revenue DECIMAL(15,2),
    total_orders INT,
    unique_customers INT,
    avg_order_value DECIMAL(10,2),
    top_category VARCHAR(100),
    yoy_growth_rate DECIMAL(5,2),  -- 전년 대비 성장률
    wow_growth_rate DECIMAL(5,2),  -- 전주 대비 성장률
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO mart_daily_sales (date, total_revenue, total_orders, ...)
SELECT 
    DATE(window_start) as date,
    SUM(total_revenue) as total_revenue,
    SUM(order_count) as total_orders,
    -- 전년 대비 성장률 계산
    ROUND(
        (SUM(total_revenue) - LAG(SUM(total_revenue), 365) OVER (ORDER BY DATE(window_start)))
        / NULLIF(LAG(SUM(total_revenue), 365) OVER (ORDER BY DATE(window_start)), 0) * 100, 2
    ) as yoy_growth_rate
FROM shop_hourly_sales_log
WHERE DATE(window_start) = CURRENT_DATE - INTERVAL '1 day'
GROUP BY DATE(window_start)
ON CONFLICT (date) DO UPDATE SET ...;
```

**사용자 코호트 분석 마트:**
```sql
-- 첫 구매 월 기준 Retention 분석
CREATE TABLE mart_user_cohort AS
SELECT 
    first_purchase_month,
    months_since_first,
    COUNT(DISTINCT user_id) as users,
    SUM(total_amount) as revenue
FROM (
    SELECT 
        user_id,
        DATE_TRUNC('month', MIN(event_time)) as first_purchase_month,
        DATE_TRUNC('month', event_time) - DATE_TRUNC('month', MIN(event_time)) 
            as months_since_first,
        total_amount
    FROM shop_events_raw
    WHERE event_type = 'purchase'
    GROUP BY user_id, event_time, total_amount
) cohort_base
GROUP BY first_purchase_month, months_since_first;
```

---

## 3. 자동화 및 시스템화 🟡

### 현재: 수동 프로세스
```
개발자가 코드 수정 → git push → SSH 접속 → docker compose up
```

### 목표: Self-Healing Pipeline
```
Git Push → Auto Deploy → Health Check → Auto Recovery → Slack Alert
```

### 구현 요소

#### 3-1. Airflow로 파이프라인 모니터링
```python
# dags/pipeline_health_monitor.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

def check_spark_job_health():
    """Spark Job이 살아있는지 확인, 죽어있으면 재시작"""
    import docker
    client = docker.from_env()
    
    container = client.containers.get('spark-shop-runner')
    
    if container.status != 'running':
        container.restart()
        send_slack_alert("⚠️ spark-shop-runner 재시작됨")
        
    return container.status

with DAG('pipeline_health', schedule='*/5 * * * *') as dag:  # 5분마다
    health_check = PythonOperator(
        task_id='check_spark_health',
        python_callable=check_spark_job_health
    )
```

#### 3-2. 데이터 지연 감지
```python
def check_data_freshness():
    """데이터가 10분 이상 안 들어오면 Alert"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    result = pg_hook.get_first("""
        SELECT MAX(window_end) FROM shop_hourly_sales_log
    """)
    last_data_time = result[0]
    
    if datetime.now() - last_data_time > timedelta(minutes=10):
        send_slack_alert(f"🚨 Data Lag Alert! Last data: {last_data_time}")
```

#### 3-3. 실패 시 자동 재처리
```python
# 배치 잡 실패 시 자동 재시도 + 수동 트리거 가능
with DAG(
    'shop_daily_aggregation',
    default_args={
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
        'on_failure_callback': slack_failure_alert
    },
    max_active_runs=1,
    catchup=True  # 놓친 날짜 자동 재처리
) as dag:
    ...
```

---

## 4. 비즈니스 가치 창출 (마켓 Export)

### 시나리오: 외부 마켓 플랫폼으로 데이터 전송

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Gold Layer      │────▶│  Airflow Batch   │────▶│  Market API      │
│  (mart_daily)    │     │  (Export DAG)    │     │  (외부 시스템)    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                │
                                ▼
                         ┌──────────────────┐
                         │  Export History  │
                         │  (감사 추적용)    │
                         └──────────────────┘
```

### Export DAG 템플릿
```python
# dags/market_export.py
def export_to_market(**context):
    """Gold Layer 데이터를 외부 마켓에 전송"""
    import pandas as pd
    import requests
    
    # 1. 데이터 조회
    df = pd.read_sql("""
        SELECT * FROM mart_daily_sales 
        WHERE date = %(date)s
    """, conn, params={'date': context['ds']})
    
    # 2. 데이터 검증
    if df.empty:
        raise ValueError("No data to export")
    
    if df['total_revenue'].isna().any():
        raise ValueError("NULL revenue found - DQ issue")
    
    # 3. API 전송
    response = requests.post(
        'https://market-api.example.com/daily-report',
        json=df.to_dict(orient='records'),
        headers={'Authorization': f'Bearer {API_KEY}'}
    )
    response.raise_for_status()
    
    # 4. 감사 로그
    log_export_history(context['ds'], len(df), response.status_code)
    
    return {"exported_rows": len(df), "status": response.status_code}
```

---

## 5. 구현 우선순위 및 로드맵

### Phase 1: DQ 체계 (1주)
- [ ] Source-Sink 건수 비교 DAG
- [ ] 이상치 탐지 DAG
- [ ] DQ Score Grafana 패널

### Phase 2: 데이터 마트 (2주)
- [ ] Bronze/Silver/Gold 테이블 스키마 설계
- [ ] `mart_daily_sales` 생성 DAG
- [ ] `mart_user_cohort` 생성 DAG

### Phase 3: 자동화 (1주)
- [ ] Pipeline Health Monitor DAG
- [ ] Data Freshness Alert
- [ ] Slack 연동

### Phase 4: 마켓 연동 (필요시)
- [ ] Export API 연동
- [ ] 감사 로그 테이블
- [ ] 재처리 메커니즘

---

## 포트폴리오 어필 포인트

### 면접에서 이렇게 말할 수 있음

> "쇼핑 데이터 파이프라인을 구축하면서 **단순 저장을 넘어 데이터 정합성 체계(DQ)**를 도입했습니다. 
> Airflow를 활용해 매일 Source-Sink 건수를 비교하고, 비즈니스 규칙 위반 데이터를 자동 탐지합니다.
> 
> 또한 **Medallion Architecture를 적용해 Bronze→Silver→Gold 계층으로 마트를 설계**했고,
> 이를 통해 비즈니스 의사결정에 바로 활용 가능한 `mart_daily_sales`, `mart_user_cohort` 등을 
> 일 배치로 생성합니다.
> 
> 파이프라인 장애 시 **Airflow가 자동으로 재시작하고 Slack 알림을 보내는 Self-Healing 구조**도 
> 구축하여 운영 안정성을 확보했습니다."

이 내용이 공고의 핵심 역량과 정확히 일치합니다! 🎯
