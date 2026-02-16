-- Trade Performance Analysis Results
create table if not exists trade_performance (
    id serial primary key,
    symbol text not null,
    alert_type text not null,           -- rise, high_vol_up, etc
    alert_time timestamptz not null,
    
    -- Analysis Window
    analysis_window_minutes integer not null, -- e.g. 60 (1 hour), 240 (4 hours)
    
    -- Price Data
    entry_price double precision not null,
    max_price double precision not null,
    min_price double precision not null,
    close_price double precision not null,
    
    -- Performance Metrics
    max_profit_pct double precision not null,
    max_drawdown_pct double precision not null,
    final_profit_pct double precision not null,
    
    -- Result Classification
    is_win boolean not null,            -- e.g. max_profit > 1%
    result_type text not null,          -- WIN, LOSS, BREAK_EVEN
    
    created_at timestamptz not null default now()
);

create index if not exists idx_trade_performance_time on trade_performance(alert_time);
create index if not exists idx_trade_performance_symbol on trade_performance(symbol);
