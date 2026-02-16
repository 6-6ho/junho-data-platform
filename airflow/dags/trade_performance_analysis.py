"""
Trade Performance Analysis DAG
- Runs daily at 01:00 KST (16:00 UTC)
- Analyzes movers alerts from the past session (18:00~01:00)
- Calculates win rate, max profit, max drawdown for each alert
- Saves individual results to trade_performance table
- Sends summary to Telegram
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime, timedelta
import requests
import time
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Performance thresholds
WIN_THRESHOLD_PCT = 1.0    # Consider "win" if max profit > 1%
STOP_LOSS_PCT = -2.0       # Stop loss threshold

# Analysis windows (minutes)
ANALYSIS_WINDOWS = [60, 240]  # 1h, 4h

default_args = {
    'owner': 'junho',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
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


def fetch_klines(symbol, start_time_ms, interval="5m", limit=100):
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


def analyze_single_alert(symbol, alert_time_ms, entry_price, window_minutes):
    """
    Analyze price action after an alert within a given time window.
    Returns dict with performance metrics or None.
    """
    # Fetch enough klines to cover the window
    # 5m candles: window_minutes / 5
    num_candles = (window_minutes // 5) + 2
    klines = fetch_klines(symbol, alert_time_ms, interval="5m", limit=num_candles)

    if not klines or len(klines) < 3:
        return None

    # Skip first candle (alert candle, we already have entry_price)
    future_candles = klines[1:]

    # Filter candles within the analysis window
    window_end_ms = alert_time_ms + (window_minutes * 60 * 1000)
    future_candles = [k for k in future_candles if k[0] <= window_end_ms]

    if not future_candles:
        return None

    max_price = entry_price
    min_price = entry_price

    for k in future_candles:
        high = float(k[2])
        low = float(k[3])
        if high > max_price:
            max_price = high
        if low < min_price:
            min_price = low

    close_price = float(future_candles[-1][4])

    max_profit_pct = ((max_price - entry_price) / entry_price) * 100
    max_drawdown_pct = ((min_price - entry_price) / entry_price) * 100
    final_profit_pct = ((close_price - entry_price) / entry_price) * 100

    is_win = max_profit_pct >= WIN_THRESHOLD_PCT
    if max_profit_pct >= WIN_THRESHOLD_PCT:
        result_type = "WIN"
    elif max_drawdown_pct <= STOP_LOSS_PCT:
        result_type = "LOSS"
    else:
        result_type = "BREAK_EVEN"

    return {
        "symbol": symbol,
        "alert_time": datetime.utcfromtimestamp(alert_time_ms / 1000),
        "analysis_window_minutes": window_minutes,
        "entry_price": entry_price,
        "max_price": max_price,
        "min_price": min_price,
        "close_price": close_price,
        "max_profit_pct": round(max_profit_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "final_profit_pct": round(final_profit_pct, 4),
        "is_win": is_win,
        "result_type": result_type,
    }


def run_performance_analysis(**context):
    """Main analysis task."""
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cur = conn.cursor()

    # 1. Fetch today's alerts (movers from the last trading session)
    # Trading session: previous day 18:00 ~ today 01:00 KST
    # Ensure we only analyze alerts old enough to have price data
    query = """
        SELECT DISTINCT ON (symbol, event_time)
            symbol, event_time, change_pct_window, type, status
        FROM movers_latest
        WHERE event_time >= NOW() - INTERVAL '12 hours'
          AND event_time <= NOW() - INTERVAL '1 hour'
        ORDER BY symbol, event_time, change_pct_window DESC
    """
    cur.execute(query)
    alerts = cur.fetchall()

    if not alerts:
        print("No alerts found for analysis")
        send_telegram("📊 *Performance Analysis*\n\nNo alerts in the last session.")
        return

    print(f"Found {len(alerts)} alerts to analyze")

    total_results = []
    insert_query = """
        INSERT INTO trade_performance (
            symbol, alert_type, alert_time,
            analysis_window_minutes,
            entry_price, max_price, min_price, close_price,
            max_profit_pct, max_drawdown_pct, final_profit_pct,
            is_win, result_type
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    for alert_row in alerts:
        symbol, event_time, change_pct, alert_type, status = alert_row
        alert_time_ms = int(event_time.timestamp() * 1000)

        # Get entry price from Binance (close of alert candle)
        klines = fetch_klines(symbol, alert_time_ms, interval="5m", limit=1)
        if not klines:
            time.sleep(0.2)
            continue

        entry_price = float(klines[0][4])

        for window_min in ANALYSIS_WINDOWS:
            result = analyze_single_alert(symbol, alert_time_ms, entry_price, window_min)
            if result is None:
                continue

            # Save to DB
            try:
                cur.execute(insert_query, (
                    result["symbol"],
                    alert_type or "rise",
                    result["alert_time"],
                    result["analysis_window_minutes"],
                    result["entry_price"],
                    result["max_price"],
                    result["min_price"],
                    result["close_price"],
                    result["max_profit_pct"],
                    result["max_drawdown_pct"],
                    result["final_profit_pct"],
                    result["is_win"],
                    result["result_type"],
                ))
                total_results.append(result)
            except Exception as e:
                print(f"DB insert error for {symbol}: {e}")
                conn.rollback()
                continue

        time.sleep(0.15)  # Rate limit

    conn.commit()
    print(f"Saved {len(total_results)} performance records")

    # 2. Generate summary
    if total_results:
        # 1h window stats
        results_1h = [r for r in total_results if r["analysis_window_minutes"] == 60]
        results_4h = [r for r in total_results if r["analysis_window_minutes"] == 240]

        msg = "📊 *Performance Analysis Report*\n\n"

        for label, results in [("1h Window", results_1h), ("4h Window", results_4h)]:
            if not results:
                continue
            wins = sum(1 for r in results if r["is_win"])
            total = len(results)
            win_rate = (wins / total) * 100 if total > 0 else 0
            avg_max = sum(r["max_profit_pct"] for r in results) / total
            avg_dd = sum(r["max_drawdown_pct"] for r in results) / total
            best = max(results, key=lambda r: r["max_profit_pct"])

            icon = "🟢" if win_rate >= 50 else "🔴"
            msg += f"*{label}* {icon}\n"
            msg += f"  Signals: {total}\n"
            msg += f"  Win Rate: *{win_rate:.1f}%*\n"
            msg += f"  Avg Max Profit: *{avg_max:.2f}%*\n"
            msg += f"  Avg Max DD: *{avg_dd:.2f}%*\n"
            msg += f"  Best: {best['symbol']} (+{best['max_profit_pct']:.1f}%)\n\n"

        send_telegram(msg)
    else:
        send_telegram("📊 *Performance Analysis*\n\nInsufficient data for analysis.")

    cur.close()
    conn.close()


with DAG(
    "trade_performance_analysis",
    default_args=default_args,
    description="Analyze movers alert performance (win rate, profit, drawdown)",
    schedule_interval="0 16 * * *",  # 16:00 UTC = 01:00 KST
    catchup=False,
    tags=["trade", "analysis"],
) as dag:

    analyze_task = PythonOperator(
        task_id="run_performance_analysis",
        python_callable=run_performance_analysis,
    )
