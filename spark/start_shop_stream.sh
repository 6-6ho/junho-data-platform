#!/bin/bash
# Submit Shop Streaming Job to Local Spark Master (Client Mode)

export SPARK_MASTER_URL=${SPARK_MASTER_URL:-"spark://localhost:7077"}

echo "Submitting Shop Streaming Job to $SPARK_MASTER_URL..."

# Note: We need to submit from OUTSIDE the container if running on host,
# OR inside 'spark-job-runner' container.
# This script assumes it's being run where 'spark-submit' is available (e.g. inside container).

if ! command -v spark-submit &> /dev/null; then
    echo "spark-submit not found. Are you running inside spark-job-runner container?"
    exit 1
fi

spark-submit \
  --master $SPARK_MASTER_URL \
  --deploy-mode client \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.3,org.apache.hadoop:hadoop-aws:3.3.4 \
  /app/jobs/shop/streaming.py
