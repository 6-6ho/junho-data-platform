"""
DQ Scoring DAG

Daily at 05:00 UTC (14:00 KST).
3 sequential tasks:
  1. compute_dq_score — completeness, validity, timeliness → dq_daily_score
  2. detect_anomalies — 7-day avg drop detection → dq_anomaly_log
  3. reconcile — category_hourly vs payment_hourly cross-check → dq_anomaly_log
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os

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


def compute_dq_score(**ctx):
    """
    Completeness: 5 categories × 24 hour slots = 120 expected.
                  Score = (actual slots / 120) × 100
    Validity: anomaly_raw count in last 24h.
              Score = max(0, 100 - anomaly_count × 2)
    Timeliness: check if latest dq_category_hourly row is within 2 hours.
              Score = 100 if within, else 100 - (hours_late × 10)
    Total: weighted average (completeness 40%, validity 30%, timeliness 30%)
    """
    conn = _get_conn()
    cur = conn.cursor()

    target_ts = ctx['logical_date']
    target_date = target_ts.date()

    # --- Completeness ---
    cur.execute("""
        SELECT COUNT(DISTINCT (category, date_trunc('hour', hour)))
        FROM dq_category_hourly
        WHERE hour >= %s::timestamp - INTERVAL '24 hours'
          AND hour < %s::timestamp
    """, (target_ts, target_ts))
    actual_slots = cur.fetchone()[0] or 0
    expected_slots = 5 * 24  # 5 categories × 24 hours
    completeness = min(100, round(actual_slots / expected_slots * 100))

    # --- Validity ---
    cur.execute("""
        SELECT COUNT(*) FROM dq_anomaly_raw
        WHERE detected_at >= %s::timestamp - INTERVAL '24 hours'
          AND detected_at < %s::timestamp
    """, (target_ts, target_ts))
    anomaly_count = cur.fetchone()[0] or 0
    validity = max(0, 100 - anomaly_count * 2)

    # --- Timeliness ---
    cur.execute("""
        SELECT EXTRACT(EPOCH FROM (%s::timestamp - MAX(created_at))) / 3600
        FROM dq_category_hourly
    """, (target_ts,))
    row = cur.fetchone()
    hours_late = row[0] if row and row[0] else 0
    if hours_late <= 2:
        timeliness = 100
    else:
        timeliness = max(0, round(100 - (hours_late - 2) * 10))

    total = round(completeness * 0.4 + validity * 0.3 + timeliness * 0.3)

    # Count anomalies by severity
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE severity = 'critical') AS critical_count,
            COUNT(*) FILTER (WHERE severity = 'warning') AS warning_count
        FROM dq_anomaly_log
        WHERE detected_at::date = %s
    """, (target_date,))
    sev = cur.fetchone()
    critical_count = sev[0] if sev else 0
    warning_count = sev[1] if sev else 0

    cur.execute("""
        INSERT INTO dq_daily_score (date, completeness_score, validity_score, timeliness_score,
            total_score, critical_count, warning_count, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            completeness_score = EXCLUDED.completeness_score,
            validity_score = EXCLUDED.validity_score,
            timeliness_score = EXCLUDED.timeliness_score,
            total_score = EXCLUDED.total_score,
            critical_count = EXCLUDED.critical_count,
            warning_count = EXCLUDED.warning_count,
            updated_at = %s
    """, (target_date, completeness, validity, timeliness, total, critical_count, warning_count,
          target_ts, target_ts))
    conn.commit()

    print(f"DQ Score [{target_date}] completeness={completeness} validity={validity} "
          f"timeliness={timeliness} total={total}")

    cur.close()
    conn.close()


