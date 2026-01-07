import sys
import os
import math
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.db import get_active_trendlines, save_alerts_batch

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
        .appName("AlertsJob") \
        .config("spark.jars", "/app/jars/spark-sql-kafka-0-10_2.12-3.5.0.jar,/app/jars/spark-token-provider-kafka-0-10_2.12-3.5.0.jar,/app/jars/kafka-clients-3.4.1.jar,/app/jars/commons-pool2-2.11.1.jar") \
        .getOrCreate()

def get_line_price_at_time(line, current_time_ms):
    # y = mx + c
    # m = (p2 - p1) / (t2 - t1)
    # y - p1 = m * (x - t1) => y = m(x - t1) + p1
    if line['t2_ms'] == line['t1_ms']: return line['p1'] # Vertical line
    m = (line['p2'] - line['p1']) / (line['t2_ms'] - line['t1_ms'])
    return m * (current_time_ms - line['t1_ms']) + line['p1']

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

    def process_batch(batch_df, batch_id):
        rows = batch_df.collect()
        if not rows: return

        # 1. Fetch active trendlines
        lines = get_active_trendlines() # [{line_id, symbol, ...}]
        if not lines: return

        # Organize lines by symbol for faster lookup
        lines_map = {}
        for line in lines:
            if line['symbol'] not in lines_map: lines_map[line['symbol']] = []
            lines_map[line['symbol']].append(line)
        
        alerts = []
        current_dt = datetime.now()

        for row in rows:
            sym = row.symbol
            price = row.price
            event_time = row.event_time_ms

            if sym in lines_map:
                for line in lines_map[sym]:
                    # Calculate Line Price at this moment
                    line_price = get_line_price_at_time(line, event_time)
                    
                    # Logic: Crossing Detection
                    # V1 Simplification: "Price is above/below line with buffer"
                    # Real Crossing requires "Previous Price". 
                    # Here we check "Price > Line*(1+Buffer)" or "Price < Line*(1-Buffer)"
                    # To treat as "Event", we rely on the DB cooldown to prevent spam.
                    
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
                            "line_id": line['line_id'],
                            "direction": direction,
                            "price": price,
                            "line_price": line_price,
                            "buffer_pct": line['buffer_pct']
                        })
        
        # Save alerts (DB constraint handles cooldown if we implemented it, 
        # but pure INSERT will spam unless we filter by cooldown in Python logic.
        # V1: Insert all, handle dedup in UI or improved DB logic needed.)
        # TODO: Add Cooldown Check using DB timestamp.
        
        save_alerts_batch(alerts)

    query = df.writeStream \
        .foreachBatch(process_batch) \
        .start()
    
    query.awaitTermination()

if __name__ == "__main__":
    run()
