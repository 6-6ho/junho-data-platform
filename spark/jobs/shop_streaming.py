#!/usr/bin/env python3
"""
Shop Streaming Job - 데스크탑 전용
쇼핑 데이터 실시간 처리: Sales, Brand, Funnel, KPI + Iceberg

실행: spark-submit jobs/shop_streaming.py
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, window, sum as spark_sum,
    count, avg, countDistinct, lit, current_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    IntegerType, TimestampType
)

# =========================================================================
# CONFIG
# =========================================================================
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": "postgres",
    "driver": "org.postgresql.Driver"
}

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
if __name__ == "__main__":
    print("=" * 60)
    print("Starting Shop Streaming Job (Desktop Node)")
    print("Sales, Brand, Funnel, KPI + Iceberg")
    print("=" * 60)

    spark = SparkSession.builder \
        .appName("ShopStreaming") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # --- Iceberg DDL ---
    print("[Iceberg] Creating namespace and tables if not exist...")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS my_catalog.shop LOCATION 's3a://iceberg-warehouse/shop'")
    
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
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS my_catalog.shop.brand_stats (
            window_start TIMESTAMP,
            brand_name STRING,
            total_revenue DOUBLE,
            order_count LONG
        ) USING iceberg
    """)
    
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
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS my_catalog.shop.realtime_metrics (
            metric_name STRING,
            metric_value DOUBLE,
            last_updated TIMESTAMP
        ) USING iceberg
    """)
    print("[Iceberg] Tables verified in my_catalog.shop")
    
    # --- Shop Raw Stream ---
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
    
    # --- SALES by Category (Hourly) ---
    sales_df = shop_df \
        .filter(col("event_type") == "purchase") \
        .groupBy(window(col("event_time"), "1 hour"), col("category")) \
        .agg(
            spark_sum("total_amount").alias("total_revenue"),
            count("*").alias("order_count"),
            avg("total_amount").alias("avg_order_value")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("category"),
            col("total_revenue"),
            col("order_count"),
            col("avg_order_value")
        )
    
    query_sales = sales_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_hourly_sales) \
        .queryName("shop_sales") \
        .start()
    
    # --- BRAND Stats ---
    brand_df = shop_df \
        .filter(col("event_type") == "purchase") \
        .groupBy(window(col("event_time"), "1 hour"), col("brand")) \
        .agg(
            spark_sum("total_amount").alias("total_revenue"),
            count("*").alias("order_count")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("brand").alias("brand_name"),
            col("total_revenue"),
            col("order_count")
        )
    
    query_brand = brand_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_brand_stats) \
        .queryName("shop_brand") \
        .start()
    
    # --- FUNNEL ---
    funnel_df = shop_df \
        .groupBy(window(col("event_time"), "1 hour")) \
        .agg(
            countDistinct("session_id").alias("total_sessions"),
            spark_sum((col("event_type") == "view").cast("long")).alias("view_count"),
            spark_sum((col("event_type") == "add_to_cart").cast("long")).alias("cart_count"),
            spark_sum((col("event_type") == "purchase").cast("long")).alias("purchase_count")
        ) \
        .withColumn("conversion_rate", 
                    (col("purchase_count") / col("total_sessions")) * 100) \
        .select(
            col("window.start").alias("window_start"),
            col("total_sessions"),
            col("view_count"),
            col("cart_count"),
            col("purchase_count"),
            col("conversion_rate")
        )
    
    query_funnel = funnel_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_funnel_stats) \
        .queryName("shop_funnel") \
        .start()
    
    # --- REALTIME KPI ---
    kpi_df = shop_df \
        .groupBy(window(col("event_time"), "5 minutes")) \
        .agg(
            spark_sum("total_amount").alias("revenue_5m"),
            count("*").alias("events_5m"),
            countDistinct("user_id").alias("users_5m")
        ) \
        .select(
            lit("revenue_5m").alias("metric_name"),
            col("revenue_5m").alias("metric_value"),
            current_timestamp().alias("last_updated")
        )
    
    query_kpi = kpi_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(upsert_realtime_metrics) \
        .queryName("shop_kpi") \
        .start()
    
    print("[Shop] Sales, Brand, Funnel, KPI queries started")
    print("=" * 60)
    
    # Await all
    spark.streams.awaitAnyTermination()
