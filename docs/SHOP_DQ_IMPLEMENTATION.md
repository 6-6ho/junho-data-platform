# Shop 데이터 DQ 체계 구현 계획 (최종)

> **프로젝트 배경**: 이전 회사에서 매장 장비 이슈로 데이터 누락이 발생했으나 감지 시스템이 없어 고객사 신뢰 하락을 경험.
> 이 프로젝트는 **"그런 환경이 있다면 어떻게 구성할까?"**를 직접 구현해보는 것.

---

## 현재 환경 상태

### 노트북 (Trade Processing)
| 서비스 | 상태 | 역할 |
|--------|------|------|
| kafka | ✅ Running | 메시지 브로커 |
| postgres | ✅ Running | 데이터 저장 |
| spark-trade-runner | ✅ Running | Trade 스트리밍 처리 |
| airflow | ✅ Running | 배치 스케줄러 |
| grafana | ✅ Running | 모니터링 대시보드 |

### 데스크탑 (Shop Processing)
| 서비스 | 상태 | 역할 |
|--------|------|------|
| shop-generator | ✅ Running | 쇼핑 이벤트 생성 (~20/sec) |
| spark-shop-runner | ✅ Running | Shop 스트리밍 처리 |
| minio | ✅ Running | Data Lake (D:\minio-data) |

---

## Step 1: 장애 시뮬레이션 환경 구축

### 1-1. shop-generator에 Chaos Mode 추가

**수정 대상**: `apps/shop-generator/generators/shopping_event.py`

```python
class ShoppingEventGenerator:
    def __init__(self, chaos_mode=False):
        self.chaos_mode = chaos_mode
        self.failed_categories = set()      # 장애 난 카테고리
        self.failed_payments = set()        # 장애 난 결제수단
        
    def _simulate_failures(self):
        """장애 상황 시뮬레이션 (5분마다 상태 변경)"""
        import random
        
        # 3% 확률로 카테고리 장애 발생
        if random.random() < 0.03:
            category = random.choice(['fashion', 'electronics', 'beauty', 'food', 'home'])
            self.failed_categories.add(category)
            print(f"[CHAOS] Category failure: {category}")
        
        # 5% 확률로 복구
        if self.failed_categories and random.random() < 0.05:
            recovered = self.failed_categories.pop()
            print(f"[CHAOS] Category recovered: {recovered}")
        
        # 2% 확률로 결제수단 장애
        if random.random() < 0.02:
            payment = random.choice(['kakao_pay', 'naver_pay', 'toss'])
            self.failed_payments.add(payment)
            print(f"[CHAOS] Payment failure: {payment}")
    
    def generate(self) -> dict:
        if self.chaos_mode:
            self._simulate_failures()
            
        event = self._generate_base_event()
        
        # 장애 난 카테고리면 데이터 누락
        if event['category'] in self.failed_categories:
            return None  # 데이터 누락!
        
        # 장애 난 결제수단이면 purchase 누락
        if event['event_type'] == 'purchase':
            if event.get('payment_method') in self.failed_payments:
                return None
        
        # 1% 확률로 이상 데이터 생성 (버그 시뮬레이션)
        if self.chaos_mode and random.random() < 0.01:
            event['price'] = random.choice([-100, 0, 99999999])  # 비정상 가격
        
        return event
```

**수정 대상**: `apps/shop-generator/main.py`

```python
import os

CHAOS_MODE = os.getenv('CHAOS_MODE', 'false').lower() == 'true'

generator = ShoppingEventGenerator(chaos_mode=CHAOS_MODE)
```

**docker-compose.desktop.yml 수정**:
```yaml
shop-generator:
  environment:
    - CHAOS_MODE=true  # 장애 시뮬레이션 활성화
```

---

## Step 2: DQ 모니터링 테이블 생성

**수정 대상**: `docs/07_db_ddl.sql` 또는 새 마이그레이션

