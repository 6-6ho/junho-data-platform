import sys
import os
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, to_timestamp, expr
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType
)

# Add parent directory to path to import common modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from common.db import save_movers_batch, save_market_snapshot, get_watchlist
    from common.trade_utils import send_telegram_alert, AlertManager, classify_status
except ImportError:
    # Fallback for when running from different context
    sys.path.append(os.path.join(os.getcwd(), 'spark'))
    from common.db import save_movers_batch, save_market_snapshot, get_watchlist
    from common.trade_utils import send_telegram_alert, AlertManager, classify_status

# CONFIG
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TRADE_TOPIC = "raw.ticker.usdtm"

# Schema
TRADE_SCHEMA = StructType([
    StructField("event_time_ms", LongType()),
    StructField("symbol", StringType()),
    StructField("price", DoubleType()),
    StructField("volume_24h", DoubleType()),
    StructField("quote_volume_24h", DoubleType()),
    StructField("change_pct_24h", DoubleType())
])

# Thresholds
THRESHOLD_5M_MIN = 3.0    # 5m 최소 진입 기준
THRESHOLD_10M_MIN = 7.0   # 10m 최소 진입 기준

am = AlertManager()

# Symbol-level cooldown to prevent duplicate alerts from overlapping sliding windows
# Key: symbol, Value: last alert timestamp (epoch seconds)
_movers_cooldown_5m = {}
_movers_cooldown_10m = {}
MOVERS_COOLDOWN_5M = 300   # 5 minutes: suppress same symbol
MOVERS_COOLDOWN_10M = 600  # 10 minutes: suppress same symbol

def process_movers_5m(batch_df, batch_id):
    print(f"[{datetime.now()}] Processing Batch {batch_id} for 5m Window...")
    rows = batch_df.collect()
    if not rows:
        print(f"[{datetime.now()}] Batch {batch_id} is empty.")
        return
        
    print(f"[{datetime.now()}] Batch {batch_id} has {len(rows)} rows.")
    
    # 1. Save ALL rows to market_snapshot for Theme RS
    # Deduplicate by symbol to avoid "ON CONFLICT DO UPDATE command cannot affect row a second time"
    dedup_snapshots = {}
    for row in rows:
        symbol = row.symbol
        # Use actual message time (latest_event_time) instead of window_end_time
        event_time = row.latest_event_time
        if symbol not in dedup_snapshots or event_time > dedup_snapshots[symbol]["event_time"]:
            dedup_snapshots[symbol] = {
                "symbol": symbol,
                "price": row.close_price,
                "change_pct_24h": row.change_pct_24h,
                "volume_24h": row.volume_24h,
                "change_pct_window": row.change_pct_window,
                "vol_ratio": 0.0, # Placeholder
                "event_time": event_time
            }
            
    snapshot_list = list(dedup_snapshots.values())
    save_market_snapshot(snapshot_list)
    print(f"[{datetime.now()}] Upserted {len(snapshot_list)} rows to market_snapshot.")

    # 2. Filter and save only significant RISE moves to movers_latest
    #    With symbol-level cooldown to prevent duplicates from overlapping windows
    watchlist = get_watchlist()
    movers = []
    now_ts = time.time()
    for row in rows:
        if row.change_pct_window < THRESHOLD_5M_MIN:
            continue

        status = classify_status(row.change_pct_window, "5m")

        # Cooldown check: skip if this symbol was already alerted recently
        last_alert = _movers_cooldown_5m.get(row.symbol, 0)
        if now_ts - last_alert < MOVERS_COOLDOWN_5M:
            continue  # Skip duplicate

        _movers_cooldown_5m[row.symbol] = now_ts

        is_fav = bool(watchlist and row.symbol in watchlist)
        # 즐겨찾기: 모든 Tier 알림 / 비즐겨찾기: High만
        should_alert = is_fav or "High" in status

        if should_alert and am.should_send(row.symbol):
            icon = "⭐" if is_fav else "🚀"
            msg = f"{icon} *{status}: {row.symbol} (5m)*\n" \
                  f"Price: *{row.close_price}*\n" \
                  f"Change: *{row.change_pct_window:.2f}%*\n" \
                  f"Time: {row.latest_event_time}"
            send_telegram_alert(msg)
            am.update(row.symbol)
            print(f"[Alert] Sent Telegram: {row.symbol}")

        movers.append({
            "type": "rise",
            "symbol": row.symbol,
            "status": status,
            "window": "5m",
            "event_time": row.latest_event_time,
            "change_pct_window": row.change_pct_window,
            "vol_ratio": 0.0
        })
            
    if movers:
        save_movers_batch(movers)

