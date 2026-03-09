#!/bin/bash
echo "=============================================="
echo "Starting Unified Spark Streaming"
echo "3 Jobs in 1 Driver (Memory Optimized)"
echo "=============================================="

# Single spark-submit for all jobs
ICEBERG_CONF=""
if [ "$ENABLE_ICEBERG" == "true" ]; then
  echo "Enabling Iceberg/MinIO Configuration..."
  ICEBERG_CONF="--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.my_catalog=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.my_catalog.type=hadoop \
  --conf spark.sql.catalog.my_catalog.warehouse=s3a://iceberg-warehouse/data \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minio \
  --conf spark.hadoop.fs.s3a.secret.key=${MINIO_SECRET_KEY} \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false"
fi

# Single spark-submit for all jobs
spark-submit \
  --master ${SPARK_MASTER_URL:-"local[*]"} \
  --deploy-mode client \
  --conf spark.cores.max=${SPARK_CORES_MAX:-4} \
  --conf spark.executor.cores=${SPARK_EXECUTOR_CORES:-2} \
  --conf spark.executor.memory=${SPARK_EXECUTOR_MEMORY:-1536m} \
  --conf spark.driver.memory=${SPARK_DRIVER_MEMORY:-1024m} \
  --conf spark.scheduler.mode=FAIR \
  --conf spark.sql.shuffle.partitions=${SPARK_SHUFFLE_PARTITIONS:-8} \
  --conf spark.streaming.kafka.maxRatePerPartition=500 \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.adaptive.skewJoin.enabled=true \
  --conf spark.sql.adaptive.coalescePartitions.enabled=true \
  --conf spark.locality.wait=3s \
  $ICEBERG_CONF \
  jobs/${SPARK_JOB_NAME:?Set SPARK_JOB_NAME}
