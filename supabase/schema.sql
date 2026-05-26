-- Supabase schema for the Cloudflare Pages version.
-- Run this in Supabase SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.stocks (
  stock_id text primary key,
  stock_name text,
  market text,
  industry text,
  is_etf boolean not null default false,
  updated_at timestamptz not null default now()
);

create table if not exists public.daily_prices (
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  trade_date date not null,
  open numeric,
  high numeric,
  low numeric,
  close numeric,
  volume numeric,
  value numeric,
  primary key (stock_id, trade_date)
);

create table if not exists public.institutional_trades (
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  trade_date date not null,
  foreign_net_buy numeric default 0,
  investment_trust_net_buy numeric default 0,
  dealer_net_buy numeric default 0,
  primary key (stock_id, trade_date)
);

create table if not exists public.monthly_revenues (
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  revenue_month date not null,
  revenue numeric,
  revenue_yoy numeric,
  revenue_mom numeric,
  primary key (stock_id, revenue_month)
);

create table if not exists public.financial_quarters (
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  quarter text not null,
  eps numeric,
  roe numeric,
  pe numeric,
  gross_margin numeric,
  operating_margin numeric,
  primary key (stock_id, quarter)
);

create table if not exists public.margin_trades (
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  trade_date date not null,
  margin_balance numeric,
  margin_change numeric,
  short_balance numeric,
  short_change numeric,
  primary key (stock_id, trade_date)
);

create table if not exists public.large_holder_stats (
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  stat_date date not null,
  holders_400_lots_ratio numeric,
  holders_400_lots_change numeric,
  primary key (stock_id, stat_date)
);

create table if not exists public.broker_branch_trades (
  trade_date date not null,
  stock_id text not null references public.stocks(stock_id) on delete cascade,
  broker_name text not null,
  buy_lots numeric default 0,
  sell_lots numeric default 0,
  net_buy_lots numeric default 0,
  next_day_reverse_sell boolean,
  next_day_return numeric,
  return_3d numeric,
  return_5d numeric,
  max_drawdown numeric,
  data_source text,
  primary key (trade_date, stock_id, broker_name)
);

create table if not exists public.screening_runs (
  id uuid primary key default gen_random_uuid(),
  run_at timestamptz not null default now(),
  mode text,
  candidate_mode text,
  config_json jsonb,
  status text,
  error_message text
);

create table if not exists public.screening_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references public.screening_runs(id) on delete cascade,
  rank_no integer not null,
  stock_id text not null,
  stock_name text,
  price numeric,
  score_10 numeric,
  fundamental_score numeric,
  technical_score numeric,
  chip_score numeric,
  market_score numeric,
  grade text,
  risks_json jsonb,
  details_json jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_daily_prices_stock_date
  on public.daily_prices(stock_id, trade_date desc);

create index if not exists idx_institutional_trades_stock_date
  on public.institutional_trades(stock_id, trade_date desc);

create index if not exists idx_broker_branch_stock_broker_date
  on public.broker_branch_trades(stock_id, broker_name, trade_date desc);

alter table public.stocks enable row level security;
alter table public.daily_prices enable row level security;
alter table public.institutional_trades enable row level security;
alter table public.monthly_revenues enable row level security;
alter table public.financial_quarters enable row level security;
alter table public.margin_trades enable row level security;
alter table public.large_holder_stats enable row level security;
alter table public.broker_branch_trades enable row level security;
alter table public.screening_runs enable row level security;
alter table public.screening_results enable row level security;

drop policy if exists "public read stocks" on public.stocks;
create policy "public read stocks" on public.stocks for select using (true);

drop policy if exists "public read screening results" on public.screening_results;
create policy "public read screening results" on public.screening_results for select using (true);

drop policy if exists "public read screening runs" on public.screening_runs;
create policy "public read screening runs" on public.screening_runs for select using (true);

