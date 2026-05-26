from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd


def sample_price_frame(stock_id: str, base: float = 100.0, days: int = 260) -> pd.DataFrame:
    rng = np.random.default_rng(abs(hash(stock_id)) % (2**32))
    dates = [date.today() - timedelta(days=i) for i in range(days * 2)]
    weekdays = [d for d in dates if d.weekday() < 5][:days]
    weekdays.reverse()
    trend = np.linspace(base * 0.82, base * 1.08, len(weekdays))
    noise = rng.normal(0, base * 0.012, len(weekdays)).cumsum()
    close = np.maximum(10, trend + noise)
    open_ = close * (1 + rng.normal(0, 0.008, len(close)))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.003, 0.025, len(close)))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.003, 0.025, len(close)))
    volume = rng.integers(1500, 12000, len(close)).astype(float)
    volume[-5:] *= np.linspace(1.1, 1.8, 5)
    return pd.DataFrame(
        {
            "date": [str(d) for d in weekdays],
            "stock_id": stock_id,
            "Trading_Volume": volume,
            "open": open_,
            "max": high,
            "min": low,
            "close": close,
        }
    )


def sample_institutional_frame(stock_id: str, days: int = 30) -> pd.DataFrame:
    dates = [date.today() - timedelta(days=i) for i in range(days * 2)]
    weekdays = [d for d in dates if d.weekday() < 5][:days]
    weekdays.reverse()
    rows = []
    for i, d in enumerate(weekdays):
        rows.append({"date": str(d), "stock_id": stock_id, "name": "Investment_Trust", "buy": 700 + i * 8, "sell": 250})
        rows.append({"date": str(d), "stock_id": stock_id, "name": "Foreign_Investor", "buy": 1200, "sell": 900 - min(i * 5, 200)})
    return pd.DataFrame(rows)


def sample_fundamentals(stock_id: str) -> dict[str, float | list[float]]:
    seed = abs(hash(stock_id)) % 9
    return {
        "revenue_yoy": [15, 25, 55, 90, 35, 10, 68, 22, 48][seed],
        "roe": [9, 12, 16, 21, 26, 18, 14, 30, 10][seed],
        "eps_last_4q": [1.2, 1.5, 1.8, 2.1],
        "pe": [16, 18, 22, 28, 14, 20, 24, 30, 12][seed],
        "pe_3y_avg": [20, 20, 20, 24, 18, 20, 22, 28, 16][seed],
        "large_holder_change": [0.4, 0.8, -0.1, 1.2, 0.6, 1.8, 0.2, 2.4, 0.7][seed],
        "margin_balance_change_5d_pct": [1, 3, 5, 14, 2, -1, 4, 8, 0][seed],
        "topic_score": 2.0,
        "market_bull_score": 3.0,
    }

