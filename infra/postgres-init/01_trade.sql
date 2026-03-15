

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

create index if not exists idx_movers_rise_distinct
  on movers_latest(symbol, event_time, change_pct_window desc)
  where type = 'rise';



-- Favorites (Watchlist) Config
create table if not exists favorite_groups (
  group_id uuid primary key,
  name text not null,
  "ordering" integer not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists favorite_items (
  item_id uuid primary key,
  group_id uuid not null references favorite_groups(group_id) on delete cascade,
  symbol text not null,
  "ordering" integer not null default 0,
  created_at timestamptz not null default now()
);

create index if not exists idx_fav_items_group on favorite_items(group_id);
