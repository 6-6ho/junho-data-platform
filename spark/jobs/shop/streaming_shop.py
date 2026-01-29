import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, sum, approx_count_distinct, expr, lit, coalesce
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, LongType, TimestampType
from datetime import datetime

# Path setup for common modules if needed (though we use direct JDBC here)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Kafka Config
KAFKA_TOPIC = "shopping-events"
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

# Postgres Config
DB_URL = "jdbc:postgresql://postgres:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": "postgres",
    "driver": "org.postgresql.Driver"
}

# -------------------------------------------------------------------------
# SCHEMA DEFINITION
# -------------------------------------------------------------------------
# Event Example: 
# {"event_type": "purchase", "user_id": "u1", "price": 10000, "timestamp": "...", "brand": "Nike", ...}
SCHEMA = StructType([
    StructField("event_id", StringType()),
    StructField("event_type", StringType()),
    StructField("user_id", StringType()),
    StructField("product_id", StringType()),
    StructField("category", StringType()),
    StructField("brand", StringType()),
    StructField("price", DoubleType()),
    StructField("total_amount", DoubleType()), # Only for purchase
    StructField("quantity", IntegerType()),
    StructField("timestamp", StringType()),
    StructField("session_id", StringType()),
    StructField("device", StructType([
        StructField("type", StringType()),
        StructField("os", StringType())
    ]))
])

def create_spark_session():
    return (SparkSession.builder
        .appName("ShopStreamingAnalytics")
        .getOrCreate())

# -------------------------------------------------------------------------
# POSTGRES UPSERT LOGIC (foreachBatch)
# -------------------------------------------------------------------------

def write_realtime_metrics(batch_df, batch_id):
    """
    Writes KPI metrics to 'shop_realtime_metrics' table.
    KPIs: Active Users (5m), Total Revenue (Today), Total Orders (Today)
    """
    print(f"DEBUG: Processing batch {batch_id} with {batch_df.count()} rows")
    batch_df.persist()
    
    # 1. Total Revenue & Orders (Global Aggregation since start of day - approximate in stream)
    # Note: In pure streaming without state, 'total since start' is hard.
    # We will aggregate the CURRENT BATCH and use an atomic increment in DB? 
    # OR better: Maintain state in Spark with a long window (24h).
    # Let's use a 24h window sliding every 1 min for "Today's Stats".
    
    # Actually, the batch_df here comes from the aggregated query below.
    # Let's see how we structure the stream first.
    pass

# We will define separate writer functions for each logic

def upsert_hourly_sales(batch_df, batch_id):
    if batch_df.isEmpty(): return
    
    # Simple JDBC append - but we want UPSERT.
    # Spark JDBC doesn't support UPSERT natively nicely without custom dialects or INSERT ON CONFLICT.
    # We will use a custom approach: 
    # Read existing, join (too slow) OR use a specific Postgres approach.
    # For simplicity/robustness in this demo: Delete from DB for this window? No.
    # We'll use "INSERT ... ON CONFLICT" via a specialized driver option or raw SQL execution?
    # Actually, standard Spark JDBC 'overwrite' on a temp table and then merge is common.
    # But let's try standard Append and let the dashboard handle duplicates? 
    # NO, duplicates in money are bad.
    
    # Hack for Postgres Upsert via Spark:
    # Use 'dbtable' query with INSERT ON CONFLICT? No.
    # We will use the driver to execute a custom SQL for each row? Too slow.
    # Better: Write to staging table, then trigger SQL to merge.
    
    # Plan B (Simpler for this scope): 
    # Just Append. But we aggregate by Window in Spark with "Update" mode.
    # If using Update mode, we get ALL rows that changed.
    # If we append them to a log table, the dashboard can take `MAX(last_updated)`?
    # Let's try to overwrite the specific rows?
    
    # Let's just use Append for now and on the Dashboard side, 
    # query: SELECT ... FROM data GROUP BY window, category -> SUM? No.
    
    # OK, Real Solution:
    # Use `foreachBatch` to write dataframes to a temp table, then run a JDBC SQL command to Merge.
    
    # But wait, psycopg2 is not installed in the Spark Container standard image usually.
    # We rely on pure JDBC.
    # Let's assume we can tolerate "Last Win" semantics if we write to a table with no constraint?
    # No, we defined PK in schema. Append will fail on duplicate.
    
    # STRATEGY: 
    # 1. Write to `stg_shop_hourly_sales` (Truncate before write? or Append with Batch ID)
    # 2. But we can't easily run arbitrary SQL via Spark JDBC Writer.
    
    # ALTERNATIVE STRATEGY for Prototype:
    # Catch Exception? No.
    # Let's change the SQL Schema to NOT have PK? And dashboard does `SUM`.
    # No, that drifts values.
    # Let's use `saveMode("append")` but on table `shop_hourly_sales_log`.
    # Dashboard view: `create view shop_hourly_sales as select ... from log ... group by ...`
    # This is the Lambda Architecture "Speed Layer" approach. 
    # Let's do this! It's robust.
    
    batch_df.write \
        .mode("append") \
        .jdbc(DB_URL, "shop_hourly_sales_log", properties=DB_PROPERTIES)

