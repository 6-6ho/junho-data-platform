"""
Signal Validation DAG
- Runs daily at 10:00 KST (01:00 UTC)
- Randomly samples recent signals and re-fetches prices from Binance
- Compares stored profit_pct with recalculated values
- Logs results to signal_validation_log
- Sends Telegram alert on failures
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import requests
import random
import json
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DIFF_THRESHOLD_PCT = 1.0
SAMPLE_SIZE = 10
LOOKBACK_DAYS = 7
VERIFY_MINUTE = 10  # 10분 시점 profit_pct 검증

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram token not configured")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def fetch_klines(symbol, start_time_ms, interval="1m", limit=100):
    """Fetch klines from Binance Futures API."""
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_time_ms,
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Binance API error for {symbol}: {e}")
        return []


def run_signal_validation(**context):
    """Validate stored signal data against Binance prices."""
    ds = context.get("ds")
    target_date = datetime.strptime(ds, "%Y-%m-%d").date()

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    # 1. target_date 기준 7일 이내 시그널 중 랜덤 10개 선택
    cur.execute("""
        SELECT symbol, alert_time, entry_price, timeseries_data
        FROM trade_performance_timeseries
        WHERE created_at >= %s::date - INTERVAL '7 days'
          AND created_at < %s::date + INTERVAL '1 day'
        ORDER BY RANDOM()
        LIMIT %s
    """, (target_date, target_date, SAMPLE_SIZE))
    samples = cur.fetchall()

    if not samples:
        print(f"No signals to validate (date={target_date})")
        cur.close()
        conn.close()
        return

    print(f"Validating {len(samples)} signals (date={target_date})")
    fail_count = 0
    pass_count = 0
    error_count = 0
    fail_details = []

    for symbol, alert_time, entry_price, timeseries_data in samples:
        alert_time_ms = int(alert_time.timestamp() * 1000)

        try:
            # 2. Binance에서 entry candle + 10분 시점까지 재조회
            klines = fetch_klines(symbol, alert_time_ms, interval="1m", limit=VERIFY_MINUTE + 1)

            if not klines or len(klines) < VERIFY_MINUTE + 1:
                # 데이터 불충분 — error 처리
                cur.execute("""
                    INSERT INTO signal_validation_log
                    (symbol, alert_time, stored_profit_pct, recalc_profit_pct, diff_pct, status, detail)
                    VALUES (%s, %s, NULL, NULL, NULL, 'error', %s)
                """, (symbol, alert_time, f"Insufficient klines: got {len(klines) if klines else 0}"))
                error_count += 1
                continue

            # 재계산: entry candle의 close price → 10분 시점의 close price
            recalc_entry = float(klines[0][4])
            recalc_close = float(klines[VERIFY_MINUTE][4])
            recalc_profit = ((recalc_close - recalc_entry) / recalc_entry) * 100

            # 3. 저장된 값과 비교
            verify_key = str(VERIFY_MINUTE)
            if isinstance(timeseries_data, str):
                timeseries_data = json.loads(timeseries_data)

            stored_profit = None
            if verify_key in timeseries_data:
                stored_profit = timeseries_data[verify_key].get("profit_pct")

            if stored_profit is None:
                cur.execute("""
                    INSERT INTO signal_validation_log
                    (symbol, alert_time, stored_profit_pct, recalc_profit_pct, diff_pct, status, detail)
                    VALUES (%s, %s, NULL, %s, NULL, 'error', %s)
                """, (symbol, alert_time, round(recalc_profit, 4),
                      f"No stored data for minute {VERIFY_MINUTE}"))
                error_count += 1
                continue

            diff = abs(stored_profit - recalc_profit)

            # 4. 오차 판정
            if diff > DIFF_THRESHOLD_PCT:
                status = 'fail'
                fail_count += 1
                fail_details.append(
                    f"  {symbol} | stored={stored_profit:.4f}% recalc={recalc_profit:.4f}% diff={diff:.4f}%"
                )
            else:
                status = 'pass'
                pass_count += 1

            cur.execute("""
                INSERT INTO signal_validation_log
                (symbol, alert_time, stored_profit_pct, recalc_profit_pct, diff_pct, status, detail)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (symbol, alert_time, stored_profit, round(recalc_profit, 4),
                  round(diff, 4), status, None))

        except Exception as e:
            cur.execute("""
                INSERT INTO signal_validation_log
                (symbol, alert_time, stored_profit_pct, recalc_profit_pct, diff_pct, status, detail)
                VALUES (%s, %s, NULL, NULL, NULL, 'error', %s)
            """, (symbol, alert_time, str(e)))
            error_count += 1

    conn.commit()
    print(f"Validation complete: pass={pass_count}, fail={fail_count}, error={error_count}")

    # 5. fail 건이 있으면 Telegram 알림
    if fail_count > 0:
        msg = f"⚠️ *시그널 검증 실패*\n\n"
        msg += f"Pass: {pass_count} | Fail: {fail_count} | Error: {error_count}\n\n"
        msg += f"*실패 상세:*\n```\n"
        msg += "\n".join(fail_details)
        msg += "\n```\n"
        msg += f"\n임계값: ±{DIFF_THRESHOLD_PCT}% (10분 시점)"
        send_telegram(msg)
    else:
        print(f"All {pass_count} validations passed (errors: {error_count})")

    cur.close()
    conn.close()


with DAG(
    "signal_validation",
    default_args=default_args,
    description="Daily sample validation of stored signal profit against Binance",
    schedule_interval="0 1 * * *",  # 01:00 UTC = 10:00 KST
    catchup=True,
    tags=["trade", "validation", "dq"],
) as dag:

    validate_task = PythonOperator(
        task_id="run_signal_validation",
        python_callable=run_signal_validation,
    )
