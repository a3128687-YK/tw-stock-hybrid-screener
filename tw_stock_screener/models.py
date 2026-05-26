from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class CandidateMode(str, Enum):
    institution_accumulation = "institution_accumulation"
    mainstream = "mainstream"
    custom = "custom"


class StrategyMode(str, Enum):
    accumulation = "accumulation"
    momentum = "momentum"
    broker_behavior = "broker_behavior"


@dataclass
class StockSnapshot:
    stock_id: str
    stock_name: str | None
    trade_date: date | None
    price: float | None
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


@dataclass
class ScoreBreakdown:
    fundamental: float = 0.0
    technical: float = 0.0
    chip: float = 0.0
    market: float = 0.0
    total_100: float = 0.0
    total_10: float = 0.0
    labels: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass
class Recommendation:
    stock_id: str
    stock_name: str
    price: float | None
    score: ScoreBreakdown
    observation_zone: str
    stop_loss: str
    take_profit: str
    risks: list[str]
    grade: str
    data_status: str

