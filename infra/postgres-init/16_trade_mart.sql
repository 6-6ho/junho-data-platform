-- Trade Performance Mart Tables
-- Pre-computed from trade_performance_timeseries JSONB → API reads flat columns only

-- Legacy cleanup: mart_trade_stats (05_trade_dq.sql) is unused
DROP TABLE IF EXISTS mart_trade_stats;

-- A: Signal-level pre-computed metrics (profit-targets, drawdown-recovery)
CREATE TABLE IF NOT EXISTS mart_trade_signal_detail (
    symbol TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    alert_time TIMESTAMPTZ NOT NULL,
    tier TEXT NOT NULL,
    max_profit DOUBLE PRECISION NOT NULL,
    max_drawdown DOUBLE PRECISION NOT NULL,
    time_to_max_profit SMALLINT NOT NULL,
    time_to_max_drawdown SMALLINT NOT NULL,
    profit_at_60m DOUBLE PRECISION,
    max_profit_after_drawdown DOUBLE PRECISION,
    hit_min_0_5  SMALLINT, hit_min_1_0  SMALLINT, hit_min_1_5  SMALLINT,
    hit_min_2_0  SMALLINT, hit_min_2_5  SMALLINT, hit_min_3_0  SMALLINT,
    hit_min_3_5  SMALLINT, hit_min_4_0  SMALLINT, hit_min_4_5  SMALLINT,
    hit_min_5_0  SMALLINT, hit_min_6_0  SMALLINT, hit_min_7_0  SMALLINT,
    hit_min_8_0  SMALLINT, hit_min_9_0  SMALLINT, hit_min_10_0 SMALLINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, alert_type, alert_time)
);
CREATE INDEX IF NOT EXISTS idx_mart_signal_detail_tier_time
    ON mart_trade_signal_detail(tier, alert_time DESC);

-- B: Signal x TP/SL combination results (simulate, optimize, weekly/daily-pnl, compound)
CREATE TABLE IF NOT EXISTS mart_trade_strategy_result (
    symbol TEXT NOT NULL,
    alert_time TIMESTAMPTZ NOT NULL,
    tier TEXT NOT NULL,
    take_profit DOUBLE PRECISION NOT NULL,
    stop_loss DOUBLE PRECISION NOT NULL,
    result_pct DOUBLE PRECISION NOT NULL,
    result_type TEXT NOT NULL,
    exit_time_min SMALLINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, alert_time, take_profit, stop_loss)
);
CREATE INDEX IF NOT EXISTS idx_mart_strategy_tpsl_time
    ON mart_trade_strategy_result(take_profit, stop_loss, alert_time DESC);
CREATE INDEX IF NOT EXISTS idx_mart_strategy_tier_tpsl
    ON mart_trade_strategy_result(tier, take_profit, stop_loss, alert_time DESC);

-- C: Daily x tier x minute aggregation (time-based endpoint)
CREATE TABLE IF NOT EXISTS mart_trade_time_performance (
    date DATE NOT NULL,
    tier TEXT NOT NULL,
    time_min SMALLINT NOT NULL,
    total_signals INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    total_profit DOUBLE PRECISION DEFAULT 0,
    total_loss DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, tier, time_min)
);

-- E: Daily pre-aggregated TP/SL strategy stats (optimize endpoint)
CREATE TABLE IF NOT EXISTS mart_trade_optimize_daily (
    date DATE NOT NULL,
    tier TEXT NOT NULL,
    take_profit DOUBLE PRECISION NOT NULL,
    stop_loss DOUBLE PRECISION NOT NULL,
    trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    total_pnl DOUBLE PRECISION DEFAULT 0,
    total_win_pnl DOUBLE PRECISION DEFAULT 0,
    total_loss_pnl DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (date, tier, take_profit, stop_loss)
);

-- D: DQ daily stats from signal_validation_log
CREATE TABLE IF NOT EXISTS mart_signal_validation_daily (
    date DATE PRIMARY KEY,
    total_samples INT DEFAULT 0,
    pass_count INT DEFAULT 0,
    fail_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    pass_rate DOUBLE PRECISION,
    avg_diff_pct DOUBLE PRECISION,
    max_diff_pct DOUBLE PRECISION,
    data_quality_score DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
