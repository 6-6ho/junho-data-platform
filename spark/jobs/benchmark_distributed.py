"""
Spark Distributed Processing Benchmark
- Loads shop_events Parquet from MinIO
- Runs 4 workloads: Aggregation, Window, Join, Basket Prep
- Compares performance across different partition counts
- Saves results to spark_benchmark_results table
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, sum as _sum, row_number, collect_list, array_distinct, size, lit
)
from pyspark.sql.window import Window
import time
import os

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_URL = f"jdbc:postgresql://{DB_HOST}:5432/app"
DB_PROPERTIES = {
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
    "driver": "org.postgresql.Driver"
}

CONFIG_NAME = os.getenv("BENCHMARK_CONFIG", "default")


def measure(func):
    """Execute func and return elapsed seconds."""
    start = time.time()
    func()
    return round(time.time() - start, 3)


def run():
    spark = SparkSession.builder \
        .appName(f"Benchmark-{CONFIG_NAME}") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minio") \
        .config("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", "minio123")) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()

    sc = spark.sparkContext

    # Detect cluster resources
    executor_count = max(len(sc._jsc.sc().statusTracker().getExecutorInfos()) - 1, 1)
    total_cores = sc.defaultParallelism
    print(f"=== Cluster: {executor_count} executors, {total_cores} cores ===")

    # Load data
    try:
        df = spark.read.parquet("s3a://raw/shop_events")
    except Exception as e:
        print(f"No data found: {e}")
        return

    df.cache()
    row_count = df.count()
    print(f"=== Data: {row_count:,} rows ===")

    if row_count == 0:
        print("No data to benchmark.")
        return

    # Partition counts to test
    partition_counts = [1, 2, total_cores, total_cores * 4]
    # Deduplicate while preserving order
    seen = set()
    unique_partitions = []
    for p in partition_counts:
        if p not in seen:
            seen.add(p)
            unique_partitions.append(p)

    results = []

    for num_partitions in unique_partitions:
        print(f"\n--- Partitions: {num_partitions} ---")

        test_df = df.repartition(num_partitions)
        test_df.cache()
        test_df.count()  # materialize

        # 1. Aggregation: groupBy(category, user_id) + sum/count
        def workload_agg():
            test_df.groupBy("category", "user_id") \
                .agg(_sum("total_amount").alias("total"), count("*").alias("cnt")) \
                .count()

        agg_sec = measure(workload_agg)
        print(f"  Aggregation: {agg_sec}s")

        # 2. Window Function: row_number() over(partitionBy user_id orderBy event_time)
        def workload_window():
            w = Window.partitionBy("user_id").orderBy("event_time")
            test_df.withColumn("rn", row_number().over(w)) \
                .filter(col("rn") == 1) \
                .count()

        window_sec = measure(workload_window)
        print(f"  Window: {window_sec}s")

        # 3. Join: user_stats self-join
        def workload_join():
            user_stats = test_df.groupBy("user_id") \
                .agg(count("*").alias("event_count"), _sum("total_amount").alias("total_spend"))
            test_df.join(user_stats, "user_id", "left") \
                .select("event_id", "user_id", "event_count", "total_spend") \
                .count()

        join_sec = measure(workload_join)
        print(f"  Join: {join_sec}s")

        # 4. Basket Prep: collect_list for basket analysis
        def workload_basket():
            test_df.filter(col("event_type") == "purchase") \
                .groupBy("session_id") \
                .agg(collect_list("product_id").alias("items")) \
                .withColumn("items", array_distinct(col("items"))) \
                .filter(size(col("items")) > 1) \
                .count()

        basket_sec = measure(workload_basket)
        print(f"  Basket Prep: {basket_sec}s")

        test_df.unpersist()

        results.append({
            "config_name": CONFIG_NAME,
            "partitions": num_partitions,
            "executor_count": executor_count,
            "total_cores": total_cores,
            "row_count": row_count,
            "aggregation_sec": agg_sec,
            "window_function_sec": window_sec,
            "join_sec": join_sec,
            "basket_prep_sec": basket_sec,
        })

    # Save results to Postgres
    results_df = spark.createDataFrame(results)
    results_df.write.mode("append") \
        .jdbc(DB_URL, "spark_benchmark_results", properties=DB_PROPERTIES)

    # Print summary
    print("\n========== BENCHMARK RESULTS ==========")
    print(f"Config: {CONFIG_NAME}")
    print(f"Executors: {executor_count}, Cores: {total_cores}, Rows: {row_count:,}")
    print(f"{'Partitions':<12} {'Agg(s)':<10} {'Window(s)':<12} {'Join(s)':<10} {'Basket(s)':<10}")
    print("-" * 54)
    for r in results:
        print(f"{r['partitions']:<12} {r['aggregation_sec']:<10} {r['window_function_sec']:<12} {r['join_sec']:<10} {r['basket_prep_sec']:<10}")
    print("=" * 54)

    df.unpersist()
    spark.stop()


if __name__ == "__main__":
    run()
