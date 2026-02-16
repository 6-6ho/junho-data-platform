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
    count, avg, approx_count_distinct, lit, current_timestamp
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
    "password": os.getenv("POSTGRES_PASSWORD", ""),
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
    StructField("payment_method", StringType()),  # DQ 집계용
    StructField("timestamp", StringType()),
    StructField("session_id", StringType()),
    StructField("device", StructType([
        StructField("type", StringType()),
        StructField("os", StringType())
    ]))
])

# =========================================================================
# SHOP PROCESSING LOGIC (Postgres Only)
# =========================================================================
def upsert_hourly_sales(batch_df, batch_id):
    cnt = batch_df.count()
    print(f"[DEBUG] Sales Batch {batch_id}: {cnt} rows")
    if cnt == 0:
        return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_hourly_sales_log", properties=DB_PROPERTIES)

def upsert_brand_stats(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_brand_stats_log", properties=DB_PROPERTIES)

def upsert_funnel_stats(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_funnel_stats_log", properties=DB_PROPERTIES)

def upsert_realtime_metrics(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_realtime_metrics_log", properties=DB_PROPERTIES)


# =========================================================================
# DQ (DATA QUALITY) PROCESSING LOGIC
# =========================================================================
def process_dq_category_hourly(batch_df, batch_id):
    """카테고리별 시간당 DQ 집계"""
    cnt = batch_df.count()
    if cnt == 0:
        return
    print(f"[DQ] Category Hourly Batch {batch_id}: {cnt} rows")
    batch_df.write.mode("append").jdbc(DB_URL, "dq_category_hourly", properties=DB_PROPERTIES)

def process_dq_payment_hourly(batch_df, batch_id):
    """결제수단별 시간당 DQ 집계"""
    if batch_df.isEmpty():
        return
    print(f"[DQ] Payment Hourly Batch {batch_id}")
    batch_df.write.mode("append").jdbc(DB_URL, "dq_payment_hourly", properties=DB_PROPERTIES)

def process_dq_anomaly_raw(batch_df, batch_id):
    """이상 가격 데이터 격리 저장"""
    cnt = batch_df.count()
    if cnt == 0:
        return
    print(f"[DQ] ⚠️ Anomaly Raw Batch {batch_id}: {cnt} anomalies detected!")
    batch_df.write.mode("append").jdbc(DB_URL, "dq_anomaly_raw", properties=DB_PROPERTIES)


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
    # Note: Skipping DDL as tables are created on first write
    # The namespace and tables will be auto-created by Iceberg
    print("[Iceberg] Skipping DDL - tables will be created on first write")
    
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
            approx_count_distinct("session_id").alias("total_sessions"),
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
            approx_count_distinct("user_id").alias("users_5m")
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
    
    # =========================================================================
    # DQ (DATA QUALITY) STREAMS
    # =========================================================================
    
    # --- DQ: 카테고리별 시간당 이벤트/매출 집계 ---
    dq_category_df = shop_df \
        .groupBy(
            window(col("event_time"), "1 hour").alias("hour_window"),
            col("category")
        ) \
        .agg(
            count("*").alias("event_count"),
            spark_sum((col("event_type") == "purchase").cast("int")).alias("purchase_count"),
            spark_sum("total_amount").alias("total_revenue")
        ) \
        .select(
            col("hour_window.start").alias("hour"),
            col("category"),
            col("event_count"),
            col("purchase_count"),
            col("total_revenue")
        )
    
    query_dq_category = dq_category_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='1 minute') \
        .foreachBatch(process_dq_category_hourly) \
        .queryName("dq_category") \
        .start()
    
    # --- DQ: 결제수단별 시간당 집계 (purchase만) ---
    dq_payment_df = shop_df \
        .filter(col("event_type") == "purchase") \
        .filter(col("payment_method").isNotNull()) \
        .groupBy(
            window(col("event_time"), "1 hour").alias("hour_window"),
            col("payment_method")
        ) \
        .agg(
            count("*").alias("purchase_count"),
            spark_sum("total_amount").alias("total_revenue")
        ) \
        .select(
            col("hour_window.start").alias("hour"),
            col("payment_method"),
            col("purchase_count"),
            col("total_revenue")
        )
    
    query_dq_payment = dq_payment_df.writeStream \
        .outputMode("update") \
        .trigger(processingTime='1 minute') \
        .foreachBatch(process_dq_payment_hourly) \
        .queryName("dq_payment") \
        .start()
    
    # --- DQ: 이상 가격 데이터 감지 및 격리 ---
    dq_anomaly_df = shop_df \
        .filter(
            (col("price") < 0) | 
            (col("price") == 0) | 
            (col("price") > 10000000)  # 천만원 이상
        ) \
        .withColumn("anomaly_reason",
            lit("abnormal_price")
        ) \
        .select(
            col("event_id"),
            col("event_type"),
            col("user_id"),
            col("product_id"),
            col("category"),
            col("price"),
            col("total_amount"),
            col("event_time").alias("timestamp"),
            col("anomaly_reason")
        )
    
    query_dq_anomaly = dq_anomaly_df.writeStream \
        .outputMode("append") \
        .trigger(processingTime='30 seconds') \
        .foreachBatch(process_dq_anomaly_raw) \
        .queryName("dq_anomaly") \
        .start()
    
    print("[Shop] Sales, Brand, Funnel, KPI queries started")
    print("[DQ] Category, Payment, Anomaly queries started")
    print("=" * 60)
    
    # Await all
    spark.streams.awaitAnyTermination()

