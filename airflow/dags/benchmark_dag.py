from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.cncf.kubernetes.secret import Secret
from datetime import datetime, timedelta

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

SPARK_IMAGE = "registry.local:5000/jdp/spark:latest"

# MinIO credentials — K8s Secret → Pod env vars (로그/describe에 노출 안 됨)
MINIO_SECRETS = [
    Secret('env', 'AWS_ACCESS_KEY_ID', 'minio-secret', 'MINIO_ACCESS_KEY'),
    Secret('env', 'AWS_SECRET_ACCESS_KEY', 'minio-secret', 'MINIO_SECRET_KEY'),
]

S3A_ARGS = [
    '--conf', 'spark.hadoop.fs.s3a.endpoint=http://minio.data.svc:9000',
    '--conf', 'spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.EnvironmentVariableCredentialsProvider',
    '--conf', 'spark.hadoop.fs.s3a.path.style.access=true',
    '--conf', 'spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem',
]

COMMON_ENV = {
    'DB_HOST': 'postgres.database.svc',
    'DB_PORT': '5432',
    'DB_NAME': 'app',
    'POSTGRES_USER': 'postgres',
}

with DAG(
    'benchmark_distributed',
    default_args=default_args,
    description='Spark Distributed Processing Benchmark (Single vs Multi executor)',
    schedule_interval=None,
    catchup=False,
    tags=['benchmark', 'spark'],
) as dag:

    # Task 1: Single executor baseline
    single_executor = KubernetesPodOperator(
        task_id='benchmark_single',
        name='benchmark-single',
        namespace='data',
        image=SPARK_IMAGE,
        cmds=['spark-submit'],
        arguments=[
            '--master', 'k8s://https://kubernetes.default.svc:443',
            '--deploy-mode', 'client',
            '--conf', f'spark.kubernetes.container.image={SPARK_IMAGE}',
            '--conf', 'spark.kubernetes.namespace=data',
            '--conf', 'spark.executor.instances=1',
            '--conf', 'spark.cores.max=1',
            '--conf', 'spark.executor.cores=1',
            '--conf', 'spark.driver.memory=1g',
            '--conf', 'spark.executor.memory=1g',
            '--conf', 'spark.sql.shuffle.partitions=1',
            '--conf', 'spark.sql.adaptive.enabled=false',
            '--conf', 'spark.kubernetes.node.selector.role=worker',
        ] + S3A_ARGS + [
            '--name', 'Benchmark-Single',
            '/app/jobs/benchmark_distributed.py',
        ],
        service_account_name='spark',
        node_selector={'role': 'worker'},
        env_vars={**COMMON_ENV, 'BENCHMARK_CONFIG': 'single'},
        secrets=MINIO_SECRETS,
        is_delete_operator_pod=True,
        get_logs=True,
        execution_timeout=timedelta(minutes=30),
    )

    # Task 2: Multi executor (distributed)
    multi_executor = KubernetesPodOperator(
        task_id='benchmark_multi',
        name='benchmark-multi',
        namespace='data',
        image=SPARK_IMAGE,
        cmds=['spark-submit'],
        arguments=[
            '--master', 'k8s://https://kubernetes.default.svc:443',
            '--deploy-mode', 'client',
            '--conf', f'spark.kubernetes.container.image={SPARK_IMAGE}',
            '--conf', 'spark.kubernetes.namespace=data',
            '--conf', 'spark.executor.instances=2',
            '--conf', 'spark.cores.max=4',
            '--conf', 'spark.executor.cores=2',
            '--conf', 'spark.driver.memory=1g',
            '--conf', 'spark.executor.memory=1536m',
            '--conf', 'spark.sql.shuffle.partitions=8',
            '--conf', 'spark.sql.adaptive.enabled=true',
            '--conf', 'spark.sql.adaptive.skewJoin.enabled=true',
            '--conf', 'spark.kubernetes.node.selector.role=worker',
        ] + S3A_ARGS + [
            '--name', 'Benchmark-Multi',
            '/app/jobs/benchmark_distributed.py',
        ],
        service_account_name='spark',
        node_selector={'role': 'worker'},
        env_vars={**COMMON_ENV, 'BENCHMARK_CONFIG': 'multi'},
        secrets=MINIO_SECRETS,
        is_delete_operator_pod=True,
        get_logs=True,
        execution_timeout=timedelta(minutes=30),
    )

    single_executor >> multi_executor
