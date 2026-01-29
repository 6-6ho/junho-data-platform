"""
Unified Spark Streaming - 3개 작업을 1개 Driver로 통합
Trade (Movers + Alerts) + Shop Analytics

메모리 최적화: 기존 3개 Driver (~1.5GB) → 1개 Driver (~600MB)
"""
import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, first, last, max as spark_max, 
    count, sum as spark_sum, approx_count_distinct, expr, lit, coalesce
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    LongType, IntegerType, TimestampType
)
from datetime import datetime

# Common DB 모듈
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
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

# Trade Config
TRADE_TOPIC = "raw.ticker.usdtm"
TRADE_SCHEMA = StructType([
    StructField("event_time_ms", LongType()),
    StructField("symbol", StringType()),
    StructField("price", DoubleType()),
    StructField("volume_24h", DoubleType()),
    StructField("quote_volume_24h", DoubleType()),
    StructField("change_pct_24h", DoubleType())
])

# Shop Config
SHOP_TOPIC = "shopping-events"
SHOP_SCHEMA = StructType([
    StructField("event_id", StringType()),
    StructField("event_type", StringType()),
    StructField("user_id", StringType()),
    StructField("product_id", StringType()),
    StructField("category", StringType()),
    StructField("brand", StringType()),
    StructField("price", DoubleType()),
    StructField("total_amount", DoubleType()),
    StructField("quantity", IntegerType()),
    StructField("timestamp", StringType()),
    StructField("session_id", StringType()),
    StructField("device", StructType([
        StructField("type", StringType()),
        StructField("os", StringType())
    ]))
])

# Postgres Config (환경변수로 호스트 변경 가능)
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": "postgres",
    "driver": "org.postgresql.Driver"
}

# Thresholds
THRESHOLD_5M = 3.0
THRESHOLD_10M = 7.0

# =========================================================================
# MOVERS PROCESSING LOGIC
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
# ALERTS PROCESSING LOGIC
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
# SHOP PROCESSING LOGIC
# =========================================================================
def upsert_hourly_sales(batch_df, batch_id):
    cnt = batch_df.count()
    print(f"[DEBUG] Sales Batch {batch_id}: {cnt} rows")
    if cnt == 0:
        return
    # 1. Postgres (Interactive)
    batch_df.write.mode("append").jdbc(DB_URL, "shop_hourly_sales_log", properties=DB_PROPERTIES)
    # 2. Iceberg (Data Lake)
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.hourly_sales")

