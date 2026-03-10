from pyspark.sql import SparkSession
from pyspark.sql.functions import col, collect_list, array_distinct, size, desc, lit
from pyspark.ml.fpm import FPGrowth
import argparse
from datetime import date, datetime, timedelta
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", type=str, default=None,
                        help="Target date (YYYY-MM-DD). Defaults to today.")
    args, _ = parser.parse_known_args()
    target = datetime.strptime(args.target_date, "%Y-%m-%d").date() if args.target_date else date.today()
    target_end = (target + timedelta(days=1)).isoformat()

    spark = SparkSession.builder \
        .appName("BatchBasketAnalysis") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minio123")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    # Read Raw Data
    try:
        df = spark.read.parquet("s3a://raw/shop_events")
    except Exception as e:
        print(f"No data found: {e}")
        return

    # Filter events up to target_date
    df = df.filter(col("event_time") < lit(target_end))

    # 1. Prepare Transactions (Group by session_id)
    # Filter for 'purchase' events and group items by session
    transactions = df.filter(col("event_type") == "purchase") \
        .groupBy("session_id") \
        .agg(collect_list("product_id").alias("items")) \
        .withColumn("items", array_distinct(col("items"))) \
        .filter(size(col("items")) > 1)  # Only sessions with >= 2 items

    tx_count = transactions.count()
    print(f"Analyzing {tx_count} transactions up to {target} (session-based)...")

    if tx_count == 0:
        print("No multi-item sessions found. Skipping FP-Growth.")
        return

    # 2. FP-Growth (Association Rules)
    fpGrowth = FPGrowth(itemsCol="items", minSupport=0.001, minConfidence=0.05)
    model = fpGrowth.fit(transactions)

    # 3. Get Rules & Filter
    rules = model.associationRules

    rules_df = rules.select(
        col("antecedent").cast("string").alias("antecedents"),
        col("consequent").cast("string").alias("consequents"),
        col("confidence"),
        col("lift"),
        col("support")
    ).filter("lift > 1.0") \
     .orderBy(desc("lift"))

    # 4. Write to Postgres — skip if 0 rules to prevent truncating existing data
    rules_count = rules_df.count()
    if rules_count == 0:
        print("FP-Growth produced 0 rules (lift > 1.0). Skipping write to preserve existing data.")
        return

    rules_df.write \
        .option("truncate", "true") \
        .mode("overwrite") \
        .jdbc(DB_URL, "mart_product_association", properties=DB_PROPERTIES)

    print(f"Basket Analysis Updated. Rules generated: {rules_count}")

    # Show top 20 rules for logs
    rules_df.show(20, truncate=False)

if __name__ == "__main__":
    run()
