from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

LAPTOP_IP = os.getenv("LAPTOP_IP", "postgres")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")

S3A_CONF = (
    f"--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 "
    f"--conf spark.hadoop.fs.s3a.access.key={MINIO_ACCESS_KEY} "
    f"--conf spark.hadoop.fs.s3a.secret.key={MINIO_SECRET_KEY} "
    f"--conf spark.hadoop.fs.s3a.path.style.access=true "
    f"--conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem"
)

with DAG(
    'benchmark_distributed',
    default_args=default_args,
    description='Spark Distributed Processing Benchmark (Single vs Multi executor)',
    schedule_interval=None,
    catchup=False,
    tags=['benchmark', 'spark'],
) as dag:

    # Task 1: Single executor baseline
    single_executor = BashOperator(
        task_id='benchmark_single',
        bash_command=f'''
            docker exec -e DB_HOST={LAPTOP_IP} -e BENCHMARK_CONFIG=single spark-master \
            /opt/spark/bin/spark-submit \
            --master spark://spark-master:7077 \
            --conf spark.cores.max=1 \
            --conf spark.executor.cores=1 \
            --conf spark.driver.memory=1g \
            --conf spark.executor.memory=1g \
            --conf spark.sql.shuffle.partitions=1 \
            --conf spark.sql.adaptive.enabled=false \
            {S3A_CONF} \
            --name Benchmark-Single \
            /app/jobs/benchmark_distributed.py
        ''',
        execution_timeout=timedelta(minutes=30),
    )

    # Task 2: Multi executor (distributed)
    multi_executor = BashOperator(
        task_id='benchmark_multi',
        bash_command=f'''
            docker exec -e DB_HOST={LAPTOP_IP} -e BENCHMARK_CONFIG=multi spark-master \
            /opt/spark/bin/spark-submit \
            --master spark://spark-master:7077 \
            --conf spark.cores.max=4 \
            --conf spark.executor.cores=2 \
            --conf spark.driver.memory=1g \
            --conf spark.executor.memory=1536m \
            --conf spark.sql.shuffle.partitions=8 \
            --conf spark.sql.adaptive.enabled=true \
            --conf spark.sql.adaptive.skewJoin.enabled=true \
            {S3A_CONF} \
            --name Benchmark-Multi \
            /app/jobs/benchmark_distributed.py
        ''',
        execution_timeout=timedelta(minutes=30),
    )

    single_executor >> multi_executor
