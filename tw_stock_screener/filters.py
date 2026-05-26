from __future__ import annotations

import math

from .config import AppConfig


def hard_filter(metrics: dict, fundamentals: dict, config: AppConfig) -> tuple[bool, list[str], list[str]]:
    cfg = config.hard_filters
    reasons: list[str] = []
    warnings: list[str] = []

    eps_last_4q = fundamentals.get("eps_last_4q")
    if not eps_last_4q or len(eps_last_4q) < 4:
        reasons.append("近四季 EPS 資料不足")
    elif sum(eps_last_4q[-4:]) < 0:
        reasons.append("近四季 EPS 合計為負")

    roe = fundamentals.get("roe")
    if roe is None:
        reasons.append("ROE 資料不足")
    elif roe < cfg.min_roe:
        reasons.append(f"最近一季 ROE < {cfg.min_roe:g}%")

    if _is_missing(metrics.get("vol_ma60")) or metrics.get("vol_ma60", 0) < cfg.min_avg_volume_3m:
        reasons.append("近 3 個月平均成交量太低或資料不足")

    if cfg.exclude_low_price and not _is_missing(metrics.get("price")) and metrics["price"] < cfg.min_price:
        reasons.append(f"股價低於 {cfg.min_price:g} 元")

    if not _is_missing(metrics.get("return_20d_pct")) and metrics["return_20d_pct"] > cfg.overheated_20d_return:
        warnings.append("近 20 日漲幅超過 80%，標記過熱")
        reasons.append("短線漲幅過熱")

    if (
        metrics.get("upper_shadow_ratio", 0) >= cfg.long_upper_shadow_ratio
        and metrics.get("volume_ratio", 0) >= cfg.high_risk_volume_ratio
        and fundamentals.get("same_day_smart_money_net", 0) < 0
    ):
        warnings.append("當日爆量長上影且資金賣超，標記高風險")

    return len(reasons) == 0, reasons, warnings


def technical_filter(metrics: dict, config: AppConfig) -> tuple[bool, list[str], list[str]]:
    cfg = config.technical_filters
    reasons: list[str] = []
    warnings: list[str] = []
    price = metrics.get("price")
    ma5 = metrics.get("ma5")
    ma10 = metrics.get("ma10")
    ma20 = metrics.get("ma20")

    if _is_missing(price) or _is_missing(ma20) or price <= ma20:
        reasons.append("收盤價未站上 MA20")
    if (_is_missing(ma5) or _is_missing(ma20) or ma5 <= ma20) and (_is_missing(ma10) or ma10 <= ma20):
        reasons.append("MA5/MA10 未站上 MA20")
    if _is_missing(metrics.get("volume_ratio")) or metrics["volume_ratio"] < cfg.min_volume_to_ma5:
        reasons.append("成交量未達 5 日均量 x 0.8")
    if (
        _is_missing(price)
        or _is_missing(metrics.get("high_52w"))
        or metrics["high_52w"] <= 0
        or price <= metrics["high_52w"] * cfg.min_52w_high_ratio
    ):
        reasons.append("現價未達 52 週高點的 70%")
    if not _is_missing(metrics.get("rsi")) and metrics["rsi"] > cfg.max_rsi:
        warnings.append("RSI 高於 75，過熱追價風險")

    return len(reasons) == 0, reasons, warnings


def strategy_filter(strategy_mode: str, metrics: dict, fundamentals: dict) -> tuple[bool, list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []
    price = metrics.get("price")
    rsi = metrics.get("rsi")

    if strategy_mode == "accumulation":
        near_ma20 = _distance_ok(price, metrics.get("ma20"), 0.08)
        near_ma60 = _distance_ok(price, metrics.get("ma60"), 0.10)
        if not (near_ma20 or near_ma60):
            reasons.append("蓄勢模式要求股價接近 MA20 或 MA60")
        if metrics.get("return_20d_pct", 999) > 25:
            reasons.append("蓄勢模式排除近 20 日漲幅過大")
        if fundamentals.get("large_holder_change") is not None and fundamentals.get("large_holder_change", 0) <= 0:
            reasons.append("大戶持股未增加")
        if _is_missing(rsi) or not (45 <= rsi <= 60):
            reasons.append("RSI 不在 45~60 蓄勢區")
    elif strategy_mode == "momentum":
        if _is_missing(price) or _is_missing(metrics.get("ma10")) or price <= metrics["ma10"]:
            reasons.append("動能模式要求股價站上 MA10")
        if _is_missing(metrics.get("ma5")) or _is_missing(metrics.get("ma20")) or metrics["ma5"] <= metrics["ma20"]:
            reasons.append("動能模式要求 MA5 > MA20")
        if metrics.get("volume_ratio", 0) <= 1.5:
            reasons.append("動能模式要求量比 > 1.5")
        eps_last_4q = fundamentals.get("eps_last_4q") or []
        if not eps_last_4q or sum(eps_last_4q[-4:]) < 0:
            reasons.append("動能模式要求 EPS 不為負")
        if not _is_missing(rsi) and rsi > 75:
            warnings.append("RSI > 75，標記過熱，不列為強力標的")
    return len(reasons) == 0, reasons, warnings


def _distance_ok(value: float | None, base: float | None, max_distance: float) -> bool:
    if _is_missing(value) or _is_missing(base) or base == 0:
        return False
    return abs(value - base) / base <= max_distance


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))

