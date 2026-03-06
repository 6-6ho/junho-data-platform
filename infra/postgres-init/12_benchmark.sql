CREATE TABLE IF NOT EXISTS spark_benchmark_results (
    id SERIAL PRIMARY KEY,
    config_name TEXT NOT NULL,
    partitions INT,
    executor_count INT,
    total_cores INT,
    row_count BIGINT,
    aggregation_sec DOUBLE PRECISION,
    window_function_sec DOUBLE PRECISION,
    join_sec DOUBLE PRECISION,
    basket_prep_sec DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
