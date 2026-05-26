from __future__ import annotations

import pandas as pd

from .config import AppConfig
from .data_sources import DataRepository


def build_candidate_pool(
    candidate_mode: str,
    config: AppConfig,
    repository: DataRepository,
    custom_symbols: list[str] | None = None,
) -> list[str]:
    if candidate_mode == "custom":
        return _normalize_symbols(custom_symbols or [])
    if candidate_mode == "mainstream":
        return config.mainstream_pool[:60]
    if candidate_mode == "institution_accumulation":
        return _investment_trust_pool(config.mainstream_pool, repository, limit=60)
    raise ValueError(f"Unknown candidate mode: {candidate_mode}")


def _investment_trust_pool(seed_symbols: list[str], repository: DataRepository, limit: int) -> list[str]:
    ranked: list[tuple[str, int, float]] = []
    for stock_id in seed_symbols:
        trades = repository.institutional_trades(stock_id, 40)
        streak = investment_trust_buy_streak(trades, lookback=12)
        total = investment_trust_net_buy(trades, lookback=12)
        ranked.append((stock_id, streak, total))
    ranked.sort(key=lambda row: (row[1], row[2]), reverse=True)
    return [row[0] for row in ranked[:limit]]


def investment_trust_buy_streak(trades: pd.DataFrame, lookback: int = 12) -> int:
    series = _institution_net_series(trades, "Investment_Trust")
    if series.empty:
        return 0
    streak = 0
    for value in series.tail(lookback).iloc[::-1]:
        if value > 0:
            streak += 1
        else:
            break
    return streak


def investment_trust_net_buy(trades: pd.DataFrame, lookback: int = 12) -> float:
    series = _institution_net_series(trades, "Investment_Trust")
    return float(series.tail(lookback).sum()) if not series.empty else 0.0


def foreign_net_buy_5d(trades: pd.DataFrame) -> float:
    series = _institution_net_series(trades, "Foreign_Investor")
    return float(series.tail(5).sum()) if not series.empty else 0.0


def _institution_net_series(trades: pd.DataFrame, name: str) -> pd.Series:
    if trades.empty or "name" not in trades.columns:
        return pd.Series(dtype=float)
    df = trades.copy()
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["buy"] = pd.to_numeric(df.get("buy"), errors="coerce").fillna(0)
    df["sell"] = pd.to_numeric(df.get("sell"), errors="coerce").fillna(0)
    mask = df["name"].astype(str).str.contains(name, case=False, na=False)
    grouped = df.loc[mask].assign(net=lambda x: x["buy"] - x["sell"]).groupby("date")["net"].sum()
    return grouped.sort_index()


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized = []
    for symbol in symbols:
        value = str(symbol).strip()
        if value:
            normalized.append(value)
    return normalized

