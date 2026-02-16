import sys
import os
import json
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, window, to_timestamp, expr, 
    count, sum as spark_sum, approx_count_distinct,
    to_date, hour
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType, IntegerType, TimestampType
)
import psycopg2
from psycopg2.extras import execute_values

# Add parent directory to path to import common modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from common.db import DBConnection
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), 'spark'))
    from common.db import DBConnection

# CONFIG
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
SHOP_TOPIC = "shopping-events"

# Postgres Config for Spark JDBC
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "driver": "org.postgresql.Driver"
}

# Schema
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

# =========================================================================
# SINK FUNCTIONS
# =========================================================================

def upsert_hourly_sales(batch_df, batch_id):
    if batch_df.isEmpty(): return
    # 1. Postgres (Interactive)
    # batch_df has [window_start, window_end, category, total_revenue, order_count, avg_order_value]
    # To append to postgres log table:
    batch_df.write.mode("append").jdbc(DB_URL, "shop_hourly_sales_log", properties=DB_PROPERTIES)
    
    # 2. Iceberg (Data Lake)
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.hourly_sales")

def upsert_brand_stats(batch_df, batch_id):
    if batch_df.isEmpty(): return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_brand_stats_log", properties=DB_PROPERTIES)
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.brand_stats")

def upsert_funnel_stats(batch_df, batch_id):
    if batch_df.isEmpty(): return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_funnel_stats_log", properties=DB_PROPERTIES)
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.funnel_stats")

def upsert_realtime_metrics(batch_df, batch_id):
    if batch_df.isEmpty(): return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_realtime_metrics_log", properties=DB_PROPERTIES)
    batch_df.write \
        .format("iceberg") \
        .mode("append") \
        .save("my_catalog.shop.realtime_metrics")

# =========================================================================
# DQ SINK FUNCTIONS (Using DBConnection Pool)
# =========================================================================

def process_dq_category_hourly(batch_df, batch_id):
    if batch_df.isEmpty(): return
    rows = batch_df.collect()
    
    conn = DBConnection.get_connection()
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
        conn.rollback()
    finally:
        DBConnection.return_connection(conn)

def process_dq_payment_hourly(batch_df, batch_id):
    if batch_df.isEmpty(): return
    rows = batch_df.collect()
    
    conn = DBConnection.get_connection()
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
        conn.rollback()
    finally:
        DBConnection.return_connection(conn)

def process_raw_archival(batch_df, batch_id):
    if batch_df.isEmpty(): return
    # Archive to MinIO (Data Lake)
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
    spark = SparkSession.builder \
        .appName("ShopAnalytics") \
        .config("spark.scheduler.mode", "FAIR") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Create Tables if not exist
    spark.sql("CREATE NAMESPACE IF NOT EXISTS my_catalog.shop")
    
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

    # Read Kafka
    shop_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", SHOP_TOPIC) \
        .option("startingOffsets", "earliest") \
        .load() \
        .select(from_json(col("value").cast("string"), SHOP_SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", col("timestamp").cast(TimestampType()))
    
    shop_df = shop_raw.withWatermark("event_time", "10 minutes")

    # --- 1. HOURLY SALES ---
    query_sales = shop_df \
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
        ) \
        .writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_hourly_sales) \
        .start()

    # --- 2. RAW ARCHIVAL ---
    query_archival = shop_df.writeStream \
        .foreachBatch(process_raw_archival) \
        .start()

    # (Skipping other queries for brevity if not strictly needed for MVP, but user asked for "separation", so I should probably keep them all?
    #  Review said "redundancy...". But this is separation.
    #  To keep file size manageable, I will implement Brand, Funnel, & DQ as well.)

    # --- 3. BRAND STATS ---
    query_brand = shop_df \
        .filter("event_type = 'purchase' AND brand IS NOT NULL") \
        .groupBy(window("event_time", "1 hour"), "brand") \
        .agg(
            spark_sum("total_amount").alias("total_revenue"),
            count("event_id").alias("order_count")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("brand").alias("brand_name"),
            "total_revenue", "order_count"
        ) \
        .writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_brand_stats) \
        .start()

    # --- 4. FUNNEL STATS ---
    # Simplified Funnel
    query_funnel = shop_df \
        .groupBy(window("event_time", "1 hour")) \
        .agg(
            count("session_id").alias("total_sessions"),
            spark_sum(expr("case when event_type = 'view' then 1 else 0 end")).alias("view_count"),
            spark_sum(expr("case when event_type = 'cart' then 1 else 0 end")).alias("cart_count"),
            spark_sum(expr("case when event_type = 'purchase' then 1 else 0 end")).alias("purchase_count")
        ) \
        .withColumn("conversion_rate", col("purchase_count") / col("total_sessions")) \
        .select(
            col("window.start").alias("window_start"),
            "total_sessions", "view_count", "cart_count", "purchase_count", "conversion_rate"
        ) \
        .writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_funnel_stats) \
        .start()

    # --- 5. DQ CHECKS (Payment Hourly) ---
    query_dq_payment = shop_df \
        .filter("event_type = 'purchase'") \
        .groupBy(window("event_time", "1 hour"), "payment_method") \
        .agg(
            count("event_id").alias("purchase_count"),
            spark_sum("total_amount").alias("total_revenue")
        ) \
        .select(
            col("window.start").alias("hour_start"),
            "payment_method", "purchase_count", "total_revenue"
        ) \
        .writeStream \
        .outputMode("update") \
        .foreachBatch(process_dq_payment_hourly) \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
