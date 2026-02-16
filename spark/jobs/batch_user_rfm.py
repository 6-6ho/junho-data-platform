from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, max, datediff, current_date, lit, ntile
from pyspark.sql.window import Window
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
        .appName("BatchUserRFM") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    # Read Raw Data (Parquet)
    try:
        df = spark.read.parquet("s3a://raw/shop_events")
# ... (middle parts omitted, assuming replace_file_content works on chunks)
# Actually I need to split this into chunks if I can't match huge block.
# Let's use multi_replace.

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"No data found: {e}")
        return

    # Filter Purchase Events
    purchase_df = df.filter(col("event_type") == "purchase")

    # RFM Calculation
    # Recency: Days since last purchase
    # Frequency: Count of orders
    # Monetary: Sum of total_amount
    rfm_agg = purchase_df.groupBy("user_id").agg(
        datediff(current_date(), max("date")).alias("recency_days"),
        count("event_id").alias("frequency"),
        sum("total_amount").alias("monetary")
    )

    # Scoring (1-5) using Quantiles
    # Recency: Lower is better (5 is best)
    # Frequency: Higher is better
    # Monetary: Higher is better
    
    # Note: If not enough data, ntile might fail or give minimal groups.
    # Handling small data gracefully
    if rfm_agg.count() < 10:
        print("Not enough data for Quantiles, using simple logic")
        rfm_scored = rfm_agg.withColumn("r_score", lit(5)) \
                            .withColumn("f_score", lit(5)) \
                            .withColumn("m_score", lit(5))
    else:
        window_spec = Window.orderBy("recency_days") # ASC
        window_spec_desc = Window.orderBy(col("frequency").desc())
        window_spec_money = Window.orderBy(col("monetary").desc())
        
        # Calculate percentiles roughly or use ntile
        rfm_scored = rfm_agg \
            .withColumn("r_score", ntile(5).over(Window.orderBy(col("recency_days").desc()))) \
            .withColumn("f_score", ntile(5).over(Window.orderBy("frequency"))) \
            .withColumn("m_score", ntile(5).over(Window.orderBy("monetary")))
            
            # Simple Fix for Recency Score: Recent = Low Days = High Score
            # Original ntile(5).over(orderBy(recency desc)) -> High days (old) get 5?? No.
            # We want Low Days -> 5.
            # So order by recency desc: High days (Old) -> Rank 1?
            # Let's adjust: Order by recency DESC assigns 1 to Biggest Recency (Oldest).
            # So 5 is Smallest Recency (Newest). Correct.
    
    # Segment Logic
    # 555 -> VIP
    # 111 -> Lost
    # etc.
    final_df = rfm_scored.withColumn("rfm_segment", 
        expr("""
            CASE 
                WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'VIP'
                WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
                WHEN r_score <= 2 AND recency_days <= 10 THEN 'New Potential'
                WHEN r_score <= 2 THEN 'Risk'
                ELSE 'Regular'
            END
        """)
    )

    # Write to Postgres
    final_df.write \
        .mode("overwrite") \
        .jdbc(DB_URL, "mart_user_rfm", properties=DB_PROPERTIES)
    
    print("User RFM Mart Updated")

if __name__ == "__main__":
    run()
