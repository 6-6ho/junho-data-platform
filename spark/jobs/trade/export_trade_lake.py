"""
Trade Historical Data Lake — Iceberg Export

Postgres 서빙 테이블의 일일 스냅샷을 Iceberg에 아카이빙.
Iceberg의 time travel + 파티션 프루닝으로 과거 데이터 조회 가능.

Tables:
  iceberg.trade.market_history    — 전종목 가격 일일 스냅샷
  iceberg.trade.movers_history    — 탐지된 급등/급락 신호 아카이브
  iceberg.trade.dq_history        — DQ 심볼별 시간 집계 아카이브

Usage:
  spark-submit ... export_trade_lake.py --target-date 2026-04-01
  spark-submit ... export_trade_lake.py --backfill
"""
import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pyspark.sql.functions import col, lit, current_timestamp, to_date
from common.spark_utils import create_spark_session, ensure_namespace

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "driver": "org.postgresql.Driver",
}


def create_lake_tables(spark):
    """Create Iceberg lake tables."""
    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.trade.market_history (
            symbol STRING,
            price DOUBLE,
            change_pct_24h DOUBLE,
            volume_24h DOUBLE,
            change_pct_window DOUBLE,
            event_time TIMESTAMP,
            snapshot_date DATE
        ) USING iceberg
        PARTITIONED BY (snapshot_date)
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.trade.movers_history (
            type STRING,
            symbol STRING,
            status STRING,
            window STRING,
            event_time TIMESTAMP,
            change_pct_window DOUBLE,
            snapshot_date DATE
        ) USING iceberg
        PARTITIONED BY (snapshot_date)
    """)

    spark.sql("""
        CREATE TABLE IF NOT EXISTS iceberg.trade.dq_history (
            hour TIMESTAMP,
            symbol STRING,
            tick_count INT,
            avg_price DOUBLE,
            volume DOUBLE,
            snapshot_date DATE
        ) USING iceberg
        PARTITIONED BY (snapshot_date)
    """)


def export_market_snapshot(spark, target_date):
    """market_snapshot 전종목 가격 → Iceberg 일일 스냅샷."""
    df = spark.read.jdbc(
        DB_URL,
        "(SELECT symbol, price, change_pct_24h, volume_24h, change_pct_window, event_time FROM market_snapshot) AS t",
        properties=DB_PROPERTIES,
    )
    count = df.count()
    if count == 0:
        print(f"[Lake] No market_snapshot data")
        return

    result = df.withColumn("snapshot_date", lit(target_date).cast("date"))

    # 멱등성: 해당 날짜 파티션 삭제 후 재적재
    spark.sql(f"DELETE FROM iceberg.trade.market_history WHERE snapshot_date = DATE '{target_date}'")
    result.writeTo("iceberg.trade.market_history").append()
    print(f"[Lake] market_history: {count} symbols archived for {target_date}")


def export_movers(spark, target_date):
    """movers_latest 신호 → Iceberg 아카이브."""
    query = f"""(
        SELECT type, symbol, status, window, event_time, change_pct_window
        FROM movers_latest
        WHERE event_time::date = '{target_date}'
    ) AS t"""
    df = spark.read.jdbc(DB_URL, query, properties=DB_PROPERTIES)
    count = df.count()
    if count == 0:
        print(f"[Lake] No movers for {target_date}")
        return

    result = df.withColumn("snapshot_date", lit(target_date).cast("date"))
    spark.sql(f"DELETE FROM iceberg.trade.movers_history WHERE snapshot_date = DATE '{target_date}'")
    result.writeTo("iceberg.trade.movers_history").append()
    print(f"[Lake] movers_history: {count} signals archived for {target_date}")


def export_dq_metrics(spark, target_date):
    """dq_trade_symbol_hourly → Iceberg 아카이브."""
    query = f"""(
        SELECT hour, symbol, tick_count, avg_price, volume
        FROM dq_trade_symbol_hourly
        WHERE hour::date = '{target_date}'
    ) AS t"""
    df = spark.read.jdbc(DB_URL, query, properties=DB_PROPERTIES)
    count = df.count()
    if count == 0:
        print(f"[Lake] No DQ metrics for {target_date}")
        return

    result = df.withColumn("snapshot_date", lit(target_date).cast("date"))
    spark.sql(f"DELETE FROM iceberg.trade.dq_history WHERE snapshot_date = DATE '{target_date}'")
    result.writeTo("iceberg.trade.dq_history").append()
    print(f"[Lake] dq_history: {count} rows archived for {target_date}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", type=str, default=None)
    parser.add_argument("--backfill", action="store_true")
    args = parser.parse_args()

    if not args.target_date and not args.backfill:
        args.target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    spark = create_spark_session("TradeHistoricalLake")
    ensure_namespace(spark, "iceberg.trade")
    create_lake_tables(spark)

    if args.backfill:
        # 최근 30일 백필
        for i in range(30, 0, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            print(f"\n--- Backfill {d} ---")
            export_market_snapshot(spark, d)
            export_movers(spark, d)
            export_dq_metrics(spark, d)
    else:
        export_market_snapshot(spark, args.target_date)
        export_movers(spark, args.target_date)
        export_dq_metrics(spark, args.target_date)

    print("\n[Lake] Export completed")
    spark.stop()


if __name__ == "__main__":
    main()
