"""
Backfill Script: Timeseries Performance Analysis for Existing Signals
- Reads existing signals from movers_latest
- Fetches 60 1min klines after each signal
- Calculates profit % at each 1min interval (1, 2, 3, ..., 60 minutes)
- Stores to trade_performance_timeseries as JSONB
"""
import os
import time
import json
import requests
import psycopg2
from datetime import datetime, timezone

BINANCE_API = "https://fapi.binance.com"
WIN_THRESHOLD_PCT = 1.0  # Win if profit >= 1%
DAYS_BACK = 7
RATE_LIMIT_SLEEP = 0.15

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": 5432,
    "dbname": "app",
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
}


def fetch_klines(symbol, start_time_ms, interval="1m", limit=100):
    """Fetch klines from Binance Futures API."""
    url = (f"{BINANCE_API}/fapi/v1/klines?"
           f"symbol={symbol}&interval={interval}&startTime={start_time_ms}&limit={limit}")
    try:
        resp = requests.get(url, timeout=10)
        klines = resp.json()
        if isinstance(klines, dict):  # Error response
            return []
        return klines
    except Exception as e:
        print(f"  API error for {symbol}: {e}")
        return []


def analyze_timeseries_performance(symbol, alert_time_ms, entry_price):
    """
    Analyze performance at 1-minute intervals from 1min to 60min (60 time points).

    Returns:
        dict: {
            "timeseries_data": {
                "1": {"price": ..., "profit_pct": ..., "is_win": ...},
                "2": {"price": ..., "profit_pct": ..., "is_win": ...},
                ...
                "60": {"price": ..., "profit_pct": ..., "is_win": ...}
            }
        } or None if insufficient data
    """
    # 60 minutes = 60 candles of 1min intervals
    num_candles = 61  # 60 + buffer
    klines = fetch_klines(symbol, alert_time_ms, interval="1m", limit=num_candles)

    if not klines or len(klines) < 2:
        return None

    # Skip first candle (alert candle itself)
    future_candles = klines[1:]

    timeseries_data = {}

    # Calculate for each 1-minute interval: 1, 2, 3, ..., 60
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

    return {"timeseries_data": timeseries_data} if timeseries_data else None


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


def main():
    print("=" * 60)
    print(f"Timeseries Backfill: Last {DAYS_BACK} days | [Large] Rise signals")
    print("=" * 60, flush=True)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Fetch existing signals from movers_latest (last N days, [Large] Rise only)
    cutoff_time = f"NOW() - INTERVAL '{DAYS_BACK} days'"
    query = f"""
        SELECT DISTINCT
            symbol, type, event_time, change_pct_window, status
        FROM movers_latest
        WHERE event_time >= {cutoff_time}
          AND type = 'rise'
          AND change_pct_window >= 5.0
          AND NOT EXISTS (
              SELECT 1 FROM trade_performance_timeseries ts
              WHERE ts.symbol = movers_latest.symbol
                AND ts.alert_time = movers_latest.event_time
          )
        ORDER BY event_time DESC
    """
    cur.execute(query)
    signals = cur.fetchall()

    print(f"Found {len(signals)} signals to backfill (excluding duplicates)")
    if len(signals) == 0:
        print("No signals to process. Exiting.")
        cur.close()
        conn.close()
        return

    processed = 0
    skipped = 0
    errors = 0
    t0 = time.time()

    for i, (symbol, alert_type, event_time, change_pct, status) in enumerate(signals):
        try:
            alert_time_ms = int(event_time.timestamp() * 1000)

            # Get entry price from alert candle (1min candle)
            klines = fetch_klines(symbol, alert_time_ms, interval="1m", limit=1)
            if not klines:
                skipped += 1
                time.sleep(RATE_LIMIT_SLEEP)
                continue

            entry_price = float(klines[0][4])

            # Analyze timeseries (1, 2, 3, ..., 60 minutes)
            ts_result = analyze_timeseries_performance(symbol, alert_time_ms, entry_price)
            if ts_result:
                save_timeseries_result(cur, symbol, alert_type, event_time, entry_price, ts_result)
                conn.commit()
                processed += 1

                num_points = len(ts_result["timeseries_data"])
                if (i + 1) % 10 == 0 or i == 0:
                    print(f"[{i+1}/{len(signals)}] {symbol} @ {event_time.strftime('%m/%d %H:%M')}: "
                          f"{num_points} time points", flush=True)
            else:
                skipped += 1

            time.sleep(RATE_LIMIT_SLEEP)

        except Exception as e:
            print(f"[{i+1}/{len(signals)}] ERROR {symbol}: {e}", flush=True)
            conn.rollback()
            errors += 1
            time.sleep(0.5)

        # Progress update every 50 signals
        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(signals) - i - 1) / rate if rate > 0 else 0
            print(f"\n--- Progress: {i+1}/{len(signals)} | "
                  f"Processed: {processed}, Skipped: {skipped}, Errors: {errors} | "
                  f"ETA: {eta/60:.1f}min ---\n", flush=True)

    conn.commit()
    cur.close()
    conn.close()

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"DONE in {elapsed/60:.1f} minutes")
    print(f"Processed: {processed} | Skipped: {skipped} | Errors: {errors}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
