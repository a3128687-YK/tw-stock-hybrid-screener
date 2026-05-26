from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .finmind import FinMindClient
from .sample import sample_fundamentals, sample_institutional_frame, sample_price_frame


class DataRepository:
    def __init__(self, finmind_token: str | None = None, use_sample: bool = False) -> None:
        self.finmind = FinMindClient(finmind_token)
        self.use_sample = use_sample
        self.errors: list[str] = []

    def prices(self, stock_id: str, lookback_days: int = 420) -> pd.DataFrame:
        if self.use_sample:
            return sample_price_frame(stock_id, base=self._sample_base(stock_id))
        start = date.today() - timedelta(days=lookback_days)
        try:
            return self.finmind.stock_prices(stock_id, start)
        except Exception as exc:
            self.errors.append(f"{stock_id} price: {exc}")
            return pd.DataFrame()

    def institutional_trades(self, stock_id: str, lookback_days: int = 60) -> pd.DataFrame:
        if self.use_sample:
            return sample_institutional_frame(stock_id)
        start = date.today() - timedelta(days=lookback_days)
        try:
            return self.finmind.institutional_trades(stock_id, start)
        except Exception as exc:
            self.errors.append(f"{stock_id} institutional: {exc}")
            return pd.DataFrame()

    def fundamentals(self, stock_id: str) -> dict:
        if self.use_sample:
            return sample_fundamentals(stock_id)
        fundamentals: dict = {}
        start = date.today() - timedelta(days=1100)
        try:
            revenue = self.finmind.monthly_revenue(stock_id, start)
            if not revenue.empty:
                revenue = revenue.sort_values("date")
                yoy_col = "revenue_year_growth_rate"
                if yoy_col in revenue.columns:
                    fundamentals["revenue_yoy"] = float(pd.to_numeric(revenue[yoy_col], errors="coerce").dropna().iloc[-1])
        except Exception as exc:
            self.errors.append(f"{stock_id} revenue: {exc}")

        try:
            financial = self.finmind.financial_statement(stock_id, start)
            fundamentals.update(_extract_financial_metrics(financial))
        except Exception as exc:
            self.errors.append(f"{stock_id} financial: {exc}")

        fundamentals.setdefault("large_holder_change", None)
        fundamentals.setdefault("margin_balance_change_5d_pct", None)
        fundamentals.setdefault("topic_score", 0.0)
        fundamentals.setdefault("market_bull_score", 2.0)
        return fundamentals

    def _sample_base(self, stock_id: str) -> float:
        return 40.0 + (abs(hash(stock_id)) % 180)


def _extract_financial_metrics(financial: pd.DataFrame) -> dict:
    if financial.empty:
        return {}
    df = financial.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

    metrics: dict = {}
    eps = _latest_values_by_type(df, ["EPS", "基本每股盈餘"])
    if eps:
        metrics["eps_last_4q"] = eps[-4:]
    roe = _latest_values_by_type(df, ["ROE", "權益報酬率"])
    if roe:
        metrics["roe"] = float(roe[-1])
    pe = _latest_values_by_type(df, ["PE", "本益比"])
    if pe:
        metrics["pe"] = float(pe[-1])
        metrics["pe_3y_avg"] = float(sum(pe[-12:]) / len(pe[-12:]))
    return metrics


def _latest_values_by_type(df: pd.DataFrame, names: list[str]) -> list[float]:
    if "type" not in df.columns or "value" not in df.columns:
        return []
    mask = df["type"].astype(str).isin(names)
    values = pd.to_numeric(df.loc[mask, "value"], errors="coerce").dropna().tolist()
    return [float(v) for v in values]

