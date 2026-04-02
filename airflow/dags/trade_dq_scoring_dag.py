"""
Trade DQ Scoring DAG

Daily at 06:00 UTC (15:00 KST).
3 sequential tasks:
  1. compute_trade_dq_score — completeness, validity, timeliness → dq_trade_daily_score
  2. detect_trade_anomalies — symbol drop, price outlier spike → dq_trade_anomaly_log
  3. reconcile_trade — source_hourly vs symbol_hourly cross-check → dq_trade_anomaly_log

Shop DQ와 완전 독립. Trade(암호화폐 거래소) 데이터 품질 관리.
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


def compute_trade_dq_score(**ctx):
    """
    Completeness: distinct symbols in dq_trade_symbol_hourly / total symbols in market_snapshot
    Validity: dq_trade_anomaly_raw count in last 24h → 100 - count*2
    Timeliness: freshness of market_snapshot.event_time → 100 if <2min, else -10/min
    """
    target_date = ctx['ds']
    target_ts = f"{target_date} 00:00:00+00"
    conn = _get_conn()
    cur = conn.cursor()

    # Completeness: symbol coverage
    cur.execute("""
        SELECT COUNT(DISTINCT symbol)
        FROM dq_trade_symbol_hourly
        WHERE hour >= %s::timestamptz - INTERVAL '24 hours'
          AND hour < %s::timestamptz
    """, (target_ts, target_ts))
    actual_symbols = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(DISTINCT symbol) FROM market_snapshot")
    expected_symbols = cur.fetchone()[0] or 1

    completeness = min(100, int(actual_symbols / expected_symbols * 100))

    # Validity: anomaly count
    cur.execute("""
        SELECT COUNT(*) FROM dq_trade_anomaly_raw
        WHERE detected_at >= %s::timestamptz - INTERVAL '24 hours'
          AND detected_at < %s::timestamptz
    """, (target_ts, target_ts))
    anomaly_count = cur.fetchone()[0] or 0
    validity = max(0, 100 - anomaly_count * 2)

    # Timeliness: target_date 당일 기준으로 마지막 데이터와 해당일 자정의 차이
    # NOW() 기준이면 배치 실행 시각에 오염됨
    cur.execute("""
        SELECT EXTRACT(EPOCH FROM (
            %s::timestamptz - COALESCE(MAX(hour), %s::timestamptz - INTERVAL '24 hours')
        )) / 3600
        FROM dq_trade_symbol_hourly
        WHERE hour >= %s::timestamptz - INTERVAL '24 hours'
          AND hour < %s::timestamptz
    """, (target_ts, target_ts, target_ts, target_ts))
    row = cur.fetchone()
    hours_gap = float(row[0]) if row and row[0] else 24
    if hours_gap <= 2:
        timeliness = 100
    else:
        timeliness = max(0, int(100 - (hours_gap - 2) * 10))

    total = int(completeness * 0.4 + validity * 0.3 + timeliness * 0.3)

    # Severity counts from anomaly log
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE severity = 'critical'),
            COUNT(*) FILTER (WHERE severity = 'warning')
        FROM dq_trade_anomaly_log
        WHERE detected_at::date = %s::date
    """, (target_date,))
    sev = cur.fetchone()
    critical_count = sev[0] if sev else 0
    warning_count = sev[1] if sev else 0

    # Upsert
    cur.execute("""
        INSERT INTO dq_trade_daily_score (date, completeness_score, validity_score, timeliness_score, total_score, critical_count, warning_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            completeness_score = EXCLUDED.completeness_score,
            validity_score = EXCLUDED.validity_score,
            timeliness_score = EXCLUDED.timeliness_score,
            total_score = EXCLUDED.total_score,
            critical_count = EXCLUDED.critical_count,
            warning_count = EXCLUDED.warning_count,
            updated_at = NOW()
    """, (target_date, completeness, validity, timeliness, total, critical_count, warning_count))
    conn.commit()
    cur.close()
    conn.close()
    print(f"[Trade DQ] Score: C={completeness} V={validity} T={timeliness} Total={total} "
          f"(symbols={actual_symbols}/{expected_symbols}, anomalies={anomaly_count}, gap={hours_gap:.1f}h)")


