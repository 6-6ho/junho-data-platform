#!/bin/bash
# Trade Streaming Job - 노트북에서 실행
# Movers 5m/10m + Alerts

echo "=============================================="
echo "Starting Trade Streaming (Laptop Node)"
echo "Movers 5m, 10m, Alerts"
echo "=============================================="

spark-submit \
  --master ${SPARK_MASTER_URL:-"local[*]"} \
  --deploy-mode client \
  --conf spark.cores.max=1 \
  --conf spark.executor.memory=512m \
  --conf spark.driver.memory=512m \
  --conf spark.scheduler.mode=FAIR \
  --conf spark.sql.shuffle.partitions=4 \
  --conf spark.streaming.kafka.maxRatePerPartition=50 \
  jobs/trade_streaming.py
