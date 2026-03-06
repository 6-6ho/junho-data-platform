from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, max, datediff, current_date, current_timestamp, lit, ntile, expr, to_date
from pyspark.sql.window import Window
import os

from rfm_segment import classify_rfm  # noqa: F401 — re-export for backwards compat

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
        .appName("BatchUserRFM") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minio123")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    # Read Raw Data - scan ALL available data (no date filter)
    try:
        df = spark.read.parquet("s3a://raw/shop_events")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"No data found: {e}")
        return

    # Filter Purchase Events and add date column for Recency calculation
    purchase_df = df.filter(col("event_type") == "purchase") \
                    .withColumn("purchase_date", to_date("event_time")) \
                    .repartition(8, "user_id")

    # RFM Calculation
    # Recency: Days since last purchase
    # Frequency: Count of orders
    # Monetary: Sum of total_amount
    rfm_agg = purchase_df.groupBy("user_id").agg(
        datediff(current_date(), max("purchase_date")).alias("recency"),
        count("event_id").alias("frequency"),
        sum("total_amount").alias("monetary")
    )

    user_count = rfm_agg.count()
    print(f"RFM analysis for {user_count} users")

    # Scoring (1-5) using Quantiles
    # Recency: Lower days = better = higher score (order DESC so lowest days get rank 5)
    # Frequency: Higher is better
    # Monetary: Higher is better
    if user_count < 10:
        print("Not enough data for quantiles, assigning default scores (3/3/3 = Regular)")
        rfm_scored = rfm_agg.withColumn("r_score", lit(3)) \
                            .withColumn("f_score", lit(3)) \
                            .withColumn("m_score", lit(3))
    else:
        rfm_scored = rfm_agg \
            .withColumn("r_score", ntile(5).over(Window.orderBy(col("recency").desc()))) \
            .withColumn("f_score", ntile(5).over(Window.orderBy("frequency"))) \
            .withColumn("m_score", ntile(5).over(Window.orderBy("monetary")))

    # Segment Logic (METRICS_DEFINITION.md 기준)
    # VIP:     R >= 4 AND F >= 4 AND M >= 4
    # Loyal:   F >= 3
    # Risk:    R <= 2
    # New:     R >= 4 AND F <= 2
    # Regular: 나머지
    final_df = rfm_scored.withColumn("rfm_segment",
        expr("""
            CASE
                WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'VIP'
                WHEN f_score >= 3 THEN 'Loyal'
                WHEN r_score <= 2 THEN 'Risk'
                WHEN r_score >= 4 AND f_score <= 2 THEN 'New'
                ELSE 'Regular'
            END
        """)
    ).withColumn("updated_at", current_timestamp())

    # Select columns matching DDL (04_shop_mart.sql)
    output_df = final_df.select(
        "user_id", "recency", "frequency", "monetary",
        "r_score", "f_score", "m_score", "rfm_segment", "updated_at"
    )

    # Write to Postgres
    output_df.write \
        .option("truncate", "true") \
        .mode("overwrite") \
        .jdbc(DB_URL, "mart_user_rfm", properties=DB_PROPERTIES)

    print("User RFM Mart Updated")

    # Show segment distribution
    output_df.groupBy("rfm_segment").count().orderBy(col("count").desc()).show()

if __name__ == "__main__":
    run()
