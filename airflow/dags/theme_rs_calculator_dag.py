"""
Theme RS Calculator DAG
- Runs every 10 minutes
- Calculates Theme Relative Strength (RS) snapshots
- Saves to theme_rs_snapshot table
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import logging

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

def calculate_theme_rs(**context):
    """
    Calculate RS scores for all themes and insert into snapshot table.
    """
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    try:
        # Calculate RS using market_snapshot (complete coin list)
        query = """
            WITH latest_prices AS (
                SELECT 
                    symbol,
                    change_pct_24h
                FROM market_snapshot
            ),
            market_avg AS (
                SELECT COALESCE(AVG(change_pct_24h), 0) as avg_pct
                FROM latest_prices
            ),
            theme_stats AS (
                SELECT
                    t.theme_id,
                    t.theme_name,
                    t.exclude_from_rs,
                    COUNT(lp.symbol) as coin_count,
                    ROUND(AVG(COALESCE(lp.change_pct_24h, 0))::numeric, 2) as avg_change_pct,
                    MAX(lp.change_pct_24h) as best_pct,
                    (ARRAY_AGG(lp.symbol ORDER BY lp.change_pct_24h DESC NULLS LAST))[1] as top_coin,
                    MAX(lp.change_pct_24h) as top_coin_pct
                FROM theme_master t
                LEFT JOIN coin_theme_mapping c USING(theme_id)
                LEFT JOIN latest_prices lp ON lp.symbol = c.symbol || 'USDT'
                WHERE t.exclude_from_rs = FALSE
                GROUP BY t.theme_id, t.theme_name, t.exclude_from_rs
            )
            INSERT INTO theme_rs_snapshot (
                snapshot_time, theme_id, avg_change_pct, market_avg_pct, 
                rs_score, coin_count, top_coin, top_coin_pct
            )
            SELECT
                NOW(),
                ts.theme_id,
                ts.avg_change_pct,
                ROUND(ma.avg_pct::numeric, 2),
                CASE
                    WHEN ma.avg_pct = 0 THEN 1.0
                    WHEN ts.avg_change_pct IS NULL THEN 0.0
                    ELSE ROUND((ts.avg_change_pct / ma.avg_pct)::numeric, 2)
                END as rs_score,
                ts.coin_count,
                ts.top_coin,
                ts.top_coin_pct
            FROM theme_stats ts
            CROSS JOIN market_avg ma
        """
        
        cur.execute(query)
        conn.commit()
        logging.info("Theme RS snapshot calculated and saved.")

    except Exception as e:
        logging.error(f"Failed to calculate Theme RS: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

with DAG(
    "theme_rs_calculator",
    default_args=default_args,
    description="Calculate Theme RS snapshots every 10 minutes",
    schedule_interval="*/10 * * * *",
    catchup=False,
    tags=["theme", "analysis"],
) as dag:

    calc_task = PythonOperator(
        task_id="calculate_theme_rs",
        python_callable=calculate_theme_rs,
    )
