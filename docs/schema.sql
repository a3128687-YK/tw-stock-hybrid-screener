-- SQLite schema used by tw-stock-hybrid-screener.
-- The broker_branch_trades table is intentionally present before broker
-- branch data is enabled, so the analysis module can be switched on later
-- without changing downstream reports.

PRAGMA foreign_keys = ON;

CREATE TABLE stocks (
  stock_id TEXT PRIMARY KEY,
  stock_name TEXT,
  market TEXT,
  industry TEXT,
  is_etf INTEGER DEFAULT 0,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE daily_prices (
  stock_id TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  volume REAL,
  value REAL,
  PRIMARY KEY (stock_id, trade_date)
);

CREATE TABLE institutional_trades (
  stock_id TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  foreign_net_buy REAL DEFAULT 0,
  investment_trust_net_buy REAL DEFAULT 0,
  dealer_net_buy REAL DEFAULT 0,
  PRIMARY KEY (stock_id, trade_date)
);

CREATE TABLE monthly_revenues (
  stock_id TEXT NOT NULL,
  revenue_month TEXT NOT NULL,
  revenue REAL,
  revenue_yoy REAL,
  revenue_mom REAL,
  PRIMARY KEY (stock_id, revenue_month)
);

CREATE TABLE financial_quarters (
  stock_id TEXT NOT NULL,
  quarter TEXT NOT NULL,
  eps REAL,
  roe REAL,
  pe REAL,
  gross_margin REAL,
  operating_margin REAL,
  PRIMARY KEY (stock_id, quarter)
);

CREATE TABLE margin_trades (
  stock_id TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  margin_balance REAL,
  margin_change REAL,
  short_balance REAL,
  short_change REAL,
  PRIMARY KEY (stock_id, trade_date)
);

CREATE TABLE large_holder_stats (
  stock_id TEXT NOT NULL,
  stat_date TEXT NOT NULL,
  holders_400_lots_ratio REAL,
  holders_400_lots_change REAL,
  PRIMARY KEY (stock_id, stat_date)
);

CREATE TABLE broker_branch_trades (
  trade_date TEXT NOT NULL,
  stock_id TEXT NOT NULL,
  broker_name TEXT NOT NULL,
  buy_lots REAL DEFAULT 0,
  sell_lots REAL DEFAULT 0,
  net_buy_lots REAL DEFAULT 0,
  next_day_reverse_sell INTEGER,
  next_day_return REAL,
  return_3d REAL,
  return_5d REAL,
  max_drawdown REAL,
  data_source TEXT,
  PRIMARY KEY (trade_date, stock_id, broker_name)
);

