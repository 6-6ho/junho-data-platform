"""
Spark Batch Job: Daily Aggregation
Performs daily aggregations on shopping events for reporting.
Scheduled via Airflow DAG.
"""

import sys
import os
from datetime import datetime, timedelta

# Add common module to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pyspark.sql.functions import (
    col, count, sum as spark_sum, avg, countDistinct, when, lit, round as spark_round
)
from pyspark.sql import Row

from common.spark_utils import (
    create_spark_session,
    ensure_namespace,
    run_idempotent_overwrite
)


def create_daily_tables(spark):
    """Create daily aggregation tables."""
    # Daily summary
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.shopping.daily_summary (
            report_date DATE,
            total_events LONG,
            unique_users LONG,
            total_revenue LONG,
            total_orders LONG,
            avg_order_value DOUBLE,
            conversion_rate DOUBLE,
            views LONG,
            cart_adds LONG,
            created_at TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (months(report_date))
    """)

    # Hourly breakdown
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.shopping.hourly_metrics (
            report_date DATE,
            hour INT,
            events LONG,
            revenue LONG,
            orders LONG,
            unique_users LONG
        )
        USING iceberg
        PARTITIONED BY (report_date)
    """)

    # Category daily
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.shopping.daily_category (
            report_date DATE,
            category STRING,
            events LONG,
            revenue LONG,
            orders LONG,
            unique_products LONG,
            top_product_id STRING
        )
        USING iceberg
        PARTITIONED BY (report_date)
    """)

    # Product performance
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.shopping.daily_product (
            report_date DATE,
            product_id STRING,
            product_name STRING,
            category STRING,
            views LONG,
            cart_adds LONG,
            purchases LONG,
            revenue LONG,
            conversion_rate DOUBLE
        )
        USING iceberg
        PARTITIONED BY (report_date)
    """)
    print("Daily aggregation tables created")


def run_daily_summary(spark, target_date: str):
    """Generate daily summary metrics."""
    print(f"Generating daily summary for {target_date}")

    events_df = spark.read.table("iceberg.shopping.events") \
        .filter(col("event_date") == target_date)

    if events_df.count() == 0:
        print(f"No data for {target_date}")
        return

    summary = events_df.agg(
        count("*").alias("total_events"),
        countDistinct("user_id").alias("unique_users"),
        spark_sum(when(col("event_type") == "purchase", col("total_amount")).otherwise(0)).alias("total_revenue"),
        spark_sum((col("event_type") == "purchase").cast("long")).alias("total_orders"),
        spark_sum((col("event_type") == "view").cast("long")).alias("views"),
        spark_sum((col("event_type") == "add_cart").cast("long")).alias("cart_adds")
    ).collect()[0]

    avg_order = summary.total_revenue / summary.total_orders if summary.total_orders > 0 else 0
    conversion = summary.total_orders / summary.unique_users if summary.unique_users > 0 else 0

    summary_df = spark.createDataFrame([Row(
        report_date=datetime.strptime(target_date, "%Y-%m-%d").date(),
        total_events=summary.total_events,
        unique_users=summary.unique_users,
        total_revenue=summary.total_revenue or 0,
        total_orders=summary.total_orders,
        avg_order_value=float(avg_order),
        conversion_rate=float(conversion),
        views=summary.views,
        cart_adds=summary.cart_adds,
        created_at=datetime.now()
    )])

    run_idempotent_overwrite(
        spark=spark,
        df=summary_df,
        table_name="iceberg.shopping.daily_summary",
        partition_col="report_date",
        partition_value=target_date
    )
    
    # Also write to JDBC for Dashboard (Postgres)
    write_to_postgres(summary_df, "analytics_daily_summary")
    print(f"Daily summary saved: {summary.total_events} events")


