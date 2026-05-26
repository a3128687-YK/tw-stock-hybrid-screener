from __future__ import annotations

from dataclasses import dataclass, field

from .candidate_pools import build_candidate_pool
from .config import AppConfig
from .data_sources import DataRepository
from .filters import hard_filter, strategy_filter, technical_filter
from .indicators import latest_metrics
from .models import Recommendation
from .scoring import score_stock


@dataclass
class ScreeningOutput:
    recommendations: list[Recommendation] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    api_errors: list[str] = field(default_factory=list)


def run_recommendation(
    config: AppConfig,
    repository: DataRepository,
    strategy_mode: str = "momentum",
    candidate_mode: str = "mainstream",
    custom_symbols: list[str] | None = None,
    limit: int = 10,
) -> ScreeningOutput:
    output = ScreeningOutput()
    symbols = build_candidate_pool(candidate_mode, config, repository, custom_symbols)
    for stock_id in symbols:
        prices = repository.prices(stock_id)
        trades = repository.institutional_trades(stock_id)
        fundamentals = repository.fundamentals(stock_id)

        metrics = latest_metrics(prices)
        if not metrics:
            output.excluded.append({"stock_id": stock_id, "reason": "價格資料不足"})
            continue

        hard_ok, hard_reasons, hard_warnings = hard_filter(metrics, fundamentals, config)
        tech_ok, tech_reasons, tech_warnings = technical_filter(metrics, config)
        strategy_ok, strategy_reasons, strategy_warnings = strategy_filter(strategy_mode, metrics, fundamentals)
        output.warnings.extend([f"{stock_id}: {warning}" for warning in hard_warnings + tech_warnings + strategy_warnings])

        if not (hard_ok and tech_ok and strategy_ok):
            output.excluded.append(
                {
                    "stock_id": stock_id,
                    "reason": "；".join(hard_reasons + tech_reasons + strategy_reasons),
                }
            )
            continue

        recommendation = score_stock(stock_id, stock_id, metrics, fundamentals, trades, config)
        if "RSI 過熱追價風險" in recommendation.score.labels and recommendation.score.total_10 >= 8:
            recommendation.grade = "分批觀察"
        if recommendation.score.total_10 >= 5:
            output.recommendations.append(recommendation)

    output.recommendations.sort(key=lambda rec: rec.score.total_10, reverse=True)
    output.recommendations = output.recommendations[:limit]
    output.api_errors = repository.errors
    return output