def process_movers_10m(batch_df, batch_id):
    # Optimize: Filter on Spark side before collect to reduce driver load
    # Only interested in rows that exceed the threshold (Rise or Fall)
    # Note: Logic in classify_status tracks ABS(change) >= 7% for Mid, so we filter broadly here.
    # THRESHOLD_10M is 7.0
    
    filtered_df = batch_df.filter(expr(f"abs(change_pct_window) >= {THRESHOLD_10M_MIN}"))

    rows = filtered_df.collect()
    if not rows:
        return

    watchlist = get_watchlist()
    movers = []
    now_ts = time.time()
    for row in rows:
        if row.change_pct_window < THRESHOLD_10M_MIN:
            continue

        status = classify_status(row.change_pct_window, "10m")

        # Cooldown check: skip if this symbol was already alerted recently
        last_alert = _movers_cooldown_10m.get(row.symbol, 0)
        if now_ts - last_alert < MOVERS_COOLDOWN_10M:
            continue  # Skip duplicate

        _movers_cooldown_10m[row.symbol] = now_ts

        is_fav = bool(watchlist and row.symbol in watchlist)
        # 즐겨찾기: 모든 Tier 알림 / 비즐겨찾기: High만
        should_alert = is_fav or "High" in status

        if should_alert and am.should_send(row.symbol, cooldown_override=MOVERS_COOLDOWN_10M):
            icon = "⭐" if is_fav else "🚀"
            msg = f"{icon} *{status}: {row.symbol} (10m)*\n" \
                  f"Price: *{row.close_price}*\n" \
                  f"Change: *{row.change_pct_window:.2f}%*\n" \
                  f"Time: {row.latest_event_time}"
            send_telegram_alert(msg)
            am.update(row.symbol)
            print(f"[Alert] Sent Telegram: {row.symbol}")

        movers.append({
            "type": "rise",
            "symbol": row.symbol,
            "status": status,
            "window": "10m",
            "event_time": row.latest_event_time,
            "change_pct_window": row.change_pct_window
        })
    
    if movers:
        save_movers_batch(movers)

def run():
    spark = SparkSession.builder \
        .appName("TradeMovers") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")

    # Read Kafka - Use EARLIEST to recover the data I accidentally deleted
    df_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", TRADE_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parse JSON
    df_parsed = df_raw.select(
        from_json(col("value").cast("string"), TRADE_SCHEMA).alias("data"),
        (col("timestamp").cast("double") / 1000).alias("msg_ts") # Kafka timestamp (sec)
    ).select("data.*", "msg_ts")
    
    # Needs timestamp for windowing + Filter USDT Perpetuals
    df_clean = df_parsed \
        .filter(col("symbol").endswith("USDT") & ~col("symbol").contains("_")) \
        .withColumn("timestamp", to_timestamp(col("event_time_ms") / 1000)) \
        .withWatermark("timestamp", "1 minutes")

    # 5m Window
    # Calculate open/close for window
    # first() and last() are not supported in streaming aggregation directly without window
    # Actually, to calculation change pct: (last - first) / first * 100
    # Spark Structured Streaming aggregation...
    
    # Define aggregation 5m
    df_5m = df_clean.groupBy(
        window("timestamp", "5 minutes", "1 minutes"),
        "symbol"
    ).agg(
        expr("first(price)").alias("open_price"),
        expr("last(price)").alias("close_price"),
        expr("last(change_pct_24h)").alias("change_pct_24h"),
        expr("last(volume_24h)").alias("volume_24h"),
        expr("max(timestamp)").alias("latest_event_time")
    ).withColumn("change_pct_window", 
        ((col("close_price") - col("open_price")) / col("open_price")) * 100
    ).withColumn("window_end_time", col("window.end"))
    
    query_5m = df_5m.writeStream \
        .foreachBatch(process_movers_5m) \
        .outputMode("update") \
        .option("checkpointLocation", "/app/checkpoints/trade-movers-5m") \
        .trigger(processingTime="10 seconds") \
        .start()

    # 10m Window
    df_10m = df_clean.groupBy(
        window("timestamp", "10 minutes", "1 minutes"),
        "symbol"
    ).agg(
        expr("first(price)").alias("open_price"),
        expr("last(price)").alias("close_price"),
        expr("max(timestamp)").alias("latest_event_time")
    ).withColumn("change_pct_window", 
        ((col("close_price") - col("open_price")) / col("open_price")) * 100
    ).withColumn("window_end_time", col("window.end"))
    
    query_10m = df_10m.writeStream \
        .foreachBatch(process_movers_10m) \
        .outputMode("update") \
        .option("checkpointLocation", "/app/checkpoints/trade-movers-10m") \
        .trigger(processingTime="10 seconds") \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