def detect_trade_anomalies(**ctx):
    """
    1. Symbol drop: 7일 평균 대비 30% 미만 심볼 보고 시 critical
    2. Price outlier spike: 1시간 내 anomaly_raw > 10건이면 warning
    """
    target_date = ctx['ds']
    target_ts = f"{target_date} 00:00:00+00"
    conn = _get_conn()
    cur = conn.cursor()

    # Symbol drop: 직전 1시간 심볼 수 vs 7일 평균
    cur.execute("""
        WITH recent AS (
            SELECT COUNT(DISTINCT symbol) as cnt
            FROM dq_trade_symbol_hourly
            WHERE hour = date_trunc('hour', %s::timestamptz - INTERVAL '1 hour')
        ),
        avg7d AS (
            SELECT AVG(symbol_count) as avg_cnt
            FROM (
                SELECT hour, COUNT(DISTINCT symbol) as symbol_count
                FROM dq_trade_symbol_hourly
                WHERE hour >= %s::timestamptz - INTERVAL '7 days'
                  AND hour < %s::timestamptz
                GROUP BY hour
            ) sub
        )
        SELECT r.cnt, a.avg_cnt
        FROM recent r, avg7d a
    """, (target_ts, target_ts, target_ts))
    row = cur.fetchone()
    if row and row[0] and row[1] and row[1] > 0:
        recent_cnt, avg_cnt = int(row[0]), float(row[1])
        if recent_cnt < avg_cnt * 0.3:
            cur.execute("""
                INSERT INTO dq_trade_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity, notes)
                VALUES ('symbol_drop', 'coverage', %s, %s, 'critical', %s)
            """, (avg_cnt, recent_cnt, f"symbols={recent_cnt}/{avg_cnt:.0f}, ratio={recent_cnt/avg_cnt*100:.1f}%"))
            print(f"[Trade DQ] CRITICAL: symbol_drop {recent_cnt}/{avg_cnt:.0f}")

    # Price outlier spike: 직전 1시간 anomaly_raw 건수
    cur.execute("""
        SELECT COUNT(*) FROM dq_trade_anomaly_raw
        WHERE detected_at >= %s::timestamptz - INTERVAL '1 hour'
          AND detected_at < %s::timestamptz
    """, (target_ts, target_ts))
    spike_count = cur.fetchone()[0] or 0
    if spike_count > 10:
        cur.execute("""
            INSERT INTO dq_trade_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity, notes)
            VALUES ('price_outlier', 'validity', 0, %s, 'warning', %s)
        """, (spike_count, f"{spike_count} anomalous ticks in 1h"))
        print(f"[Trade DQ] WARNING: price_outlier spike={spike_count}")

    conn.commit()
    cur.close()
    conn.close()


