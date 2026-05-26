from __future__ import annotations

import math

from .candidate_pools import foreign_net_buy_5d, investment_trust_buy_streak
from .config import AppConfig
from .models import Recommendation, ScoreBreakdown


def score_stock(stock_id: str, stock_name: str, metrics: dict, fundamentals: dict, institutional_trades, config: AppConfig) -> Recommendation:
    score = ScoreBreakdown()
    score.fundamental = fundamental_score(fundamentals)
    score.technical = technical_score(metrics)
    score.chip = chip_score(fundamentals, institutional_trades)
    score.market = market_behavior_score(fundamentals, metrics)
    score.total_100 = weighted_total(score, config)
    score.total_10 = round(score.total_100 / 10, 1)
    score.labels = labels_for_score(score.total_10, metrics)

    risks = infer_risks(metrics, fundamentals)
    return Recommendation(
        stock_id=stock_id,
        stock_name=stock_name,
        price=metrics.get("price"),
        score=score,
        observation_zone=observation_zone(metrics),
        stop_loss=stop_loss_reference(metrics),
        take_profit=take_profit_reference(metrics),
        risks=risks,
        grade=grade(score.total_10),
        data_status="OK",
    )


def fundamental_score(f: dict) -> float:
    score = 0.0
    yoy = f.get("revenue_yoy")
    if yoy is None:
        pass
    elif yoy > 80:
        score += 10
    elif yoy > 50:
        score += 8
    elif yoy > 20:
        score += 5
    elif yoy > 0:
        score += 2
    else:
        score -= 5

    roe = f.get("roe")
    if roe is not None:
        if roe >= 25:
            score += 8
        elif roe >= 20:
            score += 6
        elif roe >= 15:
            score += 4
        elif roe >= 10:
            score += 2

    eps = f.get("eps_last_4q") or []
    if len(eps) >= 4:
        recent = sum(eps[-2:]) / 2
        previous = sum(eps[-4:-2]) / 2
        if recent > previous:
            score += 6
        elif math.isclose(recent, previous, rel_tol=0.05):
            score += 2
        else:
            score -= 4

    pe = f.get("pe")
    avg = f.get("pe_3y_avg")
    if pe is not None and avg:
        if pe < avg:
            score += 6
        elif pe <= avg * 1.15:
            score += 3
        elif pe > avg * 1.35:
            score -= 3
    return _clamp(score, -12, 30)


def technical_score(m: dict) -> float:
    score = 0.0
    if _gt(m.get("price"), m.get("ma20")):
        score += 5
    if _gt(m.get("ma5"), m.get("ma20")):
        score += 5
    if m.get("ma20_slope", 0) > 0:
        score += 5

    volume_ratio = m.get("volume_ratio")
    if volume_ratio is not None:
        if volume_ratio > 2:
            score += 8
        elif 1.5 <= volume_ratio <= 2:
            score += 5

    rsi = m.get("rsi")
    if rsi is not None:
        if 45 <= rsi <= 60:
            score += 6
        elif 60 < rsi <= 70:
            score += 3
        elif rsi > 75:
            score -= 5

    if _distance_from_high_ok(m.get("price"), m.get("high_20d"), 0.10):
        score += 4
    return _clamp(score, -8, 30)


def chip_score(f: dict, trades) -> float:
    score = 0.0
    streak = investment_trust_buy_streak(trades)
    if streak >= 5:
        score += 10
    elif streak >= 3:
        score += 7
    elif streak == 2:
        score += 4
    elif streak == 1:
        score += 2

    if foreign_net_buy_5d(trades) > 0:
        score += 4

    margin_change = f.get("margin_balance_change_5d_pct")
    if margin_change is None or margin_change <= 10:
        score += 5
    else:
        score -= 5

    large_holder_change = f.get("large_holder_change")
    if large_holder_change is not None and large_holder_change > 0:
        score += 6

    broker_score = f.get("broker_score")
    if broker_score is not None:
        score += broker_score
    return _clamp(score, -10, 30)


