"""
Export Trade Performance Timeseries to Iceberg

Reads JSONB data from Postgres (trade_performance_timeseries, signal_raw_snapshot)
and writes flat columnar tables to Iceberg on MinIO.

Usage:
  spark-submit ... export_timeseries_to_iceberg.py --target-date 2026-03-14
  spark-submit ... export_timeseries_to_iceberg.py --backfill
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pyspark.sql.functions import (
    col, explode, from_json, to_date
)
from pyspark.sql.types import (
    MapType, StringType, StructType, StructField,
    DoubleType, BooleanType
)

from common.spark_utils import create_spark_session, ensure_namespace

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "driver": "org.postgresql.Driver",
}

# JSONB value schema: {"price": 100.5, "profit_pct": 1.2, "is_win": true}
TIMESERIES_VALUE_SCHEMA = StructType([
    StructField("price", DoubleType()),
    StructField("profit_pct", DoubleType()),
    StructField("is_win", BooleanType()),
])
TIMESERIES_MAP_SCHEMA = MapType(StringType(), TIMESERIES_VALUE_SCHEMA)


def create_iceberg_tables(spark):
    """Create Iceberg tables if they don't exist."""
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.trade.performance_timeseries (
            symbol STRING,
            alert_type STRING,
            alert_time TIMESTAMP,
            entry_price DOUBLE,
            time_min INT,
            close_price DOUBLE,
            profit_pct DOUBLE,
            is_win BOOLEAN,
            alert_date DATE
        ) USING iceberg
        PARTITIONED BY (alert_date)
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.trade.signal_raw_snapshot (
            symbol STRING,
            alert_time TIMESTAMP,
            entry_price DOUBLE,
            klines_json STRING,
            alert_date DATE
        ) USING iceberg
        PARTITIONED BY (alert_date)
    """)


def export_timeseries(spark, target_date=None):
    """Export trade_performance_timeseries JSONB → Iceberg flat rows.

    Per signal: 1 JSONB row → ~60 flat rows (1 per minute).
    """
    if target_date:
        query = f"""(
            SELECT symbol, alert_type, alert_time, entry_price,
                   timeseries_data::text AS timeseries_json
            FROM trade_performance_timeseries
            WHERE alert_time::date = '{target_date}'
        ) AS t"""
    else:
        query = """(
            SELECT symbol, alert_type, alert_time, entry_price,
                   timeseries_data::text AS timeseries_json
            FROM trade_performance_timeseries
        ) AS t"""

    df = spark.read.jdbc(DB_URL, query, properties=DB_PROPERTIES)
    count = df.count()
    if count == 0:
        print(f"No timeseries data for {target_date or 'all dates'}")
        return

    print(f"Exporting {count} timeseries records")

    # Parse JSONB string → Map → explode to flat rows
    parsed = df.withColumn(
        "ts_map", from_json(col("timeseries_json"), TIMESERIES_MAP_SCHEMA)
    )

    exploded = parsed.select(
        "symbol", "alert_type", "alert_time", "entry_price",
        explode(col("ts_map")).alias("time_key", "data")
    )

    flat = exploded.select(
        "symbol", "alert_type", "alert_time", "entry_price",
        col("time_key").cast("int").alias("time_min"),
        col("data.price").alias("close_price"),
        col("data.profit_pct").alias("profit_pct"),
        col("data.is_win").alias("is_win"),
        to_date(col("alert_time")).alias("alert_date"),
    )

    # Idempotent write: delete partition(s) then append
    if target_date:
        spark.sql(f"""
            DELETE FROM iceberg.trade.performance_timeseries
            WHERE alert_date = DATE '{target_date}'
        """)
    else:
        # Backfill: truncate entire table
        spark.sql("DELETE FROM iceberg.trade.performance_timeseries WHERE 1=1")

    flat.writeTo("iceberg.trade.performance_timeseries").append()
    print(f"Wrote {flat.count()} flat timeseries rows to Iceberg")


def export_raw_snapshots(spark, target_date=None):
    """Export signal_raw_snapshot JSONB → Iceberg (klines as string)."""
    if target_date:
        query = f"""(
            SELECT symbol, alert_time, entry_price,
                   klines_1m::text AS klines_json
            FROM signal_raw_snapshot
            WHERE alert_time::date = '{target_date}'
        ) AS t"""
    else:
        query = """(
            SELECT symbol, alert_time, entry_price,
                   klines_1m::text AS klines_json
            FROM signal_raw_snapshot
        ) AS t"""

    df = spark.read.jdbc(DB_URL, query, properties=DB_PROPERTIES)
    count = df.count()
    if count == 0:
        print(f"No raw snapshots for {target_date or 'all dates'}")
        return

    print(f"Exporting {count} raw snapshot records")

    result = df.withColumn("alert_date", to_date(col("alert_time")))

    if target_date:
        spark.sql(f"""
            DELETE FROM iceberg.trade.signal_raw_snapshot
            WHERE alert_date = DATE '{target_date}'
        """)
    else:
        spark.sql("DELETE FROM iceberg.trade.signal_raw_snapshot WHERE 1=1")

    result.writeTo("iceberg.trade.signal_raw_snapshot").append()
    print(f"Wrote {count} raw snapshot rows to Iceberg")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", type=str, default=None,
                        help="Target date (YYYY-MM-DD). If omitted with --backfill, exports all.")
    parser.add_argument("--backfill", action="store_true",
                        help="Export all historical data")
    args = parser.parse_args()

    if not args.target_date and not args.backfill:
        # Default: yesterday
        args.target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    target = args.target_date if not args.backfill else None
    mode = "backfill (all)" if args.backfill else f"date={target}"
    print(f"Export mode: {mode}")

    spark = create_spark_session("ExportTimeseries")

    ensure_namespace(spark, "iceberg.trade")
    create_iceberg_tables(spark)

    try:
        export_timeseries(spark, target)
        export_raw_snapshots(spark, target)
        print("Export completed successfully")
    except Exception as e:
        print(f"Export failed: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