def upsert_brand_stats(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    # 1. Postgres
    batch_df.write.mode("append").jdbc(DB_URL, "shop_brand_stats_log", properties=DB_PROPERTIES)
    # 2. Iceberg
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.brand_stats")

def upsert_funnel_stats(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    # 1. Postgres
    batch_df.write.mode("append").jdbc(DB_URL, "shop_funnel_stats_log", properties=DB_PROPERTIES)
    # 2. Iceberg
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.funnel_stats")

def upsert_realtime_metrics(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    # 1. Postgres
    batch_df.write.mode("append").jdbc(DB_URL, "shop_realtime_metrics_log", properties=DB_PROPERTIES)
    # 2. Iceberg
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.realtime_metrics")

# =========================================================================
# MAIN
# =========================================================================
def run():
    # 1. SparkSession with FAIR Scheduler
    spark = SparkSession.builder \
        .appName("UnifiedStreaming") \
        .config("spark.scheduler.mode", "FAIR") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.default.parallelism", "4") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 60)
    print("Unified Streaming Started - 3 Jobs in 1 Driver")
    print("=" * 60)

    # 2. Ensure Iceberg Tables Exist
    spark.sql("CREATE NAMESPACE IF NOT EXISTS my_catalog.shop")
    
    # Schemas are inferred from DataFrame logic, but for robustness we create them empty if not exists
    # Or simply rely on first batch to create? No, streaming append requires table.
    # Let's use a helper to create tables with correct schema from empty DF
    
    # Define schemas matching the aggregation results
    # Sales
    spark.sql("""
        CREATE TABLE IF NOT EXISTS my_catalog.shop.hourly_sales (
            window_start TIMESTAMP,
            window_end TIMESTAMP,
            category STRING,
            total_revenue DOUBLE,
            order_count LONG,
            avg_order_value DOUBLE
        ) USING iceberg
    """)
    
    # Brand
    spark.sql("""
        CREATE TABLE IF NOT EXISTS my_catalog.shop.brand_stats (
            window_start TIMESTAMP,
            brand_name STRING,
            total_revenue DOUBLE,
            order_count LONG
        ) USING iceberg
    """)
    
    # Funnel
    spark.sql("""
        CREATE TABLE IF NOT EXISTS my_catalog.shop.funnel_stats (
            window_start TIMESTAMP,
            total_sessions LONG,
            view_count LONG,
            cart_count LONG,
            purchase_count LONG,
            conversion_rate DOUBLE
        ) USING iceberg
    """)
    
    # KPI
    spark.sql("""
        CREATE TABLE IF NOT EXISTS my_catalog.shop.realtime_metrics (
            metric_name STRING,
            metric_value DOUBLE,
            last_updated TIMESTAMP
        ) USING iceberg
    """)

    print("[Iceberg] Tables verified in my_catalog.shop")
    
    # =====================================================================
    # TRADE STREAM
    # =====================================================================
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
    
    # =====================================================================
    # SHOP STREAM
    # =====================================================================
    shop_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", SHOP_TOPIC) \
        .option("startingOffsets", "earliest") \
        .option("maxOffsetsPerTrigger", 5000) \
        .load() \
        .select(from_json(col("value").cast("string"), SHOP_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", col("timestamp").cast(TimestampType()))
    
    shop_df = shop_raw.withWatermark("event_time", "10 minutes")
    
    # --- HOURLY SALES ---
    sales_df = shop_df \
        .filter("event_type = 'purchase'") \
        .groupBy(window("event_time", "1 hour", "5 minutes"), "category") \
        .agg(
            spark_sum("total_amount").alias("total_revenue"),
            count("event_id").alias("order_count"),
            (spark_sum("total_amount") / count("event_id")).alias("avg_order_value")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "category", "total_revenue", "order_count", "avg_order_value"
        )
    
    query_sales = sales_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_hourly_sales) \
        .queryName("shop_sales") \
        .start()
    
    # --- BRAND STATS ---
    brand_df = shop_df \
        .filter("event_type = 'purchase'") \
        .groupBy(window("event_time", "1 hour", "5 minutes"), "brand") \
        .agg(
            spark_sum("total_amount").alias("total_revenue"),
            count("event_id").alias("order_count")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("brand").alias("brand_name"),
            "total_revenue", "order_count"
        )
    
    query_brand = brand_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_brand_stats) \
        .queryName("shop_brand") \
        .start()
    
    # --- FUNNEL STATS ---
    funnel_df = shop_df \
        .groupBy(window("event_time", "1 hour", "5 minutes")) \
        .agg(
            approx_count_distinct("session_id").alias("total_sessions"),
            spark_sum(expr("case when event_type = 'view' then 1 else 0 end")).alias("view_count"),
            spark_sum(expr("case when event_type = 'add_cart' then 1 else 0 end")).alias("cart_count"),
            spark_sum(expr("case when event_type = 'purchase' then 1 else 0 end")).alias("purchase_count")
        ) \
        .withColumn("conversion_rate", 
                    (col("purchase_count") / coalesce(col("view_count"), lit(1))) * 100) \
        .select(
            col("window.start").alias("window_start"),
            "total_sessions", "view_count", "cart_count", "purchase_count", "conversion_rate"
        )
    
    query_funnel = funnel_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_funnel_stats) \
        .queryName("shop_funnel") \
        .start()
    
    # --- ACTIVE USERS KPI ---
    active_users_df = shop_df \
        .groupBy(window("event_time", "5 minutes", "1 minute")) \
        .agg(approx_count_distinct("user_id").alias("metric_value")) \
        .select(
            lit("active_users_5m").alias("metric_name"),
            col("metric_value").cast(DoubleType()),
            col("window.end").alias("last_updated")
        )
    
    query_kpi = active_users_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_realtime_metrics) \
        .queryName("shop_kpi") \
        .start()
    
    print("[Shop] Sales, Brand, Funnel, KPI queries started")
    print("=" * 60)
    print("All 8 streaming queries running in unified driver!")
    print("=" * 60)
    
    # Wait for any termination
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
