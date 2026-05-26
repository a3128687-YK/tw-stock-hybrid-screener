from __future__ import annotations

import argparse
from datetime import date, timedelta
import os
import sys
import time
from typing import Any

import requests


FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

DEFAULT_STOCKS = ["3228", "3661", "3443", "3035", "2330", "2454"]

MAINSTREAM_STOCKS = [
    "0050", "0056", "006208", "00878", "00919", "00929",
    "1101", "1216", "1301", "1303", "1326", "1402", "1590", "2002",
    "2303", "2308", "2317", "2327", "2330", "2344", "2345", "2353",
    "2356", "2376", "2377", "2382", "2395", "2408", "2412", "2454",
    "2474", "2603", "2609", "2615", "2618", "2880", "2881", "2882",
    "2883", "2884", "2885", "2886", "2887", "2890", "2891", "2892",
    "3008", "3034", "3035", "3045", "3231", "3264", "3443", "3661",
    "3711", "4938", "5347", "5871", "5880", "6505",
]


class SupabaseClient:
    def __init__(self, url: str, key: str) -> None:
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": key,
            "authorization": f"Bearer {key}",
            "content-type": "application/json",
            "prefer": "resolution=merge-duplicates",
        }

    def upsert(self, table: str, rows: list[dict[str, Any]], conflict: str) -> None:
        if not rows:
            return
        endpoint = f"{self.url}/rest/v1/{table}?on_conflict={conflict}"
        response = requests.post(endpoint, headers=self.headers, json=rows, timeout=40)
        if response.status_code >= 300:
            raise RuntimeError(f"Supabase upsert {table} failed: {response.status_code} {response.text[:500]}")


