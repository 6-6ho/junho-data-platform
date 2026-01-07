import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, first, last, max, lit
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType
from datetime import datetime

# Adjust path to import common
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.db import save_movers_batch

KAFKA_TOPIC = "raw.ticker.usdtm"

SCHEMA = StructType([
    StructField("event_time_ms", LongType()),
    StructField("symbol", StringType()),
    StructField("price", DoubleType()),
    StructField("volume_24h", DoubleType()),
    StructField("quote_volume_24h", DoubleType()),
    StructField("change_pct_24h", DoubleType())
])

def create_spark_session():
    return SparkSession.builder \
        .appName("MoversJob") \
        .config("spark.jars", "/app/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar,/app/jars/spark-token-provider-kafka-0-10_2.12-3.5.0.jar,/app/jars/kafka-clients-3.4.1.jar,/app/jars/commons-pool2-2.11.1.jar") \
        .getOrCreate()

# Threshold settings (lowered for testing)
THRESHOLD_5M = 0.1  # 5-minute window threshold
THRESHOLD_2H = 0.5  # 2-hour window threshold

def classify_status(change_pct, window_type):
    """Classify mover status based on percentage change."""
    if window_type == "5m":
        if change_pct >= 11: return "[High] Rise"
        elif change_pct >= 7: return "[Mid] Rise"
        elif change_pct >= 3: return "[Small] Rise"
        else: return "[Minor] Rise"  # For testing with low threshold
    else:  # 2h
        if change_pct >= 15: return "[High] Rise"
        elif change_pct >= 10: return "[Mid] Rise"
        elif change_pct >= 5: return "[Small] Rise"
        else: return "[Minor] Rise"

def process_window(batch_df, batch_id, window_duration, window_label, threshold):
    """Process a specific window and save movers."""
    rows = batch_df.filter(f"abs(change_pct_window) >= {threshold}").collect()
    if not rows:
        return

    movers_to_save = []
    
    for row in rows:
        symbol = row.symbol
        change_pct = row.change_pct_window
        
        if change_pct >= threshold:
            status = classify_status(change_pct, window_label)
            movers_to_save.append({
                "type": "rise",
                "symbol": symbol,
                "status": status,
                "window": window_label,
                "event_time": row.window_end_time,
                "change_pct_window": change_pct,
                "change_pct_24h": 0.0,
                "vol_ratio": None
            })

    if movers_to_save:
        save_movers_batch(movers_to_save)

def run():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")) \
        .option("subscribe", KAFKA_TOPIC) \
        .load() \
        .select(from_json(col("value").cast("string"), SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", (col("event_time_ms") / 1000).cast("timestamp"))

    # --- 5-MINUTE WINDOW ---
    windowed_5m = df \
        .withWatermark("event_time", "10 minutes") \
        .groupBy(window(col("event_time"), "5 minutes", "1 minute"), col("symbol")) \
        .agg(
            first("price").alias("open_price"),
            last("price").alias("close_price"),
            max("event_time").alias("window_end_time")
        ) \
        .withColumn("change_pct_window", ((col("close_price") - col("open_price")) / col("open_price")) * 100)

    # --- 2-HOUR WINDOW ---
    windowed_2h = df \
        .withWatermark("event_time", "3 hours") \
        .groupBy(window(col("event_time"), "2 hours", "10 minutes"), col("symbol")) \
        .agg(
            first("price").alias("open_price"),
            last("price").alias("close_price"),
            max("event_time").alias("window_end_time")
        ) \
        .withColumn("change_pct_window", ((col("close_price") - col("open_price")) / col("open_price")) * 100)

    def process_5m_batch(batch_df, batch_id):
        process_window(batch_df, batch_id, "5 minutes", "5m", THRESHOLD_5M)

    def process_2h_batch(batch_df, batch_id):
        process_window(batch_df, batch_id, "2 hours", "2h", THRESHOLD_2H)

    # Start both streaming queries
    query_5m = windowed_5m.writeStream \
        .outputMode("update") \
        .foreachBatch(process_5m_batch) \
        .start()

    query_2h = windowed_2h.writeStream \
        .outputMode("update") \
        .foreachBatch(process_2h_batch) \
        .start()
    
    # Wait for both queries
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
