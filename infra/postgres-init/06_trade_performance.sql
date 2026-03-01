-- Trade Performance Time-Series Analysis
-- Stores 60 time points (1min intervals from 1min to 60min) for each signal
create table if not exists trade_performance_timeseries (
    id serial primary key,
    symbol text not null,
    alert_type text not null,
    alert_time timestamptz not null,
    entry_price double precision not null,

    -- JSONB structure: {"1": {"price": 100.5, "profit_pct": 1.2, "is_win": true}, "2": {...}, ..., "60": {...}}
    timeseries_data jsonb not null,

    created_at timestamptz not null default now(),

    unique(symbol, alert_type, alert_time)
);

create index if not exists idx_perf_timeseries_time on trade_performance_timeseries(alert_time);
create index if not exists idx_perf_timeseries_symbol on trade_performance_timeseries(symbol);
create index if not exists idx_perf_timeseries_data on trade_performance_timeseries using gin (timeseries_data);