def upsert_brand_stats(batch_df, batch_id):
    if batch_df.isEmpty(): return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_brand_stats_log", properties=DB_PROPERTIES)

def upsert_funnel_stats(batch_df, batch_id):
    if batch_df.isEmpty(): return
    batch_df.write.mode("append").jdbc(DB_URL, "shop_funnel_stats_log", properties=DB_PROPERTIES)

def upsert_realtime_metrics(batch_df, batch_id):
    if batch_df.isEmpty(): return
    # This table key is 'metric_name'.
    # We can write to log table too.
    batch_df.write.mode("append").jdbc(DB_URL, "shop_realtime_metrics_log", properties=DB_PROPERTIES)

def debug_raw(batch_df, batch_id):
    count = batch_df.count()
    print(f"DEBUG_RAW: Batch {batch_id} count: {count}")
    if count > 0:
        batch_df.show(1)

# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
def run():
    spark = create_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # 1. READ STREAM
    raw_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "earliest") \
        .load() \
        .select(from_json(col("value").cast("string"), SCHEMA).alias("data")) \
        .select("data.*") \
        .withColumn("event_time", col("timestamp").cast(TimestampType()))

    # Watermark for late data handling (10 mins)
    df = raw_df.withWatermark("event_time", "10 minutes")

    # -------------------------------------------------------
    # LOGIC 1: HOURLY SALES by CATEGORY
    # -------------------------------------------------------
    # Window: 1 hour, slide 5 min (updates frequently)
    sales_df = (df
        .filter("event_type = 'purchase'")
        .groupBy(
            window("event_time", "1 hour", "5 minutes"),
            "category"
        )
        .agg(
            sum("total_amount").alias("total_revenue"),
            count("event_id").alias("order_count"),
            (sum("total_amount") / count("event_id")).alias("avg_order_value")
        )
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "category", "total_revenue", "order_count", "avg_order_value"
        ))

    query_sales = sales_df.writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_hourly_sales) \
        .start()

    # -------------------------------------------------------
    # LOGIC 2: BRAND PERFORMANCE (Top Brands)
    # -------------------------------------------------------
    # Window: 1 hour, slide 5 min
    brand_df = (df
        .filter("event_type = 'purchase'")
        .groupBy(
            window("event_time", "1 hour", "5 minutes"),
            "brand"
        )
        .agg(
            sum("total_amount").alias("total_revenue"),
            count("event_id").alias("order_count")
        )
        .select(
            col("window.start").alias("window_start"),
            col("brand").alias("brand_name"),
            "total_revenue", "order_count"
        ))

    query_brand = brand_df.writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_brand_stats) \
        .start()

    # -------------------------------------------------------
    # LOGIC 3: FUNNEL STATS (Simplified Session Funnel)
    # -------------------------------------------------------
    # We aggregate counts of each event type in the window.
    # Conversion Rate approx = Purchase / View
    funnel_df = (df
        .groupBy(window("event_time", "1 hour", "5 minutes"))
        .agg(
            approx_count_distinct("session_id").alias("total_sessions"),
            sum(expr("case when event_type = 'view' then 1 else 0 end")).alias("view_count"),
            sum(expr("case when event_type = 'add_cart' then 1 else 0 end")).alias("cart_count"),
            sum(expr("case when event_type = 'purchase' then 1 else 0 end")).alias("purchase_count")
        )
        .withColumn("conversion_rate", lit(0.0))
        # Actually calculated here for log
        .withColumn("conversion_rate", (col("purchase_count") / coalesce(col("view_count"), lit(1))) * 100)
        .select(
            col("window.start").alias("window_start"),
            "total_sessions", "view_count", "cart_count", "purchase_count", "conversion_rate"
        ))

    query_funnel = funnel_df.writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_funnel_stats) \
        .start()

    # -------------------------------------------------------
    # LOGIC 4: REAL-TIME KPIs (Single Number Metrics)
    # -------------------------------------------------------
    # Active Users (Last 5 mins), Revenue (Last 1 hour sliding)
    # We format this into the 'metric_name', 'metric_value' structure
    
    # 4.1 Active Users (5m)
    active_users_df = (df
        .groupBy(window("event_time", "5 minutes", "1 minute"))
        .agg(approx_count_distinct("user_id").alias("metric_value"))
        .select(
            lit("active_users_5m").alias("metric_name"),
            col("metric_value").cast(DoubleType()),
            col("window.end").alias("last_updated")
        ))
        
    query_kpi_users = active_users_df.writeStream \
        .outputMode("update") \
        .foreachBatch(upsert_realtime_metrics) \
        .start()

    query_debug = df.writeStream \
        .foreachBatch(debug_raw) \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    run()
