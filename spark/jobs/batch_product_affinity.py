from pyspark.sql import SparkSession
from pyspark.sql.functions import col, collect_list, array_distinct
from pyspark.ml.fpm import FPGrowth
import sys

# Postgres Config
import os
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "driver": "org.postgresql.Driver"
}

def run():
    spark = SparkSession.builder \
        .appName("BatchProductAffinity") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    # Read Raw Data
    try:
        df = spark.read.parquet("s3a://raw/shop_events")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"No data found: {e}")
        return

    # Filter Purchase Events & Group by Session (Basket)
    # item_id should be product_id or product_name
    transactions = df.filter(col("event_type") == "purchase") \
        .groupBy("user_id") \
        .agg(collect_list("product_id").alias("items")) \
        .withColumn("items", array_distinct(col("items"))) # Remove dupes in same session

    # FP-Growth
    # minSupport: Minimum support required to be considered a frequent itemset (0.01 = 1%)
    # minConfidence: Minimum confidence for generating association rules (0.1 = 10%)
    fpGrowth = FPGrowth(itemsCol="items", minSupport=0.001, minConfidence=0.05)
    model = fpGrowth.fit(transactions)

    # Display frequent itemsets
    # model.freqItemsets.show()

    # Display generated association rules.
    rules = model.associationRules
    
    # Transform rules for DB columns (Arrays to String)
    # antecedents: [p1, p2] -> "p1,p2"
    rules_df = rules.select(
        col("antecedents").cast("string"),
        col("consequents").cast("string"),
        col("confidence"),
        col("lift"),
        col("support")
    )

    # Write to Postgres
    rules_df.write \
        .mode("overwrite") \
        .jdbc(DB_URL, "mart_product_association", properties=DB_PROPERTIES)
    
    print("Product Affinity Mart Updated")

if __name__ == "__main__":
    run()