def reconcile_trade(**ctx):
    """
    교차검증: dq_trade_source_hourly(ticker event_count) vs dq_trade_symbol_hourly(총 tick_count)
    같은 Kafka 소스에서 두 경로로 집계. 불일치 5%→warning, 20%→critical.
    """
    target_date = ctx['ds']
    target_ts = f"{target_date} 00:00:00+00"
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        WITH source AS (
            SELECT hour, event_count
            FROM dq_trade_source_hourly
            WHERE source = 'ticker'
              AND hour >= %s::timestamptz - INTERVAL '24 hours'
              AND hour < %s::timestamptz
        ),
        symbol AS (
            SELECT hour, SUM(tick_count) as total_ticks
            FROM dq_trade_symbol_hourly
            WHERE hour >= %s::timestamptz - INTERVAL '24 hours'
              AND hour < %s::timestamptz
            GROUP BY hour
        )
        SELECT
            COALESCE(s.hour, y.hour) as hour,
            COALESCE(s.event_count, 0) as source_count,
            COALESCE(y.total_ticks, 0) as symbol_count
        FROM source s
        FULL OUTER JOIN symbol y ON s.hour = y.hour
        ORDER BY hour
    """, (target_ts, target_ts, target_ts, target_ts))

    mismatch_count = 0
    for row in cur.fetchall():
        hour, source_count, symbol_count = row
        base = max(source_count, symbol_count, 1)
        diff_pct = abs(source_count - symbol_count) / base * 100

        if diff_pct > 5:
            severity = 'critical' if diff_pct > 20 else 'warning'
            cur.execute("""
                INSERT INTO dq_trade_anomaly_log (anomaly_type, dimension, expected_value, actual_value, severity, notes)
                VALUES ('recon_mismatch', 'consistency', %s, %s, %s, %s)
            """, (source_count, symbol_count, severity, f"hour={hour}, diff={diff_pct:.1f}%"))
            mismatch_count += 1

    conn.commit()
    cur.close()
    conn.close()
    if mismatch_count:
        print(f"[Trade DQ] Reconciliation: {mismatch_count} mismatches found")
    else:
        print("[Trade DQ] Reconciliation: all hours within tolerance")


def detect_drift(**ctx):
    """
    데이터 드리프트 감지: 심볼별 tick_count/price/volume의 24h 평균을
    7일 기준선(mean ± 3σ)과 비교. z-score 절대값 > 3이면 드리프트 판정.

    감지 대상:
      - tick_drift: 틱 빈도 변화 (데이터 수집 이상)
      - price_drift: 가격 분포 변화 (시장 구조 변화)
      - volume_drift: 거래량 분포 변화 (유동성 변화)
    """
    conn = _get_conn()
    cur = conn.cursor()

    # tick_count 드리프트만 감지 (수집 이상 탐지 목적)
    # 크립토 price/volume은 heavy-tail 분포라 z-score 부적합 → 제외
    cur.execute("""
        WITH baseline AS (
            SELECT symbol,
                AVG(tick_count) as mean_ticks, STDDEV_POP(tick_count) as std_ticks
            FROM dq_trade_symbol_hourly
            WHERE hour >= NOW() - INTERVAL '8 days'
              AND hour < NOW() - INTERVAL '1 day'
            GROUP BY symbol
            HAVING COUNT(*) >= 24 AND STDDEV_POP(tick_count) > 0
        ),
        recent AS (
            SELECT symbol, AVG(tick_count) as r_ticks
            FROM dq_trade_symbol_hourly
            WHERE hour >= NOW() - INTERVAL '24 hours'
            GROUP BY symbol
        )
        SELECT r.symbol, r.r_ticks, b.mean_ticks, b.std_ticks,
            (r.r_ticks - b.mean_ticks) / b.std_ticks as tick_z
        FROM recent r
        JOIN baseline b ON r.symbol = b.symbol
        WHERE ABS((r.r_ticks - b.mean_ticks) / b.std_ticks) > 3
    """)

    drift_count = 0
    for row in cur.fetchall():
        symbol, r_ticks, mean_ticks, std_ticks, tick_z = row
        tick_z = float(tick_z or 0)
        severity = "critical" if abs(tick_z) > 5 else "warning"
        cur.execute("""
            INSERT INTO dq_trade_anomaly_log
            (anomaly_type, dimension, expected_value, actual_value, severity, notes)
            VALUES ('drift_tick_rate', %s, %s, %s, %s, %s)
        """, (symbol, float(mean_ticks), float(r_ticks), severity,
              f"z-score={tick_z:.2f}, 7d mean={float(mean_ticks):.1f}"))
        drift_count += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"[Trade DQ] Drift detection: {drift_count} drift events found")


with DAG(
    'trade_dq_scoring',
    default_args=default_args,
    description='Trade DQ 스코어링 + 이상탐지 + 교차검증 + 드리프트 감지',
    schedule='0 6 * * *',
    catchup=False,
    tags=['trade', 'dq'],
) as dag:

    t1 = PythonOperator(task_id='compute_trade_dq_score', python_callable=compute_trade_dq_score)
    t2 = PythonOperator(task_id='detect_trade_anomalies', python_callable=detect_trade_anomalies)
    t3 = PythonOperator(task_id='reconcile_trade', python_callable=reconcile_trade)
    t4 = PythonOperator(task_id='detect_drift', python_callable=detect_drift)

    t1 >> t2 >> t3 >> t4
