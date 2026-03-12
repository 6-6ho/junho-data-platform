from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from datetime import datetime, timedelta

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

SPARK_IMAGE = "registry.local:5000/jdp/spark:latest"

# MinIO credentials — K8s Secret → Pod env vars (로그/describe에 노출 안 됨)
MINIO_SECRETS = [
    Secret('env', 'AWS_ACCESS_KEY_ID', 'minio-secret', 'MINIO_ACCESS_KEY'),
    Secret('env', 'AWS_SECRET_ACCESS_KEY', 'minio-secret', 'MINIO_SECRET_KEY'),
]

with DAG(
    'basket_analysis_dag',
    default_args=default_args,
    description='Run Spark Basket Analysis (FPGrowth)',
    schedule_interval='0 3 * * *',  # Daily at 03:00 UTC (12:00 KST)
    catchup=False,
    tags=['shop', 'analysis', 'spark'],
) as dag:

    submit_job = KubernetesPodOperator(
        task_id='run_basket_analysis',
        name='basket-analysis',
        namespace='data',
        image=SPARK_IMAGE,
        cmds=['spark-submit'],
        arguments=[
            '--master', 'k8s://https://kubernetes.default.svc:443',
            '--deploy-mode', 'client',
            '--conf', f'spark.kubernetes.container.image={SPARK_IMAGE}',
            '--conf', 'spark.kubernetes.namespace=data',
            '--conf', 'spark.executor.instances=2',
            '--conf', 'spark.cores.max=3',
            '--conf', 'spark.executor.cores=1',
            '--conf', 'spark.driver.memory=1g',
            '--conf', 'spark.executor.memory=1g',
            '--conf', 'spark.sql.shuffle.partitions=6',
            '--conf', 'spark.sql.adaptive.enabled=true',
            '--conf', 'spark.sql.adaptive.skewJoin.enabled=true',
            '--conf', 'spark.kubernetes.node.selector.role=worker',
            '--conf', 'spark.hadoop.fs.s3a.endpoint=http://minio.data.svc:9000',
            '--conf', 'spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.EnvironmentVariableCredentialsProvider',
            '--conf', 'spark.hadoop.fs.s3a.path.style.access=true',
            '--conf', 'spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem',
            '--name', 'BasketAnalysis',
            '--verbose',
            '/app/jobs/batch_product_affinity.py', '--target-date', '{{ ds }}'
        ],
        service_account_name='spark',
        node_selector={'role': 'worker'},
        env_vars={
            'DB_HOST': 'postgres.database.svc',
            'DB_PORT': '5432',
            'DB_NAME': 'app',
            'POSTGRES_USER': 'postgres',
        },
        secrets=MINIO_SECRETS,
        is_delete_operator_pod=True,
        get_logs=True,
    )
