from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    renamed = df.rename(
        columns={
            "Trading_Volume": "volume",
            "max": "high",
            "min": "low",
            "date": "trade_date",
        }
    ).copy()
    for col in ["open", "high", "low", "close", "volume"]:
        if col in renamed.columns:
            renamed[col] = pd.to_numeric(renamed[col], errors="coerce")
    renamed["trade_date"] = pd.to_datetime(renamed["trade_date"], errors="coerce")
    return renamed.sort_values("trade_date").dropna(subset=["trade_date"])


def add_technical_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    df = normalize_price_frame(prices)
    if df.empty:
        return df
    close = df["close"]
    high = df["high"]
    low = df["low"]
    df["ma5"] = close.rolling(5).mean()
    df["ma10"] = close.rolling(10).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()
    df["vol_ma5"] = df["volume"].rolling(5).mean()
    df["vol_ma60"] = df["volume"].rolling(60).mean()
    df["high_20d"] = high.rolling(20).max()
    df["high_52w"] = high.rolling(252, min_periods=60).max()
    df["return_20d_pct"] = close.pct_change(20) * 100
    df["ma20_slope"] = df["ma20"] - df["ma20"].shift(5)
    df["rsi14"] = rsi(close)
    df["atr14"] = atr(high, low, close)
    df["bb_mid"] = close.rolling(20).mean()
    df["bb_std"] = close.rolling(20).std()
    df["bb_upper"] = df["bb_mid"] + 2 * df["bb_std"]
    return df


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [(high - low), (high - previous_close).abs(), (low - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def latest_metrics(prices: pd.DataFrame) -> dict[str, float]:
    df = add_technical_indicators(prices)
    if df.empty:
        return {}
    last = df.iloc[-1]
    open_ = float(last.get("open", np.nan))
    close = float(last.get("close", np.nan))
    high = float(last.get("high", np.nan))
    low = float(last.get("low", np.nan))
    upper_shadow = 0.0 if high <= low else (high - max(open_, close)) / (high - low)
    return {
        "trade_date": last["trade_date"].date().isoformat(),
        "price": close,
        "ma5": float(last.get("ma5", np.nan)),
        "ma10": float(last.get("ma10", np.nan)),
        "ma20": float(last.get("ma20", np.nan)),
        "ma60": float(last.get("ma60", np.nan)),
        "ma20_slope": float(last.get("ma20_slope", np.nan)),
        "volume": float(last.get("volume", np.nan)),
        "vol_ma5": float(last.get("vol_ma5", np.nan)),
        "vol_ma60": float(last.get("vol_ma60", np.nan)),
        "volume_ratio": float(last.get("volume", np.nan) / last.get("vol_ma5", np.nan)),
        "high_20d": float(last.get("high_20d", np.nan)),
        "high_52w": float(last.get("high_52w", np.nan)),
        "return_20d_pct": float(last.get("return_20d_pct", np.nan)),
        "rsi": float(last.get("rsi14", np.nan)),
        "atr": float(last.get("atr14", np.nan)),
        "bb_upper": float(last.get("bb_upper", np.nan)),
        "upper_shadow_ratio": float(upper_shadow),
    }

