from __future__ import annotations

import pandas as pd
import requests


class TwseOpenApiClient:
    """Small TWSE OpenAPI fallback for public reference data.

    The screener uses FinMind for normalized historical datasets first. This
    class is intentionally narrow and can grow when a TWSE/TPEX endpoint is
    preferred for a specific table.
    """

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    def listed_stock_info(self) -> pd.DataFrame:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_AVG_ALL"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        return pd.DataFrame(response.json())

