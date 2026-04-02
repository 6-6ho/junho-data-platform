"""
Trade Backfill DAG — 전체 파이프라인 갭 탐지 + 자동 재처리

매일 08:00 UTC (17:00 KST) 실행.
전체 Trade 파이프라인의 누락 날짜를 자동 탐지하고 재처리.

의존성 체인:
  movers_latest (streaming, continuous)
    → trade_performance_timeseries (performance_analysis DAG, 09:00 KST)
      → mart_trade_optimize_daily (performance_mart DAG, 09:30 KST)
    → dq_trade_daily_score (dq_scoring DAG, 15:00 KST)
    → iceberg.trade.* (lake DAG, 16:00 KST)

갭 탐지 대상:
  1. movers가 있는데 performance_timeseries가 없는 날짜 → 수집 재실행
  2. performance_timeseries가 있는데 mart가 없는 날짜 → 마트 빌드 재실행
  3. dq_trade_daily_score가 없는 날짜 → DQ 스코어링 재실행

수동 트리거: Airflow UI에서 conf={"backfill_days": 7} 로 범위 지정 가능.
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import json
import logging

logger = logging.getLogger(__name__)

LAPTOP_IP = os.getenv("LAPTOP_IP", "postgres")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

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
        host=LAPTOP_IP, port=5432, database="app",
        user="postgres", password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )


def _send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


def detect_gaps(**ctx):
    """누락 날짜 탐지. XCom으로 다음 태스크에 전달."""
    conf = ctx.get("dag_run").conf or {}
    lookback = int(conf.get("backfill_days", 14))

    conn = _get_conn()
    cur = conn.cursor()

    # 1. movers가 있는데 performance_timeseries가 없는 날짜
    cur.execute("""
        SELECT DISTINCT event_time::date as d FROM movers_latest
        WHERE event_time::date >= CURRENT_DATE - %s
          AND event_time::date < CURRENT_DATE
          AND event_time::date NOT IN (
              SELECT DISTINCT alert_time::date FROM trade_performance_timeseries
          )
        ORDER BY d
    """, (lookback,))
    perf_gaps = [str(r[0]) for r in cur.fetchall()]

    # 2. performance_timeseries가 있는데 mart가 없는 날짜
    cur.execute("""
        SELECT DISTINCT alert_time::date as d FROM trade_performance_timeseries
        WHERE alert_time::date >= CURRENT_DATE - %s
          AND alert_time::date < CURRENT_DATE
          AND alert_time::date NOT IN (
              SELECT DISTINCT date FROM mart_trade_optimize_daily
          )
        ORDER BY d
    """, (lookback,))
    mart_gaps = [str(r[0]) for r in cur.fetchall()]

    # 3. dq_trade_daily_score 누락
    cur.execute("""
        SELECT d::date FROM generate_series(
            CURRENT_DATE - %s, CURRENT_DATE - 1, '1 day'
        ) d
        WHERE d::date NOT IN (SELECT date FROM dq_trade_daily_score)
        ORDER BY d
    """, (lookback,))
    dq_gaps = [str(r[0]) for r in cur.fetchall()]

    cur.close()
    conn.close()

    gaps = {
        "performance": perf_gaps,
        "mart": mart_gaps,
        "dq": dq_gaps,
    }

    total = len(perf_gaps) + len(mart_gaps) + len(dq_gaps)
    logger.info(f"[Backfill] Gaps detected: perf={len(perf_gaps)}, mart={len(mart_gaps)}, dq={len(dq_gaps)}")

    if total > 0:
        _send_telegram(
            f"🔄 *Trade Backfill*\n"
            f"Performance 수집 누락: {len(perf_gaps)}일\n"
            f"Mart 빌드 누락: {len(mart_gaps)}일\n"
            f"DQ 스코어 누락: {len(dq_gaps)}일"
        )

    ctx['ti'].xcom_push(key='gaps', value=gaps)
    return gaps


def backfill_performance(**ctx):
    """performance_timeseries 누락 날짜 재수집."""
    import requests
    import time

    gaps = ctx['ti'].xcom_pull(key='gaps', task_ids='detect_gaps')
    dates = gaps.get("performance", [])
    if not dates:
        logger.info("[Backfill] No performance gaps")
        return

    conn = _get_conn()
    cur = conn.cursor()

    for target_date in dates:
        logger.info(f"[Backfill] Re-collecting performance for {target_date}")

        # movers_latest에서 해당 날짜 신호 조회
        cur.execute("""
            SELECT symbol, event_time, change_pct_window
            FROM movers_latest
            WHERE event_time::date = %s AND change_pct_window >= 3
        """, (target_date,))
        signals = cur.fetchall()

        collected = 0
        for symbol, alert_time, change_pct in signals:
            try:
                alert_ms = int(alert_time.timestamp() * 1000)
                url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=1m&startTime={alert_ms}&limit=61"
                resp = requests.get(url, timeout=10)
                if resp.status_code != 200:
                    continue
                klines = resp.json()
                if len(klines) < 2:
                    continue

                entry_price = float(klines[0][4])  # first candle close
                ts_data = {}
                for i, k in enumerate(klines[1:], 1):
                    close = float(k[4])
                    profit = (close - entry_price) / entry_price * 100
                    ts_data[str(i)] = {
                        "price": close,
                        "profit_pct": round(profit, 4),
                        "is_win": profit >= 1.0,
                    }

                cur.execute("""
                    INSERT INTO trade_performance_timeseries
                    (symbol, alert_type, alert_time, entry_price, timeseries_data)
                    VALUES (%s, 'rise', %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (symbol, alert_time, entry_price, json.dumps(ts_data)))

                # raw snapshot
                cur.execute("""
                    INSERT INTO signal_raw_snapshot (symbol, alert_time, entry_price, klines_1m)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (symbol, alert_time, entry_price, json.dumps(klines)))

                collected += 1
                time.sleep(0.1)  # rate limit
            except Exception as e:
                logger.warning(f"[Backfill] Failed {symbol} {target_date}: {e}")

        conn.commit()
        logger.info(f"[Backfill] {target_date}: {collected}/{len(signals)} signals re-collected")

    cur.close()
    conn.close()


def backfill_dq(**ctx):
    """DQ 스코어 누락 날짜 재계산."""
    gaps = ctx['ti'].xcom_pull(key='gaps', task_ids='detect_gaps')
    dates = gaps.get("dq", [])
    if not dates:
        logger.info("[Backfill] No DQ gaps")
        return

    conn = _get_conn()
    cur = conn.cursor()

    for target_date in dates:
        target_ts = f"{target_date} 00:00:00+00"
        logger.info(f"[Backfill] Re-scoring DQ for {target_date}")

        # Completeness
        cur.execute("""
            SELECT COUNT(DISTINCT symbol) FROM dq_trade_symbol_hourly
            WHERE hour >= %s::timestamptz - INTERVAL '24 hours' AND hour < %s::timestamptz
        """, (target_ts, target_ts))
        actual = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(DISTINCT symbol) FROM market_snapshot")
        expected = cur.fetchone()[0] or 1
        completeness = min(100, int(actual / expected * 100))

        # Validity
        cur.execute("""
            SELECT COUNT(*) FROM dq_trade_anomaly_raw
            WHERE detected_at >= %s::timestamptz - INTERVAL '24 hours' AND detected_at < %s::timestamptz
        """, (target_ts, target_ts))
        anomaly_count = cur.fetchone()[0] or 0
        validity = max(0, 100 - anomaly_count * 2)

        # Timeliness
        cur.execute("SELECT EXTRACT(EPOCH FROM (NOW() - MAX(event_time))) / 60 FROM market_snapshot")
        row = cur.fetchone()
        minutes_late = float(row[0]) if row and row[0] else 999
        timeliness = 100 if minutes_late <= 2 else max(0, int(100 - (minutes_late - 2) * 10))

        total = int(completeness * 0.4 + validity * 0.3 + timeliness * 0.3)

        cur.execute("""
            INSERT INTO dq_trade_daily_score (date, completeness_score, validity_score, timeliness_score, total_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                completeness_score=EXCLUDED.completeness_score, validity_score=EXCLUDED.validity_score,
                timeliness_score=EXCLUDED.timeliness_score, total_score=EXCLUDED.total_score, updated_at=NOW()
        """, (target_date, completeness, validity, timeliness, total))
        conn.commit()
        logger.info(f"[Backfill] DQ {target_date}: C={completeness} V={validity} T={timeliness} Total={total}")

    cur.close()
    conn.close()


def report_result(**ctx):
    """재처리 결과 요약 → Telegram."""
    gaps = ctx['ti'].xcom_pull(key='gaps', task_ids='detect_gaps')
    total = sum(len(v) for v in gaps.values())
    if total == 0:
        logger.info("[Backfill] No gaps found — pipeline healthy")
        return

    _send_telegram(
        f"✅ *Trade Backfill Complete*\n"
        f"Performance: {len(gaps.get('performance', []))}일 재수집\n"
        f"Mart: {len(gaps.get('mart', []))}일 (별도 DAG 트리거 필요)\n"
        f"DQ: {len(gaps.get('dq', []))}일 재계산"
    )


with DAG(
    'trade_backfill',
    default_args=default_args,
    description='Trade 파이프라인 갭 탐지 + 자동 재처리',
    schedule='0 8 * * *',
    catchup=False,
    tags=['trade', 'backfill', 'reliability'],
) as dag:

    t1 = PythonOperator(task_id='detect_gaps', python_callable=detect_gaps)
    t2 = PythonOperator(task_id='backfill_performance', python_callable=backfill_performance)
    t3 = PythonOperator(task_id='backfill_dq', python_callable=backfill_dq)
    t4 = PythonOperator(task_id='report_result', python_callable=report_result)

    t1 >> [t2, t3] >> t4
