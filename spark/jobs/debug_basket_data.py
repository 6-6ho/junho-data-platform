from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, size, collect_list, array_distinct
import os

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio123")

def debug():
    spark = SparkSession.builder \
        .appName("BasketDataDebug") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    print("--- Debugging Shop Events Data ---")
    try:
        df = spark.read.parquet("s3a://raw/shop_events")
        df.createOrReplaceTempView("events")
        
        # 1. Basic Counts
        total_rows = df.count()
        purchases = df.filter(col("event_type") == "purchase")
        total_purchases = purchases.count()
        print(f"Total Rows: {total_rows}")
        print(f"Total Purchases: {total_purchases}")
        
        if total_purchases == 0:
            print("NO PURCHASES FOUND!")
            return

        # 2. Session Analysis
        sessions = purchases.groupBy("session_id").agg(collect_list("product_id").alias("items"))
        sessions = sessions.withColumn("num_items", size(col("items")))
        
        total_sessions = sessions.count()
        multi_item_sessions = sessions.filter(col("num_items") > 1).count()
        
        print(f"Total Purchase Sessions: {total_sessions}")
        print(f"Multi-item Sessions: {multi_item_sessions}")
        
        if multi_item_sessions == 0:
            print("NO MULTI-ITEM SESSIONS! FPGrowth will fail.")
        
        # 3. Sample Data
        print("Sample Sessions:")
        sessions.orderBy(col("num_items").desc()).show(5, truncate=False)
        
    except Exception as e:
        print(f"Error reading data: {e}")

if __name__ == "__main__":
    debug()
