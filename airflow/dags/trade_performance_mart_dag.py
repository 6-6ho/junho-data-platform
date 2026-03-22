"""
Trade Performance Mart DAG
- Runs daily at 00:30 UTC (09:30 KST), after trade_performance_analysis (00:00 UTC)
- Phase 2: Spark reads Iceberg flat tables → writes Postgres mart
- mart_trade_signal_detail: per-signal metrics (profit targets, drawdown)
- mart_trade_strategy_result: per-signal x TP/SL simulation results
- mart_trade_time_performance: daily x tier x minute aggregation
- mart_signal_validation_daily: DQ stats from signal_validation_log (PythonOperator, no JSONB)
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import os

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

LAPTOP_IP = os.getenv("LAPTOP_IP", "postgres")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")


def build_validation_stats(**context):
    """Build mart_signal_validation_daily from signal_validation_log.

    Kept as PythonOperator — no JSONB, no Iceberg needed.
    """
    ds = context.get("ds")
    conf = context.get("dag_run").conf or {}
    backfill = conf.get("backfill", False)

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    if backfill:
        date_filter = "TRUE"
    else:
        date_filter = "validated_at::date = %s"

    query = f"""
        INSERT INTO mart_signal_validation_daily
            (date, total_samples, pass_count, fail_count, error_count,
             pass_rate, avg_diff_pct, max_diff_pct, data_quality_score)
        SELECT
            validated_at::date AS date,
            COUNT(*) AS total_samples,
            COUNT(*) FILTER (WHERE status = 'pass') AS pass_count,
            COUNT(*) FILTER (WHERE status = 'fail') AS fail_count,
            COUNT(*) FILTER (WHERE status = 'error') AS error_count,
            ROUND((COUNT(*) FILTER (WHERE status = 'pass'))::numeric
                  / NULLIF(COUNT(*), 0) * 100, 2) AS pass_rate,
            ROUND(AVG(ABS(diff_pct))::numeric, 4) AS avg_diff_pct,
            ROUND(MAX(ABS(diff_pct))::numeric, 4) AS max_diff_pct,
            ROUND(
                (COUNT(*) FILTER (WHERE status = 'pass'))::numeric
                / NULLIF(COUNT(*), 0) * 70
                + GREATEST(0, 100 - COALESCE(AVG(ABS(diff_pct)), 0) * 10)::numeric
                / 100 * 30
            , 2) AS data_quality_score
        FROM signal_validation_log
        WHERE {date_filter}
        GROUP BY validated_at::date
        ON CONFLICT (date) DO UPDATE SET
            total_samples = EXCLUDED.total_samples,
            pass_count = EXCLUDED.pass_count,
            fail_count = EXCLUDED.fail_count,
            error_count = EXCLUDED.error_count,
            pass_rate = EXCLUDED.pass_rate,
            avg_diff_pct = EXCLUDED.avg_diff_pct,
            max_diff_pct = EXCLUDED.max_diff_pct,
            data_quality_score = EXCLUDED.data_quality_score,
            created_at = NOW()
    """
    params = () if backfill else (ds,)
    cur.execute(query, params)

    conn.commit()
    print(f"Built validation_daily (backfill={backfill})")
    cur.close()
    conn.close()


with DAG(
    "trade_performance_mart",
    default_args=default_args,
    description="Build trade performance mart from Iceberg flat tables",
    schedule_interval="30 0 * * *",  # 00:30 UTC = 09:30 KST
    catchup=True,
    tags=["trade", "mart", "spark"],
) as dag:

    build_mart = BashOperator(
        task_id='build_trade_mart',
        bash_command=f'''
            docker exec -e DB_HOST={LAPTOP_IP} spark-master /opt/spark/bin/spark-submit \
            --master spark://spark-master:7077 \
            --conf spark.cores.max=3 \
            --conf spark.executor.cores=1 \
            --conf spark.driver.memory=1g \
            --conf spark.executor.memory=1g \
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
            --name BuildTradeMart \
            /app/jobs/trade/build_performance_mart.py --target-date {{{{ ds }}}}
        ''',
    )

    build_validation = PythonOperator(
        task_id="build_validation_stats",
        python_callable=build_validation_stats,
    )

    build_mart >> build_validation
