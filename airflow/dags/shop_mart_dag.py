"""
Shop Mart Build DAG

Daily at 06:00 UTC (15:00 KST).
Speed Layer(shop_hourly_sales_log, shop_funnel_stats_log) → Mart Tables 집계.

Tasks:
  1. build_daily_sales — shop_hourly_sales_log → mart_daily_sales
  2. build_daily_summary — mart_daily_sales → mart_daily_summary
  3. build_weekly_sales — shop_hourly_sales_log → mart_weekly_sales
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def _get_conn():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("LAPTOP_IP", "postgres"),
        port=5432,
        database="app",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def build_daily_sales(**ctx):
    """shop_hourly_sales_log → mart_daily_sales (최근 7일)"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mart_daily_sales (date, category, total_revenue, order_count, avg_order_value)
            SELECT
                DATE(window_start) as date,
                category,
                SUM(total_revenue) as total_revenue,
                SUM(order_count) as order_count,
                CASE WHEN SUM(order_count) > 0
                     THEN SUM(total_revenue) / SUM(order_count)
                     ELSE 0 END as avg_order_value
            FROM shop_hourly_sales_log
            WHERE window_start >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(window_start), category
            ON CONFLICT (date, category) DO UPDATE SET
                total_revenue = EXCLUDED.total_revenue,
                order_count = EXCLUDED.order_count,
                avg_order_value = EXCLUDED.avg_order_value,
                created_at = NOW()
        """)
        conn.commit()
        logger.info(f"mart_daily_sales: {cur.rowcount} rows upserted")
        cur.close()
    finally:
        conn.close()


def build_daily_summary(**ctx):
    """mart_daily_sales → mart_daily_summary (최근 7일)"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mart_daily_summary (date, total_revenue, total_orders, avg_order_value, top_category)
            SELECT
                date,
                SUM(total_revenue) as total_revenue,
                SUM(order_count) as total_orders,
                CASE WHEN SUM(order_count) > 0
                     THEN SUM(total_revenue) / SUM(order_count)
                     ELSE 0 END as avg_order_value,
                (SELECT category FROM mart_daily_sales ds2
                 WHERE ds2.date = ds.date
                 ORDER BY total_revenue DESC LIMIT 1) as top_category
            FROM mart_daily_sales ds
            WHERE date >= NOW() - INTERVAL '7 days'
            GROUP BY date
            ON CONFLICT (date) DO UPDATE SET
                total_revenue = EXCLUDED.total_revenue,
                total_orders = EXCLUDED.total_orders,
                avg_order_value = EXCLUDED.avg_order_value,
                top_category = EXCLUDED.top_category,
                created_at = NOW()
        """)
        conn.commit()
        logger.info(f"mart_daily_summary: {cur.rowcount} rows upserted")
        cur.close()
    finally:
        conn.close()


def build_weekly_sales(**ctx):
    """shop_hourly_sales_log → mart_weekly_sales (최근 8주)"""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mart_weekly_sales (week_start, week_number, year, category, total_revenue, order_count, avg_daily_revenue)
            SELECT
                DATE_TRUNC('week', DATE(window_start))::DATE as week_start,
                EXTRACT(WEEK FROM window_start)::INT as week_number,
                EXTRACT(YEAR FROM window_start)::INT as year,
                category,
                SUM(total_revenue) as total_revenue,
                SUM(order_count) as order_count,
                SUM(total_revenue) / 7 as avg_daily_revenue
            FROM shop_hourly_sales_log
            WHERE window_start >= NOW() - INTERVAL '8 weeks'
            GROUP BY DATE_TRUNC('week', DATE(window_start)), EXTRACT(WEEK FROM window_start), EXTRACT(YEAR FROM window_start), category
            ON CONFLICT (week_start, category) DO UPDATE SET
                total_revenue = EXCLUDED.total_revenue,
                order_count = EXCLUDED.order_count,
                avg_daily_revenue = EXCLUDED.avg_daily_revenue,
                week_number = EXCLUDED.week_number,
                year = EXCLUDED.year,
                created_at = NOW()
        """)
        conn.commit()
        logger.info(f"mart_weekly_sales: {cur.rowcount} rows upserted")
        cur.close()
    finally:
        conn.close()


with DAG(
    dag_id='shop_mart_build',
    default_args=default_args,
    schedule='0 6 * * *',  # 매일 06:00 UTC (15:00 KST)
    catchup=False,
    max_active_runs=1,
    tags=['shop', 'mart', 'batch'],
) as dag:
    t1 = PythonOperator(task_id='build_daily_sales', python_callable=build_daily_sales)
    t2 = PythonOperator(task_id='build_daily_summary', python_callable=build_daily_summary)
    t3 = PythonOperator(task_id='build_weekly_sales', python_callable=build_weekly_sales)

    t1 >> t2  # daily_summary depends on daily_sales
    [t1, t3]  # daily_sales and weekly_sales can run in parallel
