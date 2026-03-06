#!/bin/bash
# Burst Benchmark: Generate high-TPS data, then run single vs distributed benchmark
#
# Usage:
#   ./scripts/run_burst_benchmark.sh [BURST_TPS] [BURST_MINUTES]
#
# Defaults: 1000 TPS for 30 minutes

set -euo pipefail

BURST_TPS=${1:-1000}
BURST_MINUTES=${2:-30}
BURST_SECONDS=$((BURST_MINUTES * 60))

echo "=============================================="
echo "  Spark Distributed Benchmark"
echo "  Burst: ${BURST_TPS} TPS for ${BURST_MINUTES} min"
echo "=============================================="

# 1. Start Burst mode
echo "[1/4] Starting burst mode (${BURST_TPS} TPS)..."
docker exec jdp-kafka kafka-console-producer \
  --broker-list localhost:9092 \
  --topic generator-config \
  <<< "{\"base_tps\": ${BURST_TPS}, \"mode\": \"sale\"}"

echo "  Burst started. Waiting ${BURST_MINUTES} minutes for data accumulation..."
sleep "${BURST_SECONDS}"

# 2. Stop Burst mode
echo "[2/4] Stopping burst mode (back to 100 TPS)..."
docker exec jdp-kafka kafka-console-producer \
  --broker-list localhost:9092 \
  --topic generator-config \
  <<< '{"base_tps": 100, "mode": "normal"}'

echo "  Waiting 60s for streaming to flush remaining data..."
sleep 60

# 3. Trigger benchmark DAG
echo "[3/4] Triggering benchmark DAG..."
docker exec jdp-airflow airflow dags trigger benchmark_distributed

# 4. Monitor
echo "[4/4] Benchmark triggered. Monitor progress at:"
echo "  Airflow: http://localhost:8080/dags/benchmark_distributed"
echo "  Spark UI: http://localhost:8081"
echo ""
echo "After completion, check results:"
echo "  docker exec jdp-airflow airflow tasks logs benchmark_distributed benchmark_single latest"
echo "  docker exec jdp-airflow airflow tasks logs benchmark_distributed benchmark_multi latest"
echo ""
echo "Or query Postgres:"
echo "  SELECT config_name, partitions, executor_count, total_cores, row_count,"
echo "         aggregation_sec, window_function_sec, join_sec, basket_prep_sec"
echo "  FROM spark_benchmark_results ORDER BY created_at DESC;"
