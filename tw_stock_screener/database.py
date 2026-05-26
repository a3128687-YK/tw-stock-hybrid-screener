from __future__ import annotations

from pathlib import Path
import sqlite3


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stocks (
  stock_id TEXT PRIMARY KEY,
  stock_name TEXT,
  market TEXT,
  industry TEXT,
  is_etf INTEGER DEFAULT 0,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_prices (
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

CREATE TABLE IF NOT EXISTS institutional_trades (
  stock_id TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  foreign_net_buy REAL DEFAULT 0,
  investment_trust_net_buy REAL DEFAULT 0,
  dealer_net_buy REAL DEFAULT 0,
  PRIMARY KEY (stock_id, trade_date)
);

CREATE TABLE IF NOT EXISTS monthly_revenues (
  stock_id TEXT NOT NULL,
  revenue_month TEXT NOT NULL,
  revenue REAL,
  revenue_yoy REAL,
  revenue_mom REAL,
  PRIMARY KEY (stock_id, revenue_month)
);

CREATE TABLE IF NOT EXISTS financial_quarters (
  stock_id TEXT NOT NULL,
  quarter TEXT NOT NULL,
  eps REAL,
  roe REAL,
  pe REAL,
  gross_margin REAL,
  operating_margin REAL,
  PRIMARY KEY (stock_id, quarter)
);

CREATE TABLE IF NOT EXISTS margin_trades (
  stock_id TEXT NOT NULL,
  trade_date TEXT NOT NULL,
  margin_balance REAL,
  margin_change REAL,
  short_balance REAL,
  short_change REAL,
  PRIMARY KEY (stock_id, trade_date)
);

CREATE TABLE IF NOT EXISTS large_holder_stats (
  stock_id TEXT NOT NULL,
  stat_date TEXT NOT NULL,
  holders_400_lots_ratio REAL,
  holders_400_lots_change REAL,
  PRIMARY KEY (stock_id, stat_date)
);

CREATE TABLE IF NOT EXISTS broker_branch_trades (
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

CREATE TABLE IF NOT EXISTS screening_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at TEXT DEFAULT CURRENT_TIMESTAMP,
  mode TEXT,
  candidate_mode TEXT,
  config_json TEXT,
  status TEXT,
  error_message TEXT
);

CREATE TABLE IF NOT EXISTS screening_results (
  run_id INTEGER NOT NULL,
  rank_no INTEGER NOT NULL,
  stock_id TEXT NOT NULL,
  stock_name TEXT,
  price REAL,
  score_10 REAL,
  fundamental_score REAL,
  technical_score REAL,
  chip_score REAL,
  market_score REAL,
  grade TEXT,
  risks_json TEXT,
  details_json TEXT,
  PRIMARY KEY (run_id, rank_no)
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)

