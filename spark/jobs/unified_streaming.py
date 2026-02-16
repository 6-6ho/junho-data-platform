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
    count, sum as spark_sum, approx_count_distinct, expr, lit, coalesce,
    to_date, hour
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    LongType, IntegerType, TimestampType
)
from datetime import datetime

# Common DB 모듈
from common.db import save_movers_batch
import psycopg2
from psycopg2.extras import execute_values
import urllib.request
import urllib.parse
import json

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
    StructField("payment_method", StringType()),
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
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "driver": "org.postgresql.Driver"
}

# Thresholds
THRESHOLD_5M = 3.0
THRESHOLD_10M = 7.0

# =========================================================================
# ALERTS PROCESSING LOGIC
# =========================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        # print("[Alert] Telegram credentials not found. Skipping.")
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.getcode() != 200:
                print(f"[Alert] Failed to send Telegram: {response.read()}")
    except Exception as e:
        print(f"[Alert] Error sending Telegram: {e}")

# =========================================================================
# MOVERS PROCESSING LOGIC
# =========================================================================
def classify_status(change_pct, window_type):
    abs_change = abs(change_pct)
    direction = "Rise" if change_pct > 0 else "Fall"
    
    if window_type == "5m":
        if abs_change >= 11: return f"[High] {direction}"
        elif abs_change >= 7: return f"[Mid] {direction}"
        else: return f"[Small] {direction}"
    else: # 10m
        if abs_change >= 10: return f"[High] {direction}"
        elif abs_change >= 7: return f"[Mid] {direction}"
        else: return f"[Small] {direction}"

# Alert Manager for Deduplication
import time
from datetime import datetime, timedelta, timezone

class AlertManager:
    _instance = None
    _history = {}
    _cooldown = 300  # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlertManager, cls).__new__(cls)
        return cls._instance

    def is_dnd_active(self):
        """Check if current time is 01:00 ~ 06:00 KST"""
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        # 1시 이상 6시 미만 (01:00:00 ~ 05:59:59)
        if 1 <= now_kst.hour < 6:
            return True
        return False

    def should_send(self, symbol):
        # 1. Check DND
        if self.is_dnd_active():
            print(f"[AlertManager] DND Active (01-06 KST). Skipping {symbol}")
            return False

        # 2. Check Cooldown
        now = time.time()
        last = self._history.get(symbol, 0)
        if now - last < self._cooldown:
            return False
        return True
    
    def update(self, symbol):
        self._history[symbol] = time.time()
        print(f"[AlertManager] Updated {symbol} at {self._history[symbol]}")

# Initialize limits
am = AlertManager()