```sql
-- ================================================
-- DQ (Data Quality) 모니터링 테이블
-- ================================================

-- 카테고리별 시간당 이벤트 건수 (누락 감지용)
CREATE TABLE IF NOT EXISTS dq_category_hourly (
    hour TIMESTAMP,
    category VARCHAR(50),
    event_count INT,
    purchase_count INT,
    total_revenue DECIMAL(15,2),
    PRIMARY KEY (hour, category)
);

-- 결제수단별 시간당 건수 (결제 장애 감지용)
CREATE TABLE IF NOT EXISTS dq_payment_hourly (
    hour TIMESTAMP,
    payment_method VARCHAR(50),
    purchase_count INT,
    total_revenue DECIMAL(15,2),
    PRIMARY KEY (hour, payment_method)
);

-- DQ 이상 탐지 로그
CREATE TABLE IF NOT EXISTS dq_anomaly_log (
    id SERIAL PRIMARY KEY,
    detected_at TIMESTAMP DEFAULT NOW(),
    anomaly_type VARCHAR(100),  -- 'category_missing', 'payment_drop', 'abnormal_price'
    dimension VARCHAR(100),      -- 어떤 카테고리/결제수단
    expected_value DECIMAL(15,2),
    actual_value DECIMAL(15,2),
    severity VARCHAR(20),        -- 'warning', 'critical'
    resolved BOOLEAN DEFAULT FALSE
);

-- DQ 일별 스코어 (대시보드용)
CREATE TABLE IF NOT EXISTS dq_daily_score (
    date DATE PRIMARY KEY,
    completeness_score INT,      -- 데이터 완전성 (100점 만점)
    validity_score INT,          -- 데이터 유효성
    timeliness_score INT,        -- 데이터 적시성
    total_score INT,             -- 종합 점수
    anomaly_count INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Step 3: Spark에서 DQ 집계 추가

**수정 대상**: `spark/jobs/shop_streaming.py`

```python
# 기존 집계 외 DQ용 집계 추가
def process_for_dq(batch_df, batch_id):
    """DQ 모니터링용 집계"""
    from pyspark.sql.functions import hour, count, sum as spark_sum
    
    # 카테고리별 시간당 집계
    category_hourly = batch_df \
        .withColumn("hour", hour("event_time")) \
        .groupBy("hour", "category") \
        .agg(
            count("*").alias("event_count"),
            spark_sum((col("event_type") == "purchase").cast("int")).alias("purchase_count"),
            spark_sum("total_amount").alias("total_revenue")
        )
    
    category_hourly.write.mode("append") \
        .jdbc(DB_URL, "dq_category_hourly", properties=DB_PROPERTIES)
    
    # 결제수단별 시간당 집계 (purchase만)
    payment_hourly = batch_df \
        .filter(col("event_type") == "purchase") \
        .withColumn("hour", hour("event_time")) \
        .groupBy("hour", "payment_method") \
        .agg(
            count("*").alias("purchase_count"),
            spark_sum("total_amount").alias("total_revenue")
        )
    
    payment_hourly.write.mode("append") \
        .jdbc(DB_URL, "dq_payment_hourly", properties=DB_PROPERTIES)
    
    # 이상 가격 데이터 감지 및 격리
    anomalies = batch_df.filter(
        (col("price") < 0) | (col("price") > 10000000)
    )
    
    if anomalies.count() > 0:
        anomalies.write.mode("append") \
            .jdbc(DB_URL, "dq_anomaly_raw", properties=DB_PROPERTIES)
