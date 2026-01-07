import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, first, last, max
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

def run():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")

    df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")) \
        .option("subscribe", KAFKA_TOPIC) \
        .load() \
        .select(from_json(col("value").cast("string"), SCHEMA).alias("data")) \
        .select("data.*")

    # --- WINDOWED AGGREGATION LOGIC ---
    # 5-minute window, sliding every 1 minute
    windowed_df = df \
        .withColumn("event_time", (col("event_time_ms") / 1000).cast("timestamp")) \
        .withWatermark("event_time", "10 minutes") \
        .groupBy(window(col("event_time"), "5 minutes", "1 minute"), col("symbol")) \
        .agg(
            first("price").alias("open_price"),
            last("price").alias("close_price"),
            max("event_time").alias("window_end_time")
        ) \
        .withColumn("change_pct_window", ((col("close_price") - col("open_price")) / col("open_price")) * 100)

    def process_batch(batch_df, batch_id):
        rows = batch_df.filter("abs(change_pct_window) >= 3.0").collect() # Filter for spec compliance
        if not rows:
            return

        movers_to_save = []
        
        for row in rows:
            symbol = row.symbol
            change_pct = row.change_pct_window
            # window_end = row.window.end # Struct window {start, end}

            # Spec:
            # Rise (5m):
            # Small: 3-7%
            # Mid: 7-11%
            # High: >11%
            
            # For testing/demo, we might lower these if market is flat, 
            # but let's stick to valid spec logic or slightly looser for visibility.
            
            if change_pct >= 3.0: # Strict Spec: Minimum 3%
                status = ""
                if change_pct >= 11: status = "[High] Rise"
                elif change_pct >= 7: status = "[Mid] Rise"
                else: status = "[Small] Rise"

                movers_to_save.append({
                    "type": "rise",
                    "symbol": symbol,
                    "status": status,
                    "window": "5m", 
                    "event_time": row.window_end_time,
                    "change_pct_window": change_pct,
                    "change_pct_24h": 0.0, # Not available in this aggregate stream
                    "vol_ratio": None
                })

        save_movers_batch(movers_to_save)

    query = windowed_df.writeStream \
        .outputMode("update") \
        .foreachBatch(process_batch) \
        .start()
    
    query.awaitTermination()

if __name__ == "__main__":
    run()
