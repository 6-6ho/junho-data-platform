from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime, timedelta

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

    expand_products = KubernetesPodOperator(
        task_id='expand_products_faker',
        name='product-expansion',
        namespace='shop',
        image='registry.local:5000/jdp/shop-backend:latest',
        cmds=['python3'],
        arguments=['/app/expand_products_faker.py'],
        node_selector={'role': 'worker'},
        env_vars={
            'DB_HOST': 'postgres.database.svc',
            'DB_PORT': '5432',
            'DB_NAME': 'app',
            'POSTGRES_USER': 'postgres',
        },
        is_delete_operator_pod=True,
        get_logs=True,
    )
