-- Trendlines config
create table if not exists trendlines (
  line_id uuid primary key,
  symbol text not null,
  t1_ms bigint not null,
  p1 double precision not null,
  t2_ms bigint not null,
  p2 double precision not null,
  basis text not null default 'close',
  mode text not null default 'both',
  buffer_pct double precision not null default 0.1,
  cooldown_sec integer not null default 600,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_trendlines_symbol on trendlines(symbol);

-- Latest movers snapshot for serving UI quickly
create table if not exists movers_latest (
  type text not null,                 -- rise|high_vol_up
  symbol text not null,
  status text not null,
  "window" text not null,               -- 5m|2h|15m
  event_time timestamptz not null,
  change_pct_window double precision not null,
  change_pct_24h double precision not null,
  vol_ratio double precision,
  updated_at timestamptz not null default now(),
  primary key (type, symbol, status, event_time)
);

create index if not exists idx_movers_latest_type_time
  on movers_latest(type, event_time desc);

-- Alerts events (for feed)
create table if not exists alerts_events (
  event_time timestamptz not null,
  symbol text not null,
  line_id uuid not null,
  direction text not null,            -- break_up|break_down
  price double precision not null,
  line_price double precision not null,
  buffer_pct double precision not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_alerts_events_symbol_time
  on alerts_events(symbol, event_time desc);