def run_hourly_breakdown(spark, target_date: str):
    """Generate hourly metrics breakdown."""
    events_df = spark.read.table("iceberg.shopping.events").filter(col("event_date") == target_date)

    hourly_df = events_df.groupBy("event_hour") \
        .agg(
            count("*").alias("events"),
            spark_sum(when(col("event_type") == "purchase", col("total_amount")).otherwise(0)).alias("revenue"),
            spark_sum((col("event_type") == "purchase").cast("long")).alias("orders"),
            countDistinct("user_id").alias("unique_users")
        ) \
        .withColumn("report_date", lit(target_date).cast("date")) \
        .withColumnRenamed("event_hour", "hour")

    run_idempotent_overwrite(
        spark=spark,
        df=hourly_df,
        table_name="iceberg.shopping.hourly_metrics",
        partition_col="report_date",
        partition_value=target_date
    )
    # write_to_postgres(hourly_df, "analytics_hourly_metrics") # Optional for dashboard
    print("Hourly breakdown saved")


def run_category_aggregation(spark, target_date: str):
    """Generate category-level daily metrics."""
    events_df = spark.read.table("iceberg.shopping.events").filter(col("event_date") == target_date)

    category_df = events_df.groupBy("category") \
        .agg(
            count("*").alias("events"),
            spark_sum(when(col("event_type") == "purchase", col("total_amount")).otherwise(0)).alias("revenue"),
            spark_sum((col("event_type") == "purchase").cast("long")).alias("orders"),
            countDistinct("product_id").alias("unique_products")
        ) \
        .withColumn("report_date", lit(target_date).cast("date")) \
        .withColumn("top_product_id", lit(None).cast("string"))

    run_idempotent_overwrite(
        spark=spark,
        df=category_df,
        table_name="iceberg.shopping.daily_category",
        partition_col="report_date",
        partition_value=target_date
    )
    print("Category metrics saved")


def run_product_aggregation(spark, target_date: str):
    """Generate product-level daily metrics."""
    events_df = spark.read.table("iceberg.shopping.events").filter(col("event_date") == target_date)

    product_df = events_df.groupBy("product_id", "product_name", "category") \
        .agg(
            spark_sum((col("event_type") == "view").cast("long")).alias("views"),
            spark_sum((col("event_type") == "add_cart").cast("long")).alias("cart_adds"),
            spark_sum((col("event_type") == "purchase").cast("long")).alias("purchases"),
            spark_sum(when(col("event_type") == "purchase", col("total_amount")).otherwise(0)).alias("revenue")
        ) \
        .withColumn("report_date", lit(target_date).cast("date")) \
        .withColumn("conversion_rate", spark_round(col("purchases") / col("views") * 100, 2)) \
        .filter(col("views") > 0)

    run_idempotent_overwrite(
        spark=spark,
        df=product_df,
        table_name="iceberg.shopping.daily_product",
        partition_col="report_date",
        partition_value=target_date
    )
    print("Product metrics saved")


def write_to_postgres(df, table_name):
    """Write DataFrame to Postgres (Dashboard DB)."""
    # Note: Using shop_analytics DB running on 'postgres' host
    # This requires pg driver which is already in our dependencies
    jdbc_url = "jdbc:postgresql://postgres:5432/shop_analytics"
    props = {
        "user": "postgres",
        "password": "postgres",
        "driver": "org.postgresql.Driver"
    }
    try:
        df.write.jdbc(url=jdbc_url, table=table_name, mode="append", properties=props)
        print(f"Synced to Postgres table {table_name}")
    except Exception as e:
        print(f"Failed to write to Postgres: {e}")


def main():
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"Starting daily aggregation for {target_date}")
    spark = create_spark_session("DailyAggregation")

    ensure_namespace(spark, "iceberg.shopping")
    create_daily_tables(spark)

    try:
        run_daily_summary(spark, target_date)
        run_hourly_breakdown(spark, target_date)
        run_category_aggregation(spark, target_date)
        run_product_aggregation(spark, target_date)
        print(f"Aggregation completed for {target_date}")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
