from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import requests


class FinMindClient:
    base_url = "https://api.finmindtrade.com/api/v4/data"

    def __init__(self, token: str | None = None, timeout: int = 20) -> None:
        self.token = token
        self.timeout = timeout

    def get_dataset(
        self,
        dataset: str,
        stock_id: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        **extra: Any,
    ) -> pd.DataFrame:
        params: dict[str, Any] = {"dataset": dataset}
        if stock_id:
            params["data_id"] = stock_id
        if start_date:
            params["start_date"] = str(start_date)
        if end_date:
            params["end_date"] = str(end_date)
        if self.token:
            params["token"] = self.token
        params.update(extra)

        response = requests.get(self.base_url, params=params, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != 200:
            message = payload.get("msg") or payload.get("message") or "FinMind API failed"
            raise RuntimeError(message)
        return pd.DataFrame(payload.get("data", []))

    def stock_prices(self, stock_id: str, start_date: date | str, end_date: date | str | None = None) -> pd.DataFrame:
        return self.get_dataset("TaiwanStockPrice", stock_id, start_date, end_date)

    def institutional_trades(self, stock_id: str, start_date: date | str, end_date: date | str | None = None) -> pd.DataFrame:
        return self.get_dataset("TaiwanStockInstitutionalInvestorsBuySell", stock_id, start_date, end_date)

    def monthly_revenue(self, stock_id: str, start_date: date | str, end_date: date | str | None = None) -> pd.DataFrame:
        return self.get_dataset("TaiwanStockMonthRevenue", stock_id, start_date, end_date)

    def financial_statement(self, stock_id: str, start_date: date | str, end_date: date | str | None = None) -> pd.DataFrame:
        return self.get_dataset("TaiwanStockFinancialStatements", stock_id, start_date, end_date)

    def balance_sheet(self, stock_id: str, start_date: date | str, end_date: date | str | None = None) -> pd.DataFrame:
        return self.get_dataset("TaiwanStockBalanceSheet", stock_id, start_date, end_date)

    def margin_purchase_short_sale(self, stock_id: str, start_date: date | str, end_date: date | str | None = None) -> pd.DataFrame:
        return self.get_dataset("TaiwanStockMarginPurchaseShortSale", stock_id, start_date, end_date)