```

---

## Step 4: Airflow DQ 감지 DAG

**새 파일**: `airflow/dags/dq_monitoring.py`

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'junho',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def check_category_completeness(**context):
    """카테고리별 데이터 누락 감지"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # 지난 1시간 카테고리별 건수
    result = pg_hook.get_records("""
        SELECT category, event_count
        FROM dq_category_hourly
        WHERE hour = DATE_TRUNC('hour', NOW() - INTERVAL '1 hour')
    """)
    
    expected_categories = {'fashion', 'electronics', 'beauty', 'food', 'home'}
    found_categories = {r[0] for r in result}
    
    # 누락된 카테고리
    missing = expected_categories - found_categories
    if missing:
        # 이상 로그 기록
        for cat in missing:
            pg_hook.run("""
                INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity)
                VALUES ('category_missing', %s, 100, 0, 'critical')
            """, parameters=[cat])
        
        send_alert(f"🚨 DQ Alert: 카테고리 데이터 누락 - {missing}")
    
    # 건수가 너무 적은 카테고리 (평균의 30% 미만)
    if result:
        avg_count = sum(r[1] for r in result) / len(result)
        for cat, count in result:
            if count < avg_count * 0.3:
                pg_hook.run("""
                    INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity)
                    VALUES ('category_low_volume', %s, %s, %s, 'warning')
                """, parameters=[cat, avg_count, count])
                
                send_alert(f"⚠️ DQ Warning: {cat} 카테고리 건수 급감 ({count} < 평균 {avg_count:.0f})")

def check_payment_health(**context):
    """결제수단별 장애 감지"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    result = pg_hook.get_records("""
        SELECT payment_method, purchase_count
        FROM dq_payment_hourly
        WHERE hour = DATE_TRUNC('hour', NOW() - INTERVAL '1 hour')
    """)
    
    expected_payments = {'card', 'kakao_pay', 'naver_pay', 'toss'}
    found_payments = {r[0] for r in result}
    
    missing = expected_payments - found_payments
    if missing:
        for payment in missing:
            pg_hook.run("""
                INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity)
                VALUES ('payment_missing', %s, 100, 0, 'critical')
            """, parameters=[payment])
        
        send_alert(f"🚨 DQ Alert: 결제수단 장애 의심 - {missing}")

def calculate_daily_dq_score(**context):
    """일별 DQ 스코어 계산"""
    pg_hook = PostgresHook(postgres_conn_id='postgres_default')
    
    # 오늘의 이상 건수
    anomaly_result = pg_hook.get_first("""
        SELECT 
            COUNT(*) FILTER (WHERE severity = 'critical') as critical_count,
            COUNT(*) FILTER (WHERE severity = 'warning') as warning_count
        FROM dq_anomaly_log
        WHERE DATE(detected_at) = CURRENT_DATE
    """)
    
    critical_count = anomaly_result[0] or 0
    warning_count = anomaly_result[1] or 0
    
    # 점수 계산 (100점 만점)
    # Critical: -20점, Warning: -5점
    completeness_score = max(0, 100 - (critical_count * 20) - (warning_count * 5))
    
    # 스코어 저장
    pg_hook.run("""
        INSERT INTO dq_daily_score (date, completeness_score, validity_score, timeliness_score, total_score, anomaly_count)
        VALUES (CURRENT_DATE, %s, 100, 100, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            completeness_score = EXCLUDED.completeness_score,
            total_score = EXCLUDED.total_score,
            anomaly_count = EXCLUDED.anomaly_count
    """, parameters=[completeness_score, completeness_score, critical_count + warning_count])

def send_alert(message):
    """Slack 또는 로그로 알림"""
    print(f"[ALERT] {message}")
    # TODO: Slack webhook 연동

with DAG(
    'dq_monitoring',
    default_args=default_args,
    description='Data Quality 모니터링',
    schedule_interval='*/10 * * * *',  # 10분마다
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:
    
    check_category = PythonOperator(
        task_id='check_category_completeness',
        python_callable=check_category_completeness
    )
    
    check_payment = PythonOperator(
        task_id='check_payment_health',
        python_callable=check_payment_health
    )
    
    calculate_score = PythonOperator(
        task_id='calculate_daily_dq_score',
        python_callable=calculate_daily_dq_score
    )
    
    [check_category, check_payment] >> calculate_score
```

---

## Step 5: Grafana DQ 대시보드

**새 대시보드 패널들**:

### 패널 1: 카테고리별 실시간 상태
```sql
SELECT 
    category,
    event_count,
    CASE 
        WHEN event_count = 0 THEN 'CRITICAL'
        WHEN event_count < 50 THEN 'WARNING'
        ELSE 'OK'
    END as status
FROM dq_category_hourly
WHERE hour = DATE_TRUNC('hour', NOW())
ORDER BY event_count DESC;
```

### 패널 2: 결제수단별 상태
```sql
SELECT 
    payment_method,
    purchase_count,
    total_revenue,
    CASE 
        WHEN purchase_count = 0 THEN '🔴 DOWN'
        WHEN purchase_count < 10 THEN '🟡 LOW'
        ELSE '🟢 OK'
    END as status
FROM dq_payment_hourly
WHERE hour = DATE_TRUNC('hour', NOW());
```

