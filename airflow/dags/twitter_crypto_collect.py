"""
Twitter 크립토 멘션 수집 DAG
매시간 실행하여 트위터 데이터를 MinIO에 저장
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'twitter_crypto_collect',
    default_args=default_args,
    description='Collect crypto mentions from Twitter',
    schedule_interval='@hourly',
    catchup=False,
    tags=['twitter', 'crypto', 'data-lake'],
)

# Task 1: Collect Twitter Data
collect_task = BashOperator(
    task_id='collect_twitter_data',
    bash_command='python /opt/airflow/scripts/collect_twitter.py',
    dag=dag,
)

# Task 2: Trigger Spark Job to process and store in Iceberg
spark_job = BashOperator(
    task_id='process_to_iceberg',
    bash_command='''
    curl -X POST http://spark:4040/api/v1/applications \
      -H "Content-Type: application/json" \
      -d '{"job": "twitter_iceberg_job"}'
    ''',
    dag=dag,
)

collect_task >> spark_job
