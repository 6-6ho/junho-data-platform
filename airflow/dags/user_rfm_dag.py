from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'user_rfm_dag',
    default_args=default_args,
    description='Run Spark User RFM Analysis',
    schedule_interval='30 3 * * *', # Daily at 03:30 UTC (12:30 KST)
    catchup=False,
    tags=['shop', 'analysis', 'spark'],
) as dag:

    # Run Spark Job via BashOperator (Docker Exec)
    submit_job = BashOperator(
        task_id='run_user_rfm',
        bash_command='''
            docker exec -e DB_HOST=192.168.219.101 spark-master /opt/spark/bin/spark-submit \
            --master spark://spark-master:7077 \
            --conf spark.driver.memory=1g \
            --conf spark.executor.memory=1g \
            --conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
            --conf spark.hadoop.fs.s3a.access.key=minio \
            --conf spark.hadoop.fs.s3a.secret.key=minio123 \
            --conf spark.hadoop.fs.s3a.path.style.access=true \
            --conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
            --name UserRFM \
            --verbose \
            /app/jobs/batch_user_rfm.py
        '''
    )