### 패널 3: DQ Score 추이
```sql
SELECT 
    date,
    total_score,
    anomaly_count
FROM dq_daily_score
ORDER BY date DESC
LIMIT 30;
```

### 패널 4: 최근 이상 탐지 로그
```sql
SELECT 
    detected_at,
    anomaly_type,
    dimension,
    severity
FROM dq_anomaly_log
WHERE resolved = FALSE
ORDER BY detected_at DESC
LIMIT 10;
```

---

## 구현 체크리스트

### Phase 1: 장애 시뮬레이션 (1일)
- [ ] `shopping_event.py`에 Chaos Mode 추가
- [ ] `main.py`에서 CHAOS_MODE 환경변수 처리
- [ ] `docker-compose.desktop.yml`에 CHAOS_MODE=true 설정
- [ ] 데스크탑 shop-generator 재배포 및 테스트

### Phase 2: DQ 테이블 & Spark 집계 (1일)
- [ ] DQ 관련 테이블 DDL 실행
- [ ] `shop_streaming.py`에 DQ 집계 로직 추가
- [ ] 데스크탑 spark-shop-runner 재배포

### Phase 3: Airflow DAG (1일)
- [ ] `dq_monitoring.py` DAG 생성
- [ ] Airflow에 postgres connection 설정
- [ ] DAG 테스트 및 스케줄 확인

### Phase 4: Grafana 대시보드 (0.5일)
- [ ] DQ 대시보드 JSON 생성
- [ ] 카테고리/결제수단 상태 패널
- [ ] DQ Score 추이 패널
- [ ] 이상 로그 테이블 패널

### Phase 5: 문서화 & 스토리 정리 (0.5일)
- [ ] README 업데이트
- [ ] 면접용 스토리 정리
- [ ] 스크린샷 캡처

---

## 면접 스토리텔링 (최종)

> **Q: 이 프로젝트를 왜 만들었나요?**
>
> "이전 회사에서 매장 POS 장비 이슈로 데이터가 누락되는 문제가 빈번했습니다.
> 문제는 이를 감지할 시스템이 없어서, 고객사가 '숫자가 이상한데요'라고 
> 물어봐서야 알게 되는 경우가 많았습니다. 데이터 신뢰도 하락으로 이어졌죠.
>
> 저는 '데이터 누락을 미리 감지하고, 한눈에 상태를 파악할 수 있는 시스템'이 
> 있다면 좋겠다고 생각했습니다. 하지만 당시에는 그럴 환경이 없었습니다.
>
> 그래서 개인 프로젝트로 **장애 상황을 시뮬레이션**하고, 
> 이를 **DQ 체계로 감지**하는 시스템을 직접 구현해봤습니다."
>
> **Q: 구체적으로 어떻게 구현했나요?**
>
> "shop-generator에서 **일부러 카테고리별/결제수단별 장애를 시뮬레이션**합니다.
> 3% 확률로 특정 카테고리가 다운되고, 5% 확률로 복구되는 식입니다.
>
> Spark Streaming에서 **카테고리별, 결제수단별 시간당 건수**를 집계하고,
> Airflow가 **10분마다 이상 여부를 체크**합니다.
>
> 예를 들어 'fashion' 카테고리가 갑자기 0건이면 **'category_missing' 이상**으로 감지하고,
> Grafana 대시보드에서 **빨간불**로 표시됩니다. 담당자가 빠르게 인지할 수 있죠.
>
> 또한 **DQ Score**를 일별로 계산해서, 전체적인 데이터 품질 추이를 모니터링합니다.
> Critical 이상이 발생하면 -20점, Warning이면 -5점으로 점수가 감소합니다."

---

## 파일 구조 (최종)

```
junho-data-platform/
├── apps/
│   └── shop-generator/
│       └── generators/
│           └── shopping_event.py  # Chaos Mode 추가
├── spark/
│   └── jobs/
│       └── shop_streaming.py      # DQ 집계 로직 추가
├── airflow/
│   └── dags/
│       └── dq_monitoring.py       # DQ 감지 DAG
├── infra/
│   └── grafana/
│       └── dashboards/
│           └── dq_dashboard.json  # DQ 대시보드
└── docs/
    ├── SHOP_DQ_IMPLEMENTATION.md  # 이 문서
    └── ...
```