def process_movers_5m(batch_df, batch_id):
    rows = batch_df.filter(f"abs(change_pct_window) >= {THRESHOLD_5M}").collect()
    if not rows:
        return
    
    movers = []
    for row in rows:
        status = classify_status(row.change_pct_window, "5m")
        # Trigger Alert on High/Mid (Rise Only)
        if "Rise" in status and ("[High]" in status or "[Mid]" in status):
            if am.should_send(row.symbol):
                icon = "🚀"
                msg = f"{icon} *{status}: {row.symbol} (5m)*\n" \
                      f"Price: *{row.close_price}*\n" \
                      f"Change: *{row.change_pct_window:.2f}%*\n" \
                      f"Time: {row.window_end_time}"
                send_telegram_alert(msg)
                print(f"[Alert] Sent Telegram for {row.symbol}")
                am.update(row.symbol)
            elif am.is_dnd_active():
                # DND case handled inside should_send log, but explicit log here for clarity if needed
                pass 
            else:
                print(f"[Alert] Skipped {row.symbol} (Cooldown)")

        if row.change_pct_window >= THRESHOLD_5M:
            movers.append({
                "type": "rise",
                "symbol": row.symbol,
                "status": status,
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
        status = classify_status(row.change_pct_window, "10m")
        # Trigger Alert on High/Mid (Rise Only)
        if "Rise" in status and ("[High]" in status or "[Mid]" in status):
            if am.should_send(row.symbol):
                icon = "🚀"
                msg = f"{icon} *{status}: {row.symbol} (10m)*\n" \
                      f"Price: *{row.close_price}*\n" \
                      f"Change: *{row.change_pct_window:.2f}%*\n" \
                      f"Time: {row.window_end_time}"
                send_telegram_alert(msg)
                print(f"[Alert] Sent Telegram for {row.symbol}")
                am.update(row.symbol)
            elif am.is_dnd_active():
                pass
# ... (Existing imports)


def save_stats_batch(stats_list):
    if not stats_list:
        return
    
    conn = None
    try:
        # DB_URL format: jdbc:postgresql://postgres:5432/app
        # Parse connection params manually or just use hardcoded for now matching DB_PROPERTIES
        conn = psycopg2.connect(
            host=DB_HOST,
            database="app",
            user="postgres",
            password=os.getenv("POSTGRES_PASSWORD", "")
        )
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO mart_trade_stats 
        (window_start, window_end, total_volume, trade_count, symbol_count)
        VALUES %s
        ON CONFLICT (window_start, window_end) DO UPDATE 
        SET total_volume = EXCLUDED.total_volume,
            trade_count = EXCLUDED.trade_count,
            symbol_count = EXCLUDED.symbol_count,
            batch_processed_at = NOW();
        """
        
        values = [
            (
                s['window_start'], 
                s['window_end'], 
                s['total_volume'], 
                s['trade_count'], 
                s['symbol_count']
            ) for s in stats_list
        ]
        
        execute_values(cur, insert_query, values)
        conn.commit()
        print(f"[Stats] Saved {len(stats_list)} records to mart_trade_stats")
        
    except Exception as e:
        print(f"[Stats] Error saving stats: {e}")
    finally:
        if conn:
            conn.close()

def process_stats_batch(batch_df, batch_id):
    # This function is called on the AGGREGATED Stats DataFrame
    rows = batch_df.collect()
    if not rows:
        return
    
    stats_data = []
    for row in rows:
        stats_data.append({
            "window_start": row.window.start,
            "window_end": row.window.end,
            "total_volume": float(row.total_volume),
            "trade_count": int(row.trade_count),
            "symbol_count": int(row.symbol_count)
        })
    
    save_stats_batch(stats_data)



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
# DQ PROCESSING LOGIC
# =========================================================================
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname="app",
        user="postgres", 
        password=os.getenv("POSTGRES_PASSWORD", "")
    )

def process_dq_category_hourly(batch_df, batch_id):
    if batch_df.isEmpty(): return
    rows = batch_df.collect()
    
    conn = get_db_connection()
    try:
        data = [(r.hour_start, r.category, r.event_count, r.purchase_count, r.total_revenue) for r in rows]
        sql = """
            INSERT INTO dq_category_hourly (hour, category, event_count, purchase_count, total_revenue)
            VALUES %s
            ON CONFLICT (hour, category) DO UPDATE SET
                event_count = dq_category_hourly.event_count + EXCLUDED.event_count,
                purchase_count = dq_category_hourly.purchase_count + EXCLUDED.purchase_count,
                total_revenue = dq_category_hourly.total_revenue + EXCLUDED.total_revenue
        """
        with conn.cursor() as cur:
            execute_values(cur, sql, data)
        conn.commit()
    except Exception as e:
        print(f"Error in dq_category_hourly: {e}")
    finally:
        conn.close()

def process_dq_payment_hourly(batch_df, batch_id):
    if batch_df.isEmpty(): return
    rows = batch_df.collect()
    
    conn = get_db_connection()
    try:
        data = [(r.hour_start, r.payment_method, r.purchase_count, r.total_revenue) for r in rows]
        sql = """
            INSERT INTO dq_payment_hourly (hour, payment_method, purchase_count, total_revenue)
            VALUES %s
            ON CONFLICT (hour, payment_method) DO UPDATE SET
                purchase_count = dq_payment_hourly.purchase_count + EXCLUDED.purchase_count,
                total_revenue = dq_payment_hourly.total_revenue + EXCLUDED.total_revenue
        """
        with conn.cursor() as cur:
            execute_values(cur, sql, data)
        conn.commit()
    except Exception as e:
        print(f"Error in dq_payment_hourly: {e}")
    finally:
        conn.close()

def process_dq_anomaly_raw(batch_df, batch_id):
    if batch_df.isEmpty(): return
    # dq_anomaly_raw is append-only log
    batch_df.write.mode("append").jdbc(DB_URL, "dq_anomaly_raw", properties=DB_PROPERTIES)

def process_raw_archival(batch_df, batch_id):
    if batch_df.isEmpty(): return
    # Archive to MinIO (Data Lake) partitioned by date/hour
    # Using 'append' mode for streaming batches
    batch_df \
        .withColumn("date", to_date(col("event_time"))) \
        .withColumn("hour", hour(col("event_time"))) \
        .write \
        .mode("append") \
        .partitionBy("date", "hour") \
        .parquet("s3a://raw/shop_events")


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
    
    print(f"[Config] TRADE_TOPIC: {TRADE_TOPIC}")
    
    # Feature Flag for Shop Streaming
    ENABLE_SHOP_STREAMING = os.getenv("ENABLE_SHOP_STREAMING", "true").lower() == "true"
    print(f"[Config] ENABLE_SHOP_STREAMING: {ENABLE_SHOP_STREAMING}")

    # =====================================================================
    # TRADE STREAM (ALWAYS ACTIVE)
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
        .trigger(processingTime='1 second') \
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
        .trigger(processingTime='1 second') \
        .foreachBatch(process_movers_10m) \
        .queryName("movers_10m") \
        .start()
    
    print("[Trade] Movers 5m, 10m queries started")
    

    # -------------------------------------------------------------------------
    # 2-3. Stats Aggregation (Heartbeat for DQ)
    # -------------------------------------------------------------------------
    # 1분 단위로 전체 Volume, Count 집계
    stats_df = trade_raw \
        .withWatermark("event_time", "1 minutes") \
        .groupBy(window("event_time", "1 minute")) \
        .agg(
            spark_sum("price").alias("total_volume"), 
            count("*").alias("trade_count"),
            approx_count_distinct("symbol").alias("symbol_count")
        )

    stats_query = stats_df.writeStream \
        .outputMode("update") \
        .foreachBatch(process_stats_batch) \
        .queryName("trade_stats_dq") \
        .trigger(processingTime="1 minute") \
        .start()
    
    # =====================================================================
    # SHOP STREAM (CONDITIONAL)
    # =====================================================================
    if ENABLE_SHOP_STREAMING:
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
        
        # --- DQ: CATEGORY HOURLY ---
        dq_category_df = shop_df \
            .groupBy(window("event_time", "1 hour", "1 hour"), "category") \
            .agg(
                count("*").alias("event_count"),
                spark_sum(expr("case when event_type = 'purchase' then 1 else 0 end")).alias("purchase_count"),
                spark_sum(expr("case when event_type = 'purchase' then total_amount else 0 end")).alias("total_revenue")
            ) \
            .select(
                col("window.start").alias("hour_start"),
                "category", "event_count", "purchase_count", "total_revenue"
            )
        
        query_dq_cat = dq_category_df.writeStream \
            .outputMode("update") \
            .trigger(processingTime='1 minute') \
            .foreachBatch(process_dq_category_hourly) \
            .queryName("dq_category") \
            .start()

        # --- DQ: PAYMENT HOURLY ---
        dq_payment_df = shop_df \
            .groupBy(window("event_time", "1 hour", "1 hour"), "payment_method") \
            .agg(
                count("*").alias("event_count"),
                spark_sum(expr("case when event_type = 'purchase' then 1 else 0 end")).alias("purchase_count"),
                spark_sum(expr("case when event_type = 'purchase' then total_amount else 0 end")).alias("total_revenue")
            ) \
            .select(
                col("window.start").alias("hour_start"),
                "payment_method", "event_count", "purchase_count", "total_revenue"
            )
        
        query_dq_pay = dq_payment_df.writeStream \
            .outputMode("update") \
            .trigger(processingTime='1 minute') \
            .foreachBatch(process_dq_payment_hourly) \
            .queryName("dq_payment") \
            .start()

        # --- DQ: ANOMALY RAW ---
        dq_anomaly_df = shop_df \
            .filter("price < 0 OR price >= 10000000") \
            .select(
                col("event_id"),
                col("event_type"),
                col("user_id"),
                col("product_id"),
                col("category"),
                col("price"),
                col("total_amount"),
                col("event_time").alias("timestamp"),
                lit("abnormal_price").alias("anomaly_reason"),
                col("event_time").alias("detected_at") # roughly same
            )

        query_dq_anomaly = dq_anomaly_df.writeStream \
            .outputMode("append") \
            .foreachBatch(process_dq_anomaly_raw) \
            .queryName("dq_anomaly") \
            .start()

        # --- RAW ARCHIVAL ---
        # Archive all events to MinIO for Batch Processing
        query_archival = shop_df.writeStream \
            .outputMode("append") \
            .trigger(processingTime='1 minute') \
            .foreachBatch(process_raw_archival) \
            .queryName("shop_archival") \
            .start()
        
        print("[Shop] Sales, Brand, Funnel, KPI queries started")
    else:
        print("[Shop] Streaming DISABLED by configuration.")

    print("=" * 60)
    print("All 8 streaming queries running in unified driver!")
    print("=" * 60)
    
    # Wait for any termination
    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
