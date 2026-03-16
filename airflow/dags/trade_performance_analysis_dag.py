"""
Trade Performance Analysis DAG
- Runs daily at 09:00 KST (00:00 UTC)
- Collects timeseries data for recent signals
- Analyzes optimal TP/SL combinations
- Sends strategy recommendation to Telegram
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import requests
import time
import json
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
LAPTOP_IP = os.getenv("LAPTOP_IP", "postgres")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")

WIN_THRESHOLD_PCT = 1.0

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


def analyze_timeseries_performance(symbol, alert_time_ms, entry_price):
    """
    Analyze performance at 1-minute intervals from 1min to 60min.
    Returns timeseries_data and raw klines for snapshot storage.
    """
    num_candles = 61
    klines = fetch_klines(symbol, alert_time_ms, interval="1m", limit=num_candles)

    if not klines or len(klines) < 2:
        return None

    future_candles = klines[1:]
    timeseries_data = {}

    for interval_minutes in range(1, 61):
        candle_idx = interval_minutes - 1

        if candle_idx >= len(future_candles):
            break

        candle = future_candles[candle_idx]
        close_price = float(candle[4])

        profit_pct = ((close_price - entry_price) / entry_price) * 100
        is_win = profit_pct >= WIN_THRESHOLD_PCT

        timeseries_data[str(interval_minutes)] = {
            "price": round(close_price, 8),
            "profit_pct": round(profit_pct, 4),
            "is_win": is_win
        }

    if not timeseries_data:
        return None

    return {"timeseries_data": timeseries_data, "raw_klines": klines}


def save_timeseries_result(cur, symbol, alert_type, alert_time, entry_price, ts_result):
    """Save timeseries analysis result to trade_performance_timeseries table."""
    query = """
        INSERT INTO trade_performance_timeseries (
            symbol, alert_type, alert_time, entry_price, timeseries_data
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (symbol, alert_type, alert_time) DO NOTHING
    """
    cur.execute(query, (
        symbol,
        alert_type,
        alert_time,
        entry_price,
        json.dumps(ts_result["timeseries_data"])
    ))


def save_raw_snapshot(cur, symbol, alert_time, entry_price, raw_klines):
    """Save raw kline data to signal_raw_snapshot for traceability."""
    klines_json = []
    for k in raw_klines:
        klines_json.append({
            "open_time": k[0],
            "open": k[1],
            "high": k[2],
            "low": k[3],
            "close": k[4],
            "volume": k[5],
            "close_time": k[6],
        })
    cur.execute("""
        INSERT INTO signal_raw_snapshot (symbol, alert_time, entry_price, klines_1m)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (symbol, alert_time) DO NOTHING
    """, (symbol, alert_time, entry_price, json.dumps(klines_json)))


def simulate_strategy(signals, take_profit, stop_loss):
    """Simulate a TP/SL strategy on signals."""
    wins = 0
    losses = 0
    total_pnl = 0

    for ts_data in signals:
        time_points = []
        for time_str, data in ts_data.items():
            time_points.append((int(time_str), data["profit_pct"]))
        time_points.sort(key=lambda x: x[0])

        if not time_points:
            continue

        result_pct = None
        for t, profit in time_points:
            if profit >= take_profit:
                result_pct = take_profit
                break
            elif profit <= -stop_loss:
                result_pct = -stop_loss
                break

        if result_pct is None:
            result_pct = time_points[-1][1]

        total_pnl += result_pct
        if result_pct > 0:
            wins += 1
        elif result_pct < 0:
            losses += 1

    total = len(signals)
    win_rate = (wins / total) * 100 if total > 0 else 0
    avg_pnl = total_pnl / total if total > 0 else 0

    return {
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 1),
        "avg_pnl": round(avg_pnl, 3)
    }


def run_performance_analysis(**context):
    """Main analysis task."""
    ds = context.get("ds")
    target_date = datetime.strptime(ds, "%Y-%m-%d").date()

    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    # 1. Collect new timeseries data for recent signals
    query = """
        SELECT DISTINCT ON (symbol, event_time)
            symbol, event_time, change_pct_window, type, status
        FROM movers_latest
        WHERE event_time >= %s::date
          AND event_time < %s::date + INTERVAL '1 day' - INTERVAL '1 hour'
          AND type = 'rise'
          AND change_pct_window >= 3.0
          AND NOT EXISTS (
              SELECT 1 FROM trade_performance_timeseries ts
              WHERE ts.symbol = movers_latest.symbol
                AND ts.alert_time = movers_latest.event_time
          )
        ORDER BY symbol, event_time, change_pct_window DESC
    """
    cur.execute(query, (target_date, target_date))
    new_alerts = cur.fetchall()

    print(f"Found {len(new_alerts)} new alerts to collect (date={target_date})")
    collected = 0

    for alert_row in new_alerts:
        symbol, event_time, change_pct, alert_type, status = alert_row
        alert_time_ms = int(event_time.timestamp() * 1000)

        klines = fetch_klines(symbol, alert_time_ms, interval="1m", limit=1)
        if not klines:
            time.sleep(0.2)
            continue

        entry_price = float(klines[0][4])

        ts_result = analyze_timeseries_performance(symbol, alert_time_ms, entry_price)
        if ts_result:
            try:
                save_timeseries_result(cur, symbol, alert_type or "rise", event_time, entry_price, ts_result)
                if ts_result.get("raw_klines"):
                    save_raw_snapshot(cur, symbol, event_time, entry_price, ts_result["raw_klines"])
                collected += 1
            except Exception as e:
                print(f"Timeseries insert error for {symbol}: {e}")
                conn.rollback()

        time.sleep(0.15)

    conn.commit()
    print(f"Collected {collected} new timeseries records")

    # 2. Analyze optimal strategies by tier (target_date's data)
    cur.execute("""
        SELECT t.timeseries_data,
               CASE WHEN m.status LIKE '[High]%%' THEN 'High'
                    WHEN m.status LIKE '[Mid]%%' THEN 'Mid'
                    ELSE 'Small' END as tier
        FROM trade_performance_timeseries t
        JOIN (
            SELECT DISTINCT ON (symbol, event_time) symbol, event_time, status
            FROM movers_latest WHERE type = 'rise'
            ORDER BY symbol, event_time, change_pct_window DESC
        ) m ON m.symbol = t.symbol AND m.event_time = t.alert_time
        WHERE t.alert_time >= %s::date
          AND t.alert_time < %s::date + INTERVAL '1 day'
    """, (target_date, target_date))
    rows = cur.fetchall()

    if not rows or len(rows) < 3:
        send_telegram("📊 *전략 분석*\n\n어제 데이터 부족 (최소 3개 신호 필요)")
        cur.close()
        conn.close()
        return

    # Group signals by tier
    tier_signals = {"High": [], "Mid": [], "Small": []}
    for row in rows:
        ts_data, tier = row[0], row[1]
        tier_signals[tier].append(ts_data)

    total_signals = len(rows)
    tier_counts = {t: len(s) for t, s in tier_signals.items()}

    # Test TP/SL combinations per tier
    tp_levels = [3, 4, 5, 6, 7, 8, 9, 10]
    sl_levels = [1, 2, 3]

    # 3. Build Telegram message
    msg = f"📊 *최적 전략 분석* (어제 기준)\n"
    msg += f"📈 총 신호: *{total_signals}개* "
    msg += f"(High: {tier_counts['High']} / Mid: {tier_counts['Mid']} / Small: {tier_counts['Small']})\n\n"

    tier_emoji = {"High": "🔴", "Mid": "🟡", "Small": "🟢"}

    for tier_name in ["High", "Mid", "Small"]:
        signals = tier_signals[tier_name]
        if len(signals) < 2:
            continue

        results = []
        for tp in tp_levels:
            for sl in sl_levels:
                if tp > sl:
                    result = simulate_strategy(signals, tp, sl)
                    results.append(result)

        results.sort(key=lambda x: x["avg_pnl"], reverse=True)
        best = results[0]

        emoji = tier_emoji[tier_name]
        msg += f"{emoji} *{tier_name}* — {len(signals)}개\n"
        msg += f"  추천: TP *+{best['take_profit']}%* / SL *-{best['stop_loss']}%*"
        msg += f" | 승률 {best['win_rate']}%"
        msg += f" | 평균 PnL *{best['avg_pnl']:+.2f}%*\n\n"

    send_telegram(msg)

    cur.close()
    conn.close()


with DAG(
    "trade_performance_analysis",
    default_args=default_args,
    description="Analyze optimal TP/SL strategies for trade signals",
    schedule_interval="0 0 * * *",  # 00:00 UTC = 09:00 KST
    catchup=True,
    tags=["trade", "analysis"],
) as dag:

    analyze_task = PythonOperator(
        task_id="run_performance_analysis",
        python_callable=run_performance_analysis,
    )

    export_to_iceberg = BashOperator(
        task_id='export_to_iceberg',
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
            --name ExportTimeseries \
            /app/jobs/trade/export_timeseries_to_iceberg.py --target-date {{{{ ds }}}}
        ''',
    )

    analyze_task >> export_to_iceberg