def market_behavior_score(f: dict, m: dict) -> float:
    score = 0.0
    score += min(float(f.get("topic_score") or 0), 3)
    crowded = f.get("crowded_risk", False) or (m.get("return_20d_pct", 0) > 45 and m.get("volume_ratio", 0) > 2.5)
    if not crowded:
        score += 3
    score += min(float(f.get("market_bull_score") or 0), 4)
    return _clamp(score, 0, 10)


def weighted_total(score: ScoreBreakdown, config: AppConfig) -> float:
    weights = config.weights
    return _clamp(
        score.fundamental * weights.fundamental / 30
        + score.technical * weights.technical / 30
        + score.chip * weights.chip / 30
        + score.market * weights.market / 10,
        0,
        100,
    )


def grade(score_10: float) -> str:
    if score_10 >= 8.0:
        return "強勢觀察"
    if score_10 >= 6.5:
        return "分批觀察"
    if score_10 >= 5.0:
        return "等待回測"
    return "排除"


def labels_for_score(score_10: float, metrics: dict) -> list[str]:
    labels = [grade(score_10)]
    if metrics.get("rsi", 0) > 75:
        labels.append("RSI 過熱追價風險")
    if metrics.get("return_20d_pct", 0) > 80:
        labels.append("短線過熱")
    return labels


def observation_zone(m: dict) -> str:
    parts = []
    for name in ["ma5", "ma10", "ma20"]:
        value = m.get(name)
        if value is not None and not _nan(value):
            parts.append(f"{name.upper()} {value:.2f}")
    high = m.get("high_20d")
    if high is not None and not _nan(high):
        parts.append(f"前高回測 {high:.2f} 附近")
    return "不要直接用市價追；觀察 " + "、".join(parts) if parts else "資料不足，暫不設定觀察區"


def stop_loss_reference(m: dict) -> str:
    price = m.get("price")
    atr = m.get("atr")
    if price is None or atr is None or _nan(price) or _nan(atr) or price <= 0:
        return "資料不足，暫不設定"
    atr_pct = 2 * atr / price
    clipped_pct = min(max(atr_pct, 0.015), 0.07)
    stop = price * (1 - clipped_pct)
    return f"2 x ATR 參考，限制後約 {clipped_pct * 100:.1f}%，價位約 {stop:.2f}"


def take_profit_reference(m: dict) -> str:
    parts = []
    if m.get("bb_upper") is not None and not _nan(m["bb_upper"]):
        parts.append(f"布林上軌 {m['bb_upper']:.2f}")
    if m.get("high_20d") is not None and not _nan(m["high_20d"]):
        parts.append(f"前波高點 {m['high_20d']:.2f}")
    parts.append("或沿 MA10/MA20 移動停利")
    return "、".join(parts)


def infer_risks(m: dict, f: dict) -> list[str]:
    risks: list[str] = []
    if m.get("volume_ratio", 0) > 2.5 and m.get("return_20d_pct", 0) > 35:
        risks.append("高檔爆量")
    if f.get("margin_balance_change_5d_pct") is not None and f.get("margin_balance_change_5d_pct", 0) > 10:
        risks.append("融資暴增")
    if m.get("rsi", 0) > 75:
        risks.append("RSI 過熱")
    if f.get("same_day_smart_money_net", 0) < 0:
        risks.append("法人轉賣")
    if f.get("large_holder_change") is not None and f.get("large_holder_change", 0) < 0:
        risks.append("籌碼鬆動")
    if f.get("broker_day_trade_risk"):
        risks.append("分點隔日沖倒貨")
    return risks or ["資料面未顯示主要風險，但仍需人工確認"]


def _distance_from_high_ok(price: float | None, high: float | None, distance: float) -> bool:
    if price is None or high is None or _nan(price) or _nan(high) or high == 0:
        return False
    return (high - price) / high <= distance


def _gt(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and not _nan(left) and not _nan(right) and left > right


def _nan(value: float) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))

