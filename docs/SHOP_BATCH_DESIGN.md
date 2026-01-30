# Shop 데이터 처리 아키텍처

## 현재 구조 (Real-time Streaming)

```
┌─────────────────────────────────────────────────────────────────┐
│  shop-generator                                                 │
│  (실시간 이벤트 생성 ~20 events/sec)                              │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
              Kafka: shopping-events
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  spark-shop-runner (Streaming)                                  │
│  - 30초마다 micro-batch 처리                                     │
│  - Sales, Brand, Funnel, KPI 집계                               │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
                   PostgreSQL
                        │
                        ▼
                 Shop Analytics App
```

### 장점
- **실시간 대시보드**: 데이터 지연 ~30초
- **즉각적인 인사이트**: Funnel 분석, KPI 모니터링

### 단점
- **리소스 상시 점유**: Spark가 계속 실행됨
- **복잡한 집계 어려움**: 대규모 재계산 비효율적

---

## 제안: Hybrid 구조 (Streaming + Batch)

### 아키텍처
```
┌─────────────────────────────────────────────────────────────────┐
│  shop-generator                                                 │
└───────────────────────┬─────────────────────────────────────────┘
                        ▼
              Kafka: shopping-events
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
   [Streaming Layer]         [Batch Layer - Airflow]
   실시간 KPI 전용             일/주/월 집계
   - 5분 윈도우 매출            
   - 실시간 사용자 수           DAG 스케줄:
                               - 매일 02:00: 일별 집계
                               - 매주 월 03:00: 주별 리포트
                               - 매월 1일 04:00: 월별 분석
            │                       │
            ▼                       ▼
┌──────────────────┐    ┌──────────────────────────┐
│  PostgreSQL      │    │  MinIO (Data Lake)       │
│  (Hot Data)      │    │  - Parquet 저장          │
│  - 실시간 KPI    │    │  - 장기 보존              │
│  - 24시간 데이터  │    │  - 대용량 분석용          │
└──────────────────┘    └──────────────────────────┘
```

### Streaming으로 처리할 것 (현재 유지)
| 작업 | 이유 |
|------|------|
| 5분 윈도우 매출 | 실시간 대시보드 |
| 활성 사용자 수 | 즉각적인 모니터링 |
| 실시간 알림 트리거 | 빠른 대응 필요 |

### Batch로 전환할 것 (Airflow)
| 작업 | 스케줄 | 이유 |
|------|--------|------|
| 일별 매출 요약 | 매일 02:00 | 정확한 집계 필요 |
| 브랜드별 분석 | 매일 03:00 | 대량 데이터 처리 |
| Funnel 분석 | 매일 04:00 | 복잡한 조인 연산 |
| 주간/월간 리포트 | 주/월 | 경영 리포트 |
| 데이터 마켓 Export | 필요시 | 외부 시스템 연동 |

---

## Airflow DAG 예시

### 일별 Shop 집계 DAG
```python
# dags/shop_daily_aggregation.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'junho',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'shop_daily_aggregation',
    default_args=default_args,
    description='Daily shop data aggregation',
    schedule_interval='0 2 * * *',  # 매일 02:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    aggregate_sales = PostgresOperator(
        task_id='aggregate_daily_sales',
        postgres_conn_id='postgres_default',
        sql='''
            INSERT INTO shop_daily_sales (date, category, total_revenue, order_count)
            SELECT 
                DATE(window_start) as date,
                category,
                SUM(total_revenue) as total_revenue,
                SUM(order_count) as order_count
            FROM shop_hourly_sales_log
            WHERE DATE(window_start) = CURRENT_DATE - INTERVAL '1 day'
            GROUP BY DATE(window_start), category
            ON CONFLICT (date, category) DO UPDATE SET
                total_revenue = EXCLUDED.total_revenue,
                order_count = EXCLUDED.order_count;
        '''
    )

    export_to_minio = PythonOperator(
        task_id='export_to_data_lake',
        python_callable=export_daily_to_minio,
    )

    aggregate_sales >> export_to_minio
```

### 마켓 데이터 Export DAG
```python
# dags/shop_market_export.py
from airflow import DAG
from airflow.operators.python import PythonOperator

def export_to_market():
    """외부 마켓 플랫폼으로 데이터 전송"""
    import pandas as pd
    import requests
    
    # PostgreSQL에서 데이터 조회
    df = pd.read_sql('''
        SELECT * FROM shop_daily_sales 
        WHERE date = CURRENT_DATE - INTERVAL '1 day'
    ''', conn)
    
    # 마켓 API로 전송
    response = requests.post(
        'https://market-api.example.com/data',
        json=df.to_dict(orient='records'),
        headers={'Authorization': 'Bearer xxx'}
    )
    
    return response.status_code

with DAG(
    'shop_market_export',
    schedule_interval='0 6 * * *',  # 매일 06:00 (집계 후)
    ...
) as dag:
    
    export_task = PythonOperator(
        task_id='export_to_market',
        python_callable=export_to_market,
    )
```

---

## 마이그레이션 단계

### Phase 1: 현재 유지 (완료)
- [x] Streaming으로 모든 처리
- [x] Postgres에 실시간 저장

### Phase 2: Batch 인프라 구축
- [ ] Airflow DAG 폴더 구조 정리
- [ ] PostgreSQL 일별/주별/월별 테이블 생성
- [ ] MinIO 버킷 구조 설계

### Phase 3: Hybrid 전환
- [ ] 실시간 처리 범위 축소 (KPI만)
- [ ] Airflow DAG 배포 및 테스트
- [ ] 모니터링 대시보드 조정

### Phase 4: 마켓 연동
- [ ] 외부 마켓 API 연동
- [ ] 데이터 포맷 표준화
- [ ] Export DAG 구현

---

## 의사결정 기준

| 기준 | Streaming | Batch |
|------|-----------|-------|
| 지연시간 | < 1분 | 1시간+ |
| 데이터량 | 적음 | 대량 |
| 정확도 | 근사치 OK | 정확해야 함 |
| 재처리 | 어려움 | 쉬움 |
| 비용 | 상시 리소스 | 필요시만 |
