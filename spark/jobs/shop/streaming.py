"""
Spark Streaming Job: Shopping Events
Reads shopping events from Kafka and writes to Iceberg tables.
"""

import sys
import os

# Adjust path to import common
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pyspark.sql.functions import (
    col, from_json, to_timestamp, hour
)
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType
)

from common.spark_utils import (
    create_spark_session,
    ensure_namespace,
    get_checkpoint_path,
    SparkConfig
)


def get_shopping_event_schema():
    """Define schema for shopping events."""
    device_schema = StructType([
        StructField("type", StringType(), True),
        StructField("os", StringType(), True),
        StructField("app_version", StringType(), True)
    ])

    campaign_schema = StructType([
        StructField("id", StringType(), True),
        StructField("name", StringType(), True)
    ])

    context_schema = StructType([
        StructField("referrer", StringType(), True),
        StructField("campaign", campaign_schema, True)
    ])

    return StructType([
        StructField("event_id", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("product_name", StringType(), True),
        StructField("category", StringType(), True),
        StructField("brand", StringType(), True),
        StructField("price", IntegerType(), True),
        StructField("timestamp", StringType(), True),
        StructField("session_id", StringType(), True),
        StructField("device", device_schema, True),
        StructField("context", context_schema, True),
        StructField("quantity", IntegerType(), True),
        StructField("total_amount", IntegerType(), True),
        StructField("payment_method", StringType(), True)
    ])


def create_iceberg_table(spark):
    """Create Iceberg table if not exists."""
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.shopping.events (
            event_id STRING,
            event_type STRING,
            user_id STRING,
            product_id STRING,
            product_name STRING,
            category STRING,
            brand STRING,
            price INT,
            event_timestamp TIMESTAMP,
            session_id STRING,
            device_type STRING,
            device_os STRING,
            device_app_version STRING,
            referrer STRING,
            campaign_id STRING,
            campaign_name STRING,
            quantity INT,
            total_amount INT,
            payment_method STRING,
            event_date DATE,
            event_hour INT
        )
        USING iceberg
        PARTITIONED BY (event_date, event_type)
    """)
    print("Iceberg table created/verified: iceberg.shopping.events")


def process_shopping_events(spark):
    """Read from Kafka and write to Iceberg."""
    schema = get_shopping_event_schema()
    config = SparkConfig()

    # Read from Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", "shopping-events") \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()

    # Parse JSON
    parsed_df = kafka_df \
        .select(from_json(col("value").cast("string"), schema).alias("data")) \
        .select("data.*")
    
    # Filter out null events
    parsed_df = parsed_df.filter(col("event_id").isNotNull())

    # Transform
    transformed_df = parsed_df \
        .withColumn("event_timestamp", to_timestamp(col("timestamp"))) \
        .withColumn("event_date", col("event_timestamp").cast("date")) \
        .withColumn("event_hour", hour(col("event_timestamp"))) \
        .withColumn("device_type", col("device.type")) \
        .withColumn("device_os", col("device.os")) \
        .withColumn("device_app_version", col("device.app_version")) \
        .withColumn("referrer", col("context.referrer")) \
        .withColumn("campaign_id", col("context.campaign.id")) \
        .withColumn("campaign_name", col("context.campaign.name")) \
        .drop("timestamp", "device", "context")

    # Select columns
    final_df = transformed_df.select(
        "event_id", "event_type", "user_id", "product_id", "product_name", 
        "category", "brand", "price", "event_timestamp", "session_id",
        "device_type", "device_os", "device_app_version", "referrer",
        "campaign_id", "campaign_name", "quantity", "total_amount", 
        "payment_method", "event_date", "event_hour"
    )

    # Write to Iceberg
    checkpoint_path = get_checkpoint_path("shopping-events")
    
    query = final_df \
        .writeStream \
        .format("iceberg") \
        .outputMode("append") \
        .option("checkpointLocation", checkpoint_path) \
        .option("fanout-enabled", "true") \
        .toTable("iceberg.shopping.events")

    return query


def main():
    print("Starting Shopping Events Streaming Job...")
    spark = create_spark_session("ShoppingEventsStreaming", enable_streaming=True)

    ensure_namespace(spark, "iceberg.shopping")
    create_iceberg_table(spark)

    query = process_shopping_events(spark)

    print("Streaming started. Waiting for data...")
    query.awaitTermination()


if __name__ == "__main__":
    main()
