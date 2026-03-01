from pyspark.sql import SparkSession
from pyspark.sql.functions import col, collect_list, array_distinct, expr, size, desc
from pyspark.ml.fpm import FPGrowth
import sys
import os

# Postgres Config
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "driver": "org.postgresql.Driver"
}

def run():
    spark = SparkSession.builder \
        .appName("BatchBasketAnalysis") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minio123")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    # Read Raw Data (Parquet from Iceberg/MinIO raw zone)
    try:
        # Scan all available raw data
        df = spark.read.parquet("s3a://raw/shop_events")
    except Exception as e:
        print(f"No data found: {e}")
        return

    # 1. Prepare Transactions (Group by Session)
    # Filter for 'purchase' events and group items by session_id
    transactions = df.filter(col("event_type") == "purchase") \
        .groupBy("session_id") \
        .agg(collect_list("product_name").alias("items")) \
        .withColumn("items", array_distinct(col("items"))) \
        .filter(size(col("items")) > 1)  # Only sessions with >= 2 items

    print(f"Analyzing {transactions.count()} transactions...")

    # 2. FP-Growth (Association Rules)
    # minSupport=0.001 (0.1%): Allow niche combinations
    # minConfidence=0.05 (5%): Low bar for confidence to catch interesting but rare associations
    fpGrowth = FPGrowth(itemsCol="items", minSupport=0.001, minConfidence=0.05)
    model = fpGrowth.fit(transactions)

    # 3. Get Rules & Filter "Obvious" ones
    rules = model.associationRules
    
    # Filter by Lift > 1.2 to find meaningful associations
    rules_df = rules.select(
        col("antecedents").cast("string").alias("item_a"),
        col("consequents").cast("string").alias("item_b"),
        col("confidence"),
        col("lift"),
        col("support")
    ).filter("lift > 1.2") \
     .orderBy(desc("lift"))  # Order by Relevance (Lift)

    # 4. Write to Postgres
    # Use 'mart_basket_analysis' table
    rules_df.write \
        .mode("overwrite") \
        .jdbc(DB_URL, "mart_basket_analysis", properties=DB_PROPERTIES)
    
    print(f"Basket Analysis Updated. Rules generated: {rules_df.count()}")
    
    # Show top 20 rules for logs
    rules_df.show(20, truncate=False)

if __name__ == "__main__":
    run()
