# Spark 분산 처리 아키텍처

## 클러스터 구성

```
                ┌──────────────────┐
                │   Spark Master   │
                │    (0.5 CPU)     │
                └──────┬───────────┘
           ┌───────────┴───────────┐
    ┌──────┴──────┐         ┌──────┴──────┐
    │  Worker-1   │         │  Worker-2   │
    │  4코어 / 4G │         │  3코어 / 3G │
    └─────────────┘         └─────────────┘
```

| 노드 | CPU | Memory | 역할 |
|------|-----|--------|------|
| Master | 0.5 | 512M | 클러스터 관리 |
| Worker-1 | 4코어 | 4G | Executor 호스팅 |
| Worker-2 | 3코어 | 3G | Executor 호스팅 |

## 리소스 할당 전략

### 스트리밍 (상시 실행)

| 설정 | 값 | 근거 |
|------|-----|------|
| `spark.cores.max` | 4 | Worker-1에서 2코어 + Worker-2에서 2코어 |
| `spark.executor.cores` | 2 | executor 2개 병렬 처리 |
| `spark.executor.memory` | 1536m | 18GB RAM 환경에서 안전한 범위 |
| `spark.sql.shuffle.partitions` | 8 | 코어 수 x 2 (파이프라이닝) |
| `maxRatePerPartition` | 500 | 1,000 TPS burst 대응 |

### 배치 (DAG 스케줄)

| 설정 | 값 | 근거 |
|------|-----|------|
| `spark.cores.max` | 3 | 스트리밍과 리소스 공존 |
| `spark.executor.cores` | 1 | 3개 executor (W1에 2개, W2에 1개) |
| `spark.executor.memory` | 1g | 배치는 메모리 부담 적음 |
| `spark.sql.shuffle.partitions` | 6 | executor 수 x 2 |

### 리소스 공존 (스트리밍 + 배치 동시 실행)

```
Worker-1 (4코어):  [Streaming-E1: 2코어] [Batch-E1: 1코어] [Batch-E2: 1코어]
Worker-2 (3코어):  [Streaming-E2: 2코어] [Batch-E3: 1코어]
```

FAIR 스케줄러로 리소스 공유, 배치가 스트리밍을 밀어내지 않음.

## AQE (Adaptive Query Execution)

활성화된 기능:

- **Skew Join**: category_bias 모드에서 특정 카테고리에 데이터 몰릴 때 자동으로 파티션 분할
- **Coalesce Partitions**: 셔플 후 작은 파티션을 자동 병합하여 overhead 감소
- **locality.wait=3s**: 데이터 로컬리티 대기 후 원격 실행으로 fallback

## 벤치마크

### 실행 방법

```bash
# 방법 1: Airflow DAG (수동 트리거)
# Airflow UI → benchmark_distributed → Trigger DAG

# 방법 2: Burst + 벤치마크 자동화
./scripts/run_burst_benchmark.sh 1000 30  # 1000 TPS, 30분
```

### 벤치마크 워크로드

| 워크로드 | 설명 | 셔플 |
|---------|------|------|
| Aggregation | groupBy(category, user_id) + sum/count | O |
| Window Function | row_number() over(partitionBy user_id) | O |
| Join | user_stats self-join | O |
| Basket Prep | collect_list로 장바구니 생성 | O |

### 결과 확인

```sql
SELECT config_name, partitions, executor_count, total_cores, row_count,
       aggregation_sec, window_function_sec, join_sec, basket_prep_sec
FROM spark_benchmark_results
ORDER BY created_at DESC;
```

### 실측 결과 (530만 행, 2026-03-02)

| 구성 | Partitions | Aggregation | Window | Join | Basket Prep |
|------|-----------|-------------|--------|------|-------------|
| **single** (1 executor) | 8 | 4.169s | 5.275s | 4.640s | 2.985s |
| **multi** (2 executors) | 8 | **2.195s** | **2.505s** | **0.790s** | **2.189s** |
| **개선율** | — | **47%** | **52%** | **83%** | **27%** |

셔플 의존도가 높은 **Window Function(52%)** 과 **Join(83%)** 에서 분산 효과가 가장 크게 나타남.

## 환경별 설정

| 환경 | cores.max | executor.cores | executor.memory | shuffle.partitions |
|------|-----------|---------------|-----------------|-------------------|
| Desktop (18GB) | 4 | 2 | 1536m | 8 |
| Laptop (8GB) | 2 | 1 | 1024m | 4 |
