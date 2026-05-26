from __future__ import annotations

import sqlite3


def analyze_broker(conn: sqlite3.Connection, stock_id: str, broker: str) -> dict:
    rows = conn.execute(
        """
        SELECT *
        FROM broker_branch_trades
        WHERE stock_id = ? AND broker_name = ?
        ORDER BY trade_date
        """,
        (stock_id, broker),
    ).fetchall()
    if not rows:
        return {
            "stock_id": stock_id,
            "broker": broker,
            "data_status": "資料不足",
            "message": "尚未匯入合法可用的券商分點資料，因此 broker_behavior 模式暫不啟用評分。",
        }

    count = len(rows)
    next_day_reverse = _rate(rows, "next_day_reverse_sell", lambda v: v == 1)
    next_day_win = _rate(rows, "next_day_return", lambda v: v is not None and v > 0)
    win_3d = _rate(rows, "return_3d", lambda v: v is not None and v > 0)
    win_5d = _rate(rows, "return_5d", lambda v: v is not None and v > 0)
    avg_return = _avg(rows, "return_5d")
    avg_drawdown = _avg(rows, "max_drawdown")
    return {
        "stock_id": stock_id,
        "broker": broker,
        "data_status": "OK",
        "samples": count,
        "next_day_sell_rate": next_day_reverse,
        "next_day_win_rate": next_day_win,
        "win_rate_3d": win_3d,
        "win_rate_5d": win_5d,
        "avg_return_5d": avg_return,
        "avg_max_drawdown": avg_drawdown,
        "suspected_day_trade_broker": next_day_reverse >= 0.6 and avg_return < 0.5,
        "suspected_swing_broker": win_5d >= 0.55 and next_day_reverse < 0.4,
    }


def _rate(rows, key: str, predicate) -> float:
    values = [row[key] for row in rows if row[key] is not None]
    if not values:
        return 0.0
    return round(sum(1 for value in values if predicate(value)) / len(values), 3)


def _avg(rows, key: str) -> float:
    values = [float(row[key]) for row in rows if row[key] is not None]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)

