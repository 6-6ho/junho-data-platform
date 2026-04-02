"""
Trade Historical Lake DAG

Daily at 07:00 UTC (16:00 KST) — trade_performance_analysis(09:00) + DQ scoring(15:00) 이후.
Postgres 서빙 테이블 → Iceberg 히스토리컬 아카이브.

Iceberg tables:
  iceberg.trade.market_history    — 전종목 가격 일일 스냅샷
  iceberg.trade.movers_history    — 급등/급락 신호 아카이브
  iceberg.trade.dq_history        — DQ 심볼별 시간 집계 아카이브
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

SPARK_SUBMIT_CMD = f"""
docker exec -e DB_HOST=postgres jdp-trade-spark /opt/spark/bin/spark-submit \
  --master local[2] \
  --conf spark.driver.memory=512m \
  --conf spark.sql.shuffle.partitions=6 \
  --conf spark.sql.adaptive.enabled=true \
  --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
  --conf spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog \
  --conf spark.sql.catalog.iceberg.type=hadoop \
  --conf "spark.sql.catalog.iceberg.warehouse=s3a://iceberg-warehouse/data/" \
  --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
  --conf spark.hadoop.fs.s3a.access.key={MINIO_ACCESS_KEY} \
  --conf spark.hadoop.fs.s3a.secret.key={MINIO_SECRET_KEY} \
  --conf spark.hadoop.fs.s3a.path.style.access=true \
  --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
  --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.7.4 \
  /app/jobs/trade/export_trade_lake.py \
  --target-date {{{{ ds }}}}
"""

with DAG(
    'trade_lake',
    default_args=default_args,
    description='Trade 히스토리컬 데이터 → Iceberg 아카이브',
    schedule='0 7 * * *',
    catchup=False,
    tags=['trade', 'lake', 'iceberg'],
) as dag:

    export = BashOperator(
        task_id='export_to_iceberg_lake',
        bash_command=SPARK_SUBMIT_CMD,
    )