def detect_anomalies(**ctx):
    """
    Compare each category's last-hour event_count against its 7-day hourly average.
    If actual < 30% of avg → log 'category_drop' (critical).
    Same for payment_method → 'payment_drop'.
    """
    conn = _get_conn()
    cur = conn.cursor()

    target_ts = ctx['logical_date']

    # Category drop detection
    cur.execute("""
        WITH recent AS (
            SELECT category, event_count
            FROM dq_category_hourly
            WHERE hour = date_trunc('hour', %s::timestamp - INTERVAL '1 hour')
        ),
        avg7d AS (
            SELECT category, AVG(event_count) AS avg_count
            FROM dq_category_hourly
            WHERE hour >= %s::timestamp - INTERVAL '7 days'
              AND hour < %s::timestamp
            GROUP BY category
        )
        SELECT r.category, a.avg_count, r.event_count
        FROM recent r
        JOIN avg7d a ON r.category = a.category
        WHERE a.avg_count > 0 AND r.event_count < a.avg_count * 0.3
    """, (target_ts, target_ts, target_ts))
    for row in cur.fetchall():
        cat, avg_val, actual = row
        cur.execute("""
            INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity)
            VALUES ('category_drop', %s, %s, %s, 'critical')
        """, (cat, round(avg_val, 2), actual))
        print(f"[ANOMALY] category_drop: {cat}, expected={avg_val:.0f}, actual={actual}")

    # Payment drop detection
    cur.execute("""
        WITH recent AS (
            SELECT payment_method, purchase_count
            FROM dq_payment_hourly
            WHERE hour = date_trunc('hour', %s::timestamp - INTERVAL '1 hour')
        ),
        avg7d AS (
            SELECT payment_method, AVG(purchase_count) AS avg_count
            FROM dq_payment_hourly
            WHERE hour >= %s::timestamp - INTERVAL '7 days'
              AND hour < %s::timestamp
            GROUP BY payment_method
        )
        SELECT r.payment_method, a.avg_count, r.purchase_count
        FROM recent r
        JOIN avg7d a ON r.payment_method = a.payment_method
        WHERE a.avg_count > 0 AND r.purchase_count < a.avg_count * 0.3
    """, (target_ts, target_ts, target_ts))
    for row in cur.fetchall():
        pm, avg_val, actual = row
        cur.execute("""
            INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity)
            VALUES ('payment_drop', %s, %s, %s, 'critical')
        """, (pm, round(avg_val, 2), actual))
        print(f"[ANOMALY] payment_drop: {pm}, expected={avg_val:.0f}, actual={actual}")

    # Price anomaly count check
    cur.execute("""
        SELECT COUNT(*) FROM dq_anomaly_raw
        WHERE detected_at >= %s::timestamp - INTERVAL '1 hour'
          AND detected_at < %s::timestamp
    """, (target_ts, target_ts))
    price_anomaly_count = cur.fetchone()[0] or 0
    if price_anomaly_count > 10:
        cur.execute("""
            INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity)
            VALUES ('abnormal_price_spike', 'price', 0, %s, 'warning')
        """, (price_anomaly_count,))
        print(f"[ANOMALY] abnormal_price_spike: {price_anomaly_count} quarantined in last hour")

    conn.commit()
    cur.close()
    conn.close()


def reconcile(**ctx):
    """
    Cross-check: dq_category_hourly vs dq_payment_hourly.
    Both are tumbling 1h windows from the same Kafka source.
    SUM(purchase_count) per hour should match across both tables.
    If difference > 5% → log as 'reconciliation_mismatch'.
    """
    conn = _get_conn()
    cur = conn.cursor()

    target_ts = ctx['logical_date']

    cur.execute("""
        WITH cat AS (
            SELECT hour, SUM(purchase_count) AS total
            FROM dq_category_hourly
            WHERE hour >= %s::timestamp - INTERVAL '24 hours'
              AND hour < %s::timestamp
            GROUP BY hour
        ),
        pay AS (
            SELECT hour, SUM(purchase_count) AS total
            FROM dq_payment_hourly
            WHERE hour >= %s::timestamp - INTERVAL '24 hours'
              AND hour < %s::timestamp
            GROUP BY hour
        )
        SELECT
            COALESCE(c.hour, p.hour) AS hour,
            COALESCE(c.total, 0) AS category_total,
            COALESCE(p.total, 0) AS payment_total
        FROM cat c
        FULL OUTER JOIN pay p ON c.hour = p.hour
    """, (target_ts, target_ts, target_ts, target_ts))

    mismatch_count = 0
    for row in cur.fetchall():
        hr, cat_total, pay_total = row
        if cat_total == 0 and pay_total == 0:
            continue
        base = max(cat_total, pay_total, 1)
        diff_pct = abs(cat_total - pay_total) / base * 100

        if diff_pct > 5:
            severity = 'critical' if diff_pct > 20 else 'warning'
            cur.execute("""
                INSERT INTO dq_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity, notes)
                VALUES ('reconciliation_mismatch', 'consistency', %s, %s, %s, %s)
            """, (round(float(cat_total), 2), round(float(pay_total), 2), severity,
                  f"hour={hr}, diff={diff_pct:.1f}%"))
            mismatch_count += 1

    conn.commit()
    print(f"Reconciliation complete. {mismatch_count} mismatches found.")
    cur.close()
    conn.close()


with DAG(
    'dq_scoring_dag',
    default_args=default_args,
    description='Daily DQ scoring, anomaly detection, and reconciliation',
    schedule_interval='0 5 * * *',  # Daily at 05:00 UTC (14:00 KST)
    catchup=False,
    tags=['shop', 'dq', 'quality'],
) as dag:

    t1 = PythonOperator(
        task_id='compute_dq_score',
        python_callable=compute_dq_score,
    )

    t2 = PythonOperator(
        task_id='detect_anomalies',
        python_callable=detect_anomalies,
    )

    t3 = PythonOperator(
        task_id='reconcile',
        python_callable=reconcile,
    )

    t1 >> t2 >> t3
