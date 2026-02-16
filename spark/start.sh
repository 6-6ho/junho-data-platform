#!/bin/bash
echo "=============================================="
echo "Starting Unified Spark Streaming"
echo "3 Jobs in 1 Driver (Memory Optimized)"
echo "=============================================="

# Single spark-submit for all jobs
spark-submit \
  --master ${SPARK_MASTER_URL:-"local[*]"} \
  --deploy-mode client \
  --conf spark.cores.max=1 \
  --conf spark.executor.memory=512m \
  --conf spark.driver.memory=512m \
  --conf spark.scheduler.mode=FAIR \
  --conf spark.sql.shuffle.partitions=4 \
  --conf spark.streaming.kafka.maxRatePerPartition=50 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.my_catalog=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.my_catalog.type=hadoop \
  --conf spark.sql.catalog.my_catalog.warehouse=s3a://iceberg-warehouse/data \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minio \
  --conf spark.hadoop.fs.s3a.secret.key=${MINIO_SECRET_KEY:-minio123} \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
  jobs/${SPARK_JOB_NAME:-unified_streaming.py}
