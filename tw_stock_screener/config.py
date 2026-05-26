from __future__ import annotations

from dataclasses import dataclass, field
import os


DEFAULT_MAINSTREAM_POOL = [
    "0050", "0056", "006208", "00878", "00919", "00929",
    "1101", "1216", "1301", "1303", "1326", "1402", "1590", "2002",
    "2303", "2308", "2317", "2327", "2330", "2344", "2345", "2353",
    "2356", "2376", "2377", "2382", "2395", "2408", "2412", "2454",
    "2474", "2603", "2609", "2615", "2618", "2880", "2881", "2882",
    "2883", "2884", "2885", "2886", "2887", "2890", "2891", "2892",
    "3008", "3034", "3035", "3045", "3231", "3264", "3443", "3661",
    "3711", "4938", "5347", "5871", "5880", "6505",
]


@dataclass
class HardFilterConfig:
    min_roe: float = 8.0
    min_avg_volume_3m: float = 800.0
    min_price: float = 20.0
    exclude_low_price: bool = True
    overheated_20d_return: float = 80.0
    long_upper_shadow_ratio: float = 0.45
    high_risk_volume_ratio: float = 2.5


@dataclass
class TechnicalFilterConfig:
    min_52w_high_ratio: float = 0.70
    min_volume_to_ma5: float = 0.80
    max_rsi: float = 75.0


@dataclass
class ScoreWeights:
    fundamental: float = 30.0
    technical: float = 30.0
    chip: float = 30.0
    market: float = 10.0


@dataclass
class AppConfig:
    finmind_token: str | None = field(default_factory=lambda: os.getenv("FINMIND_TOKEN") or None)
    db_path: str = field(default_factory=lambda: os.getenv("TW_STOCK_DB", "data/tw_stock_screener.sqlite3"))
    hard_filters: HardFilterConfig = field(default_factory=HardFilterConfig)
    technical_filters: TechnicalFilterConfig = field(default_factory=TechnicalFilterConfig)
    weights: ScoreWeights = field(default_factory=ScoreWeights)
    mainstream_pool: list[str] = field(default_factory=lambda: DEFAULT_MAINSTREAM_POOL.copy())


def load_config() -> AppConfig:
    return AppConfig()
