#!/bin/bash
# Shop Streaming Job - 데스크탑에서 실행
# Sales, Brand, Funnel, KPI + Iceberg

echo "=============================================="
echo "Starting Shop Streaming (Desktop Node)"
echo "Sales, Brand, Funnel, KPI + Iceberg"
echo "=============================================="

spark-submit \
  --master ${SPARK_MASTER_URL:-"local[*]"} \
  --deploy-mode client \
  --conf spark.cores.max=2 \
  --conf spark.executor.memory=2g \
  --conf spark.driver.memory=1g \
  --conf spark.scheduler.mode=FAIR \
  --conf spark.sql.shuffle.partitions=4 \
  --conf spark.streaming.kafka.maxRatePerPartition=100 \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.my_catalog=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.my_catalog.type=hadoop \
  --conf spark.sql.catalog.my_catalog.warehouse=s3a://iceberg-warehouse/ \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key=minio \
  --conf spark.hadoop.fs.s3a.secret.key=${MINIO_SECRET_KEY:-minio123} \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --conf spark.hadoop.fs.s3a.connection.ssl.enabled=false \
  jobs/shop_streaming.py
