"""
Build Trade Performance Mart from Iceberg

Reads flat timeseries from Iceberg (no JSONB parsing),
joins with movers_latest for tier classification,
writes mart tables to Postgres via JDBC.

Output tables:
  - mart_trade_signal_detail
  - mart_trade_strategy_result
  - mart_trade_time_performance

Usage:
  spark-submit ... build_performance_mart.py --target-date 2026-03-14
  spark-submit ... build_performance_mart.py --backfill
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from pyspark.sql import functions as F, Row
from pyspark.sql.functions import (
    col, when, lit, count, sum as spark_sum, abs as spark_abs,
    collect_list, struct
)

from common.spark_utils import create_spark_session

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "driver": "org.postgresql.Driver",
}

# TP/SL grid: 33 combinations
TPSL_GRID = [(2.0, 2.5)]
for tp in range(3, 11):
    for sl in range(1, 6):
        if tp > sl:
            TPSL_GRID.append((float(tp), float(sl)))

PROFIT_TARGETS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

TARGET_COL_MAP = {
    0.5: 'hit_min_0_5', 1.0: 'hit_min_1_0', 1.5: 'hit_min_1_5',
    2.0: 'hit_min_2_0', 2.5: 'hit_min_2_5', 3.0: 'hit_min_3_0',
    3.5: 'hit_min_3_5', 4.0: 'hit_min_4_0', 4.5: 'hit_min_4_5',
    5.0: 'hit_min_5_0', 6.0: 'hit_min_6_0', 7.0: 'hit_min_7_0',
    8.0: 'hit_min_8_0', 9.0: 'hit_min_9_0', 10.0: 'hit_min_10_0',
}


def get_timeseries_with_tier(spark, target_date=None):
    """Read Iceberg timeseries + Postgres movers tier info, return joined DF."""
    ts = spark.read.table("iceberg.trade.performance_timeseries")
    if target_date:
        ts = ts.filter(col("alert_date") == target_date)

    # Get tier from movers_latest via JDBC
    movers_query = """(
        SELECT DISTINCT ON (symbol, event_time) symbol, event_time,
            CASE WHEN status LIKE '[High]%%' THEN 'High'
                 WHEN status LIKE '[Mid]%%' THEN 'Mid'
                 ELSE 'Small' END AS tier
        FROM movers_latest WHERE type = 'rise'
        ORDER BY symbol, event_time, change_pct_window DESC
    ) AS m"""
    movers = spark.read.jdbc(DB_URL, movers_query, properties=DB_PROPERTIES)

    joined = ts.join(
        movers,
        (ts.symbol == movers.symbol) & (ts.alert_time == movers.event_time),
        "inner"
    ).select(
        ts.symbol, ts.alert_type, ts.alert_time, ts.time_min,
        ts.close_price, ts.profit_pct, ts.is_win, ts.alert_date,
        movers.tier
    )

    return joined


def build_signal_detail(spark, joined_df, target_date=None):
    """Build mart_trade_signal_detail from flat timeseries.

    Per-signal metrics: max profit, drawdown, target hit times.
    Uses collect_list + UDF approach for complex per-signal logic.
    """
    # Collect all time points per signal
    signal_groups = joined_df.groupBy("symbol", "alert_type", "alert_time", "tier").agg(
        collect_list(
            struct("time_min", "profit_pct", "close_price")
        ).alias("points")
    )

    rows = signal_groups.collect()
    if not rows:
        print("No signals to process for signal_detail")
        return

    detail_rows = []
    for row in rows:
        points = sorted(row.points, key=lambda p: p.time_min)
        if not points:
            continue

        max_profit = -999.0
        max_drawdown = 999.0
        time_to_max_profit = 0
        time_to_max_drawdown = 0

        for p in points:
            if p.profit_pct > max_profit:
                max_profit = p.profit_pct
                time_to_max_profit = p.time_min
            if p.profit_pct < max_drawdown:
                max_drawdown = p.profit_pct
                time_to_max_drawdown = p.time_min

        # profit_at_60m
        profit_at_60m = None
        for p in points:
            if p.time_min == 60:
                profit_at_60m = p.profit_pct
                break
        if profit_at_60m is None:
            profit_at_60m = points[-1].profit_pct

        # max profit after max drawdown
        max_profit_after_dd = None
        for p in points:
            if p.time_min > time_to_max_drawdown:
                if max_profit_after_dd is None or p.profit_pct > max_profit_after_dd:
                    max_profit_after_dd = p.profit_pct

        # Target hit times
        hit_mins = {}
        for target in PROFIT_TARGETS:
            for p in points:
                if p.profit_pct >= target:
                    hit_mins[target] = p.time_min
                    break

        detail_rows.append(Row(
            symbol=row.symbol,
            alert_type=row.alert_type,
            alert_time=row.alert_time,
            tier=row.tier,
            max_profit=round(max_profit, 4),
            max_drawdown=round(max_drawdown, 4),
            time_to_max_profit=time_to_max_profit,
            time_to_max_drawdown=time_to_max_drawdown,
            profit_at_60m=round(profit_at_60m, 4) if profit_at_60m is not None else None,
            max_profit_after_drawdown=round(max_profit_after_dd, 4) if max_profit_after_dd is not None else None,
            hit_min_0_5=hit_mins.get(0.5),
            hit_min_1_0=hit_mins.get(1.0),
            hit_min_1_5=hit_mins.get(1.5),
            hit_min_2_0=hit_mins.get(2.0),
            hit_min_2_5=hit_mins.get(2.5),
            hit_min_3_0=hit_mins.get(3.0),
            hit_min_3_5=hit_mins.get(3.5),
            hit_min_4_0=hit_mins.get(4.0),
            hit_min_4_5=hit_mins.get(4.5),
            hit_min_5_0=hit_mins.get(5.0),
            hit_min_6_0=hit_mins.get(6.0),
            hit_min_7_0=hit_mins.get(7.0),
            hit_min_8_0=hit_mins.get(8.0),
            hit_min_9_0=hit_mins.get(9.0),
            hit_min_10_0=hit_mins.get(10.0),
        ))

    if not detail_rows:
        return

    detail_df = spark.createDataFrame(detail_rows)

    # Delete existing data for idempotent write
    if target_date:
        _jdbc_delete(f"DELETE FROM mart_trade_signal_detail WHERE alert_time::date = '{target_date}'")
    else:
        _jdbc_delete("DELETE FROM mart_trade_signal_detail WHERE TRUE")

    detail_df.write.jdbc(DB_URL, "mart_trade_signal_detail", mode="append", properties=DB_PROPERTIES)
    print(f"Wrote {len(detail_rows)} rows to mart_trade_signal_detail")


def build_strategy_result(spark, joined_df, target_date=None):
    """Build mart_trade_strategy_result: simulate 33 TP/SL combos per signal."""
    signal_groups = joined_df.groupBy("symbol", "alert_time", "tier").agg(
        collect_list(
            struct("time_min", "profit_pct")
        ).alias("points")
    )

    rows = signal_groups.collect()
    if not rows:
        print("No signals for strategy_result")
        return

    strategy_rows = []
    for row in rows:
        points = sorted(row.points, key=lambda p: p.time_min)
        if not points:
            continue

        for tp, sl in TPSL_GRID:
            result_pct = None
            result_type = None
            exit_time = None

            for p in points:
                if p.profit_pct >= tp:
                    result_pct = tp
                    result_type = 'TP'
                    exit_time = p.time_min
                    break
                elif p.profit_pct <= -sl:
                    result_pct = -sl
                    result_type = 'SL'
                    exit_time = p.time_min
                    break

            if result_pct is None:
                result_pct = points[-1].profit_pct
                result_type = 'TIMEOUT'
                exit_time = points[-1].time_min

            strategy_rows.append(Row(
                symbol=row.symbol,
                alert_time=row.alert_time,
                tier=row.tier,
                take_profit=tp,
                stop_loss=sl,
                result_pct=round(result_pct, 4),
                result_type=result_type,
                exit_time_min=exit_time,
            ))

    if not strategy_rows:
        return

    strategy_df = spark.createDataFrame(strategy_rows)

    if target_date:
        _jdbc_delete(f"DELETE FROM mart_trade_strategy_result WHERE alert_time::date = '{target_date}'")
    else:
        _jdbc_delete("DELETE FROM mart_trade_strategy_result WHERE TRUE")

    strategy_df.write.jdbc(DB_URL, "mart_trade_strategy_result", mode="append", properties=DB_PROPERTIES)
    print(f"Wrote {len(strategy_rows)} rows to mart_trade_strategy_result")


def build_time_performance(spark, joined_df, target_date=None):
    """Build mart_trade_time_performance: daily x tier x minute aggregation.

    This one can be done purely with Spark SQL (no collect).
    """
    # Per-tier aggregation
    tier_agg = joined_df.groupBy(
        col("alert_date").alias("date"), "tier", "time_min"
    ).agg(
        count("*").alias("total_signals"),
        spark_sum(when(col("is_win"), 1).otherwise(0)).alias("wins"),
        spark_sum(when(~col("is_win"), 1).otherwise(0)).alias("losses"),
        F.coalesce(
            spark_sum(when(col("is_win"), col("profit_pct")).otherwise(0)), lit(0.0)
        ).alias("total_profit"),
        F.coalesce(
            spark_sum(
                when(~col("is_win") & (col("profit_pct") < 0), spark_abs(col("profit_pct")))
                .otherwise(0)
            ), lit(0.0)
        ).alias("total_loss"),
    )

    # 'all' tier aggregation
    all_agg = joined_df.groupBy(
        col("alert_date").alias("date"), "time_min"
    ).agg(
        count("*").alias("total_signals"),
        spark_sum(when(col("is_win"), 1).otherwise(0)).alias("wins"),
        spark_sum(when(~col("is_win"), 1).otherwise(0)).alias("losses"),
        F.coalesce(
            spark_sum(when(col("is_win"), col("profit_pct")).otherwise(0)), lit(0.0)
        ).alias("total_profit"),
        F.coalesce(
            spark_sum(
                when(~col("is_win") & (col("profit_pct") < 0), spark_abs(col("profit_pct")))
                .otherwise(0)
            ), lit(0.0)
        ).alias("total_loss"),
    ).withColumn("tier", lit("all"))

    combined = tier_agg.unionByName(all_agg)

    if target_date:
        _jdbc_delete(f"DELETE FROM mart_trade_time_performance WHERE date = '{target_date}'")
    else:
        _jdbc_delete("DELETE FROM mart_trade_time_performance WHERE TRUE")

    combined.write.jdbc(DB_URL, "mart_trade_time_performance", mode="append", properties=DB_PROPERTIES)
    row_count = combined.count()
    print(f"Wrote {row_count} rows to mart_trade_time_performance")


def _jdbc_delete(sql):
    """Execute a DELETE statement on Postgres via plain JDBC."""
    import psycopg2
    conn = psycopg2.connect(
        host=DB_HOST, port=5432, dbname="app",
        user="postgres", password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date", type=str, default=None)
    parser.add_argument("--backfill", action="store_true")
    args = parser.parse_args()

    if not args.target_date and not args.backfill:
        args.target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    target = args.target_date if not args.backfill else None
    mode = "backfill (all)" if args.backfill else f"date={target}"
    print(f"Build mart mode: {mode}")

    spark = create_spark_session("BuildTradeMart")

    try:
        joined = get_timeseries_with_tier(spark, target)
        signal_count = joined.select("symbol", "alert_time").distinct().count()
        print(f"Processing {signal_count} signals")

        if signal_count == 0:
            print("No data to process")
            return

        build_signal_detail(spark, joined, target)
        build_strategy_result(spark, joined, target)
        build_time_performance(spark, joined, target)

        print("Mart build completed successfully")
    except Exception as e:
        print(f"Mart build failed: {e}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
