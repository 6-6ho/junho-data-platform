from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

DB_HOST = os.getenv("DB_HOST", "postgres")

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'product_expansion_dag',
    default_args=default_args,
    description='Expand product catalog daily using Faker',
    schedule_interval='0 4 * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['shop', 'product', 'expansion'],
) as dag:

    expand_products = BashOperator(
        task_id='expand_products_faker',
        bash_command=f'docker exec -e DB_HOST={DB_HOST} jdp-shop-api python3 /app/expand_products_faker.py',
    )
