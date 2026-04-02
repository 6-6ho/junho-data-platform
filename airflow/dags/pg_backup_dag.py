"""
Postgres Backup DAG

매일 04:00 UTC (13:00 KST) — pg_dump → gzip → MinIO 업로드.
7일 이상 된 백업 자동 삭제.
"""
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

LAPTOP_IP = os.getenv("LAPTOP_IP", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'pg_backup',
    default_args=default_args,
    description='Postgres 일일 백업 → MinIO',
    schedule='0 4 * * *',
    catchup=False,
    tags=['infra', 'backup'],
) as dag:

    backup = BashOperator(
        task_id='pg_dump_to_minio',
        bash_command=f"""
            BACKUP_FILE="/tmp/app_{{{{ ds_nodash }}}}.sql.gz"
            PGPASSWORD={PG_PASSWORD} pg_dump -h {LAPTOP_IP} -U postgres app | gzip > $BACKUP_FILE
            mc alias set myminio http://minio:9000 ${{MINIO_ROOT_USER:-minio}} ${{MINIO_ROOT_PASSWORD:-minio1215}}
            mc mb myminio/backups --ignore-existing
            mc cp $BACKUP_FILE myminio/backups/
            rm -f $BACKUP_FILE
            echo "Backup uploaded: app_{{{{ ds_nodash }}}}.sql.gz"
        """,
    )

    cleanup = BashOperator(
        task_id='cleanup_old_backups',
        bash_command=f"""
            mc alias set myminio http://minio:9000 ${{MINIO_ROOT_USER:-minio}} ${{MINIO_ROOT_PASSWORD:-minio1215}}
            mc rm --older-than 7d myminio/backups/ --force 2>/dev/null || true
            echo "Old backups cleaned"
        """,
    )

    backup >> cleanup
