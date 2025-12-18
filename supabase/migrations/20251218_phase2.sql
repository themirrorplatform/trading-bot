-- Phase 2 schema migration for trading bot cloud mirror
-- Safe to run multiple times (IF NOT EXISTS used where possible)

-- 1) Device registry
create table if not exists bot_devices (
  device_id text primary key,
  name text,
  created_at timestamptz default now(),
  last_seen_at timestamptz
);

-- 2) Mirrored events (sanitized)
create table if not exists bot_events (
  device_id text not null references bot_devices(device_id) on delete cascade,
  seq bigint not null,
  event_id text not null,
  ts timestamptz not null,
  type text not null,
  severity text not null default 'INFO',
  symbol text,
  session text,
  reason_codes text[] default '{}',
  summary text,
  payload jsonb,
  primary key (device_id, seq)
);

create index if not exists bot_events_device_ts_idx on bot_events(device_id, ts desc);
create index if not exists bot_events_type_idx on bot_events(type);
create index if not exists bot_events_reason_codes_idx on bot_events using gin (reason_codes);

-- 3) Latest snapshot
create table if not exists bot_latest_snapshot (
  device_id text primary key references bot_devices(device_id) on delete cascade,
  updated_at timestamptz not null default now(),
  last_seq bigint not null,
  snapshot jsonb not null
);

-- 4) Health pings
create table if not exists bot_health (
  device_id text primary key references bot_devices(device_id) on delete cascade,
  updated_at timestamptz not null default now(),
  mode text not null,                  -- OBSERVE/PAPER/LIVE
  kill_switch text not null,           -- ARMED/TRIPPED
  feed_latency_ms int,
  missing_bars int,
  clock_drift_ms int,
  notes text
);
