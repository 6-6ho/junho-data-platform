#!/usr/bin/env python3
"""
Trade Streaming Job - 노트북 전용
Binance 실시간 데이터 처리: Movers 5m/10m, Alerts

실행: spark-submit jobs/trade_streaming.py
"""

import os
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, window, first, last,
    max as spark_max
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType
)

# DB Helper
from common.db import (
    save_movers_batch,
    get_active_trendlines,
    save_alerts_batch,
    get_last_alert_times
)

# =========================================================================
# CONFIG
# =========================================================================
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DB_HOST = os.getenv("DB_HOST", "postgres")

TRADE_TOPIC = "raw.ticker.usdtm"
TRADE_SCHEMA = StructType([
    StructField("event_time_ms", LongType()),
    StructField("symbol", StringType()),
    StructField("price", DoubleType()),
    StructField("volume_24h", DoubleType()),
    StructField("quote_volume_24h", DoubleType()),
    StructField("change_pct_24h", DoubleType())
])

THRESHOLD_5M = 3.0
THRESHOLD_10M = 7.0

# =========================================================================
# MOVERS PROCESSING
# =========================================================================
def classify_status(change_pct, window_type):
    if window_type == "5m":
        if change_pct >= 11: return "[High] Rise"
        elif change_pct >= 7: return "[Mid] Rise"
        else: return "[Small] Rise"
    else:
        if change_pct >= 10: return "[High] Rise"
        else: return "[Mid] Rise"

def process_movers_5m(batch_df, batch_id):
    rows = batch_df.filter(f"abs(change_pct_window) >= {THRESHOLD_5M}").collect()
    if not rows:
        return
    
    movers = []
    for row in rows:
        if row.change_pct_window >= THRESHOLD_5M:
            movers.append({
                "type": "rise",
                "symbol": row.symbol,
                "status": classify_status(row.change_pct_window, "5m"),
                "window": "5m",
                "event_time": row.window_end_time,
                "change_pct_window": row.change_pct_window,
                "change_pct_24h": 0.0,
                "vol_ratio": None
            })
    
    if movers:
        save_movers_batch(movers)

def process_movers_10m(batch_df, batch_id):
    rows = batch_df.filter(f"abs(change_pct_window) >= {THRESHOLD_10M}").collect()
    if not rows:
        return
    
    movers = []
    for row in rows:
        if row.change_pct_window >= THRESHOLD_10M:
            movers.append({
                "type": "rise",
                "symbol": row.symbol,
                "status": classify_status(row.change_pct_window, "10m"),
                "window": "10m",
                "event_time": row.window_end_time,
                "change_pct_window": row.change_pct_window,
                "change_pct_24h": 0.0,
                "vol_ratio": None
            })
    
    if movers:
        save_movers_batch(movers)

# =========================================================================
# ALERTS PROCESSING
# =========================================================================
def get_line_price_at_time(line, current_time_ms):
    if line['t2_ms'] == line['t1_ms']:
        return line['p1']
    m = (line['p2'] - line['p1']) / (line['t2_ms'] - line['t1_ms'])
    return m * (current_time_ms - line['t1_ms']) + line['p1']

def process_alerts(batch_df, batch_id):
    rows = batch_df.collect()
    if not rows:
        return

    lines = get_active_trendlines()
    if not lines:
        return

    line_ids = [line['line_id'] for line in lines]
    last_alert_times = get_last_alert_times(line_ids)

    lines_map = {}
    for line in lines:
        if line['symbol'] not in lines_map:
            lines_map[line['symbol']] = []
        lines_map[line['symbol']].append(line)
    
    alerts = []
    current_dt = datetime.now()

    for row in rows:
        sym = row.symbol
        price = row.price
        event_time = row.event_time_ms

        if sym in lines_map:
            for line in lines_map[sym]:
                line_id = line['line_id']
                cooldown_sec = line.get('cooldown_sec', 600)
                
                if line_id in last_alert_times:
                    elapsed = (current_dt - last_alert_times[line_id]).total_seconds()
                    if elapsed < cooldown_sec:
                        continue
                
                line_price = get_line_price_at_time(line, event_time)
                buffer = line['buffer_pct'] / 100.0
                
                is_break_up = price > line_price * (1 + buffer)
                is_break_down = price < line_price * (1 - buffer)

                direction = None
                if is_break_up and (line['mode'] in ['break_up', 'both']):
                    direction = 'break_up'
                elif is_break_down and (line['mode'] in ['break_down', 'both']):
                    direction = 'break_down'
                
                if direction:
                    alerts.append({
                        "event_time": current_dt,
                        "symbol": sym,
                        "line_id": line_id,
                        "direction": direction,
                        "price": price,
                        "line_price": line_price,
                        "buffer_pct": line['buffer_pct']
                    })
                    last_alert_times[line_id] = current_dt
    
    save_alerts_batch(alerts)

# =========================================================================
# MAIN
# =========================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Starting Trade Streaming Job (Laptop Node)")
    print("Movers 5m/10m + Alerts")
    print("=" * 60)

    spark = SparkSession.builder \
        .appName("TradeStreaming") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Trade Raw Stream
    trade_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", TRADE_TOPIC) \
        .option("maxOffsetsPerTrigger", 5000) \
        .load() \
        .select(from_json(col("value").cast("string"), TRADE_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", (col("event_time_ms") / 1000).cast("timestamp"))
    
    # --- MOVERS: 5m Window ---
    windowed_5m = trade_raw \
        .withWatermark("event_time", "2 minutes") \
        .groupBy(window(col("event_time"), "5 minutes", "15 seconds"), col("symbol")) \
        .agg(
            first("price").alias("open_price"),
            last("price").alias("close_price"),
            spark_max("event_time").alias("window_end_time")
        ) \
        .withColumn("change_pct_window", 
                    ((col("close_price") - col("open_price")) / col("open_price")) * 100)
    
    query_movers_5m = windowed_5m.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(process_movers_5m) \
        .queryName("movers_5m") \
        .start()
    
    # --- MOVERS: 10m Window ---
    windowed_10m = trade_raw \
        .withWatermark("event_time", "2 minutes") \
        .groupBy(window(col("event_time"), "10 minutes", "30 seconds"), col("symbol")) \
        .agg(
            first("price").alias("open_price"),
            last("price").alias("close_price"),
            spark_max("event_time").alias("window_end_time")
        ) \
        .withColumn("change_pct_window", 
                    ((col("close_price") - col("open_price")) / col("open_price")) * 100)
    
    query_movers_10m = windowed_10m.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(process_movers_10m) \
        .queryName("movers_10m") \
        .start()
    
    # --- ALERTS ---
    query_alerts = trade_raw.writeStream \
        .trigger(processingTime='10 seconds') \
        .foreachBatch(process_alerts) \
        .queryName("alerts") \
        .start()
    
    print("[Trade] Movers 5m, 10m, Alerts queries started")
    print("=" * 60)
    
    # Await all
    spark.streams.awaitAnyTermination()