class FinMindClient:
    def __init__(self, token: str | None) -> None:
        self.token = token

    def data(self, dataset: str, stock_id: str | None = None, start: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"dataset": dataset}
        if stock_id:
            params["data_id"] = stock_id
        if start:
            params["start_date"] = start
        if self.token:
            params["token"] = self.token
        response = requests.get(FINMIND_URL, params=params, timeout=40)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != 200:
            raise RuntimeError(f"FinMind {dataset} {stock_id or ''}: {payload.get('msg') or payload}")
        return payload.get("data", [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest FinMind public Taiwan stock data into Supabase.")
    parser.add_argument("--stocks", default=os.getenv("TARGET_STOCKS", ",".join(DEFAULT_STOCKS)))
    parser.add_argument("--mainstream", action="store_true", help="Use the built-in 60-stock mainstream pool.")
    parser.add_argument("--price-days", type=int, default=int(os.getenv("PRICE_DAYS", "420")))
    parser.add_argument("--sleep", type=float, default=float(os.getenv("FINMIND_SLEEP_SECONDS", "0.4")))
    args = parser.parse_args()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    stocks = MAINSTREAM_STOCKS if args.mainstream else parse_stocks(args.stocks)
    finmind = FinMindClient(os.getenv("FINMIND_TOKEN"))
    supabase = SupabaseClient(supabase_url, supabase_key)

    print(f"Start ingest: {len(stocks)} stocks")
    upsert_stock_master(finmind, supabase, stocks)

    start_price = str(date.today() - timedelta(days=args.price_days))
    start_recent = str(date.today() - timedelta(days=90))
    start_fundamental = str(date.today() - timedelta(days=1100))

    for index, stock_id in enumerate(stocks, 1):
        print(f"[{index}/{len(stocks)}] {stock_id}")
        try:
            ingest_stock(finmind, supabase, stock_id, start_price, start_recent, start_fundamental)
        except Exception as exc:
            print(f"ERROR {stock_id}: {exc}", file=sys.stderr)
        time.sleep(args.sleep)

    print("Ingest finished")
    return 0


def upsert_stock_master(finmind: FinMindClient, supabase: SupabaseClient, stock_ids: list[str]) -> None:
    rows = []
    try:
        info = finmind.data("TaiwanStockInfo")
        wanted = set(stock_ids)
        for item in info:
            stock_id = str(item.get("stock_id") or "").strip()
            if stock_id in wanted:
                rows.append(
                    {
                        "stock_id": stock_id,
                        "stock_name": item.get("stock_name") or stock_id,
                        "market": item.get("type") or item.get("market") or None,
                        "industry": item.get("industry_category") or None,
                        "is_etf": stock_id.startswith("00"),
                    }
                )
    except Exception as exc:
        print(f"WARN stock master from FinMind failed: {exc}", file=sys.stderr)

    existing = {row["stock_id"] for row in rows}
    for stock_id in stock_ids:
        if stock_id not in existing:
            rows.append({"stock_id": stock_id, "stock_name": stock_id, "is_etf": stock_id.startswith("00")})
    supabase.upsert("stocks", rows, "stock_id")


def ingest_stock(finmind: FinMindClient, supabase: SupabaseClient, stock_id: str, start_price: str, start_recent: str, start_fundamental: str) -> None:
    supabase.upsert("daily_prices", map_prices(finmind.data("TaiwanStockPrice", stock_id, start_price)), "stock_id,trade_date")
    supabase.upsert("institutional_trades", map_institutions(finmind.data("TaiwanStockInstitutionalInvestorsBuySell", stock_id, start_recent)), "stock_id,trade_date")
    supabase.upsert("monthly_revenues", map_revenues(finmind.data("TaiwanStockMonthRevenue", stock_id, start_fundamental)), "stock_id,revenue_month")

    pe_by_date = latest_pe_by_date(safe_data(finmind, "TaiwanStockPER", stock_id, start_price))
    financial_rows = finmind.data("TaiwanStockFinancialStatements", stock_id, start_fundamental)
    balance_rows = safe_data(finmind, "TaiwanStockBalanceSheet", stock_id, start_fundamental)
    supabase.upsert("financial_quarters", map_financial_quarters(stock_id, financial_rows, balance_rows, pe_by_date), "stock_id,quarter")

    supabase.upsert("margin_trades", map_margin(safe_data(finmind, "TaiwanStockMarginPurchaseShortSale", stock_id, start_recent)), "stock_id,trade_date")
    supabase.upsert("large_holder_stats", map_large_holders(stock_id, safe_data(finmind, "TaiwanStockHoldingSharesPer", stock_id, start_recent)), "stock_id,stat_date")


def safe_data(finmind: FinMindClient, dataset: str, stock_id: str, start: str) -> list[dict[str, Any]]:
    try:
        return finmind.data(dataset, stock_id, start)
    except Exception as exc:
        print(f"WARN {dataset} {stock_id}: {exc}", file=sys.stderr)
        return []


def map_prices(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("date") and row.get("stock_id"):
            output.append(
                {
                    "stock_id": row["stock_id"],
                    "trade_date": row["date"],
                    "open": to_float(row.get("open")),
                    "high": to_float(row.get("max") or row.get("high")),
                    "low": to_float(row.get("min") or row.get("low")),
                    "close": to_float(row.get("close")),
                    "volume": to_float(row.get("Trading_Volume") or row.get("trading_volume")),
                    "value": to_float(row.get("Trading_money") or row.get("trading_money")),
                }
            )
    return output


def map_institutions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        stock_id = row.get("stock_id")
        trade_date = row.get("date")
        if not stock_id or not trade_date:
            continue
        item = grouped.setdefault(
            (stock_id, trade_date),
            {"stock_id": stock_id, "trade_date": trade_date, "foreign_net_buy": 0, "investment_trust_net_buy": 0, "dealer_net_buy": 0},
        )
        net = to_float(row.get("buy")) - to_float(row.get("sell"))
        name = str(row.get("name") or "")
        if contains_any(name, ["Foreign", "外資"]):
            item["foreign_net_buy"] += net
        elif contains_any(name, ["Investment_Trust", "投信"]):
            item["investment_trust_net_buy"] += net
        elif contains_any(name, ["Dealer", "自營"]):
            item["dealer_net_buy"] += net
    return list(grouped.values())


def map_revenues(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        month = row.get("date") or row.get("revenue_month")
        if row.get("stock_id") and month:
            output.append(
                {
                    "stock_id": row["stock_id"],
                    "revenue_month": normalize_month(month),
                    "revenue": to_float(row.get("revenue")),
                    "revenue_yoy": to_float(row.get("revenue_year_growth_rate") or row.get("revenue_yoy")),
                    "revenue_mom": to_float(row.get("revenue_month_growth_rate") or row.get("revenue_mom")),
                }
            )
    return output


def map_financial_quarters(stock_id: str, financial_rows: list[dict[str, Any]], balance_rows: list[dict[str, Any]], pe_by_date: dict[str, float]) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for row in financial_rows:
        quarter = row.get("date")
        if not quarter:
            continue
        item = by_date.setdefault(quarter, {"stock_id": stock_id, "quarter": quarter, "eps": None, "roe": None, "pe": nearest_value(quarter, pe_by_date)})
        key = str(row.get("type") or "") + str(row.get("origin_name") or "")
        value = to_float(row.get("value"))
        if contains_any(key, ["EPS", "基本每股盈餘"]):
            item["eps"] = value
        elif contains_any(key, ["ROE", "權益報酬"]):
            item["roe"] = value
        elif contains_any(key, ["GrossProfit", "營業毛利"]):
            item["gross_margin"] = value
        elif contains_any(key, ["OperatingIncome", "營業利益"]):
            item["operating_margin"] = value

    net_income = values_by_date(financial_rows, ["ProfitLossAttributableToOwnersOfParent", "歸屬於母公司業主", "本期淨利"])
    equity = values_by_date(balance_rows, ["EquityAttributableToOwnersOfParent", "權益歸屬於母公司業主", "權益總額"])
    for quarter, item in by_date.items():
        if item.get("roe") is None and equity.get(quarter):
            item["roe"] = round(net_income.get(quarter, 0) / equity[quarter] * 100, 3)
    return list(by_date.values())[-12:]


def map_margin(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        if row.get("stock_id") and row.get("date"):
            output.append(
                {
                    "stock_id": row["stock_id"],
                    "trade_date": row["date"],
                    "margin_balance": to_float(row.get("MarginPurchaseTodayBalance")),
                    "margin_change": to_float(row.get("MarginPurchaseBuy")) - to_float(row.get("MarginPurchaseSell")),
                    "short_balance": to_float(row.get("ShortSaleTodayBalance")),
                    "short_change": to_float(row.get("ShortSaleSell")) - to_float(row.get("ShortSaleBuy")),
                }
            )
    return output


def map_large_holders(stock_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, float] = {}
    for row in rows:
        stat_date = row.get("date")
        level = str(row.get("level") or row.get("HoldingSharesLevel") or "")
        ratio = to_float(row.get("percent") or row.get("HoldingSharesPercent") or row.get("ratio"))
        if stat_date and any(mark in level for mark in ["400", "800", "1000", "15", "16", "17"]):
            grouped[stat_date] = grouped.get(stat_date, 0) + ratio
    output = []
    previous = None
    for stat_date in sorted(grouped):
        ratio = grouped[stat_date]
        output.append({"stock_id": stock_id, "stat_date": stat_date, "holders_400_lots_ratio": ratio, "holders_400_lots_change": None if previous is None else ratio - previous})
        previous = ratio
    return output


def latest_pe_by_date(rows: list[dict[str, Any]]) -> dict[str, float]:
    output = {}
    for row in rows:
        pe = row.get("PER") or row.get("pe") or row.get("P_E_Ratio")
        if row.get("date") and pe not in (None, "", "-"):
            output[row["date"]] = to_float(pe)
    return output


def nearest_value(day: str, values: dict[str, float]) -> float | None:
    candidates = [key for key in values if key <= day]
    return values[max(candidates)] if candidates else None


def values_by_date(rows: list[dict[str, Any]], names: list[str]) -> dict[str, float]:
    output = {}
    for row in rows:
        key = str(row.get("type") or "") + str(row.get("origin_name") or "")
        if row.get("date") and contains_any(key, names):
            output[row["date"]] = to_float(row.get("value"))
    return output


def parse_stocks(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def contains_any(value: str, needles: list[str]) -> bool:
    lower = value.lower()
    return any(needle.lower() in lower for needle in needles)


def normalize_month(value: str) -> str:
    return f"{value}-01" if len(value) == 7 else value


def to_float(value: Any) -> float:
    try:
        if value in (None, "", "-"):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    raise SystemExit(main())

