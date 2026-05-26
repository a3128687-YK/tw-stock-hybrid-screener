from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from tw_stock_screener.broker_behavior import analyze_broker
from tw_stock_screener.config import load_config
from tw_stock_screener.database import connect, init_db
from tw_stock_screener.data_sources import DataRepository
from tw_stock_screener.reporting import print_broker_analysis, print_recommendations
from tw_stock_screener.screener import run_recommendation

app = typer.Typer(help="台股混合型選股輔助系統：產生觀察名單，不作為投資建議。")
console = Console()


@app.command("init-db")
def init_db_command(
    db_path: Annotated[str | None, typer.Option("--db-path", help="SQLite 資料庫路徑。")] = None,
) -> None:
    config = load_config()
    init_db(db_path or config.db_path)
    console.print(f"資料庫已初始化：{db_path or config.db_path}")


@app.command()
def recommend(
    mode: Annotated[str, typer.Option("--mode", help="策略模式：accumulation 或 momentum。")] = "momentum",
    candidate_mode: Annotated[
        str,
        typer.Option("--candidate-mode", help="候選池：institution_accumulation、mainstream、custom。"),
    ] = "mainstream",
    symbols: Annotated[str | None, typer.Option("--symbols", help="自訂代號，例如 3228,3661,3443,3035。")] = None,
    limit: Annotated[int, typer.Option("--limit", min=5, max=10, help="輸出 5~10 檔。")] = 10,
    sample: Annotated[bool, typer.Option("--sample", help="使用內建假資料示範 CLI 與輸出格式。")] = False,
) -> None:
    config = load_config()
    repository = DataRepository(config.finmind_token, use_sample=sample)
    custom_symbols = [item.strip() for item in symbols.split(",")] if symbols else None
    if symbols and candidate_mode != "custom":
        candidate_mode = "custom"
    output = run_recommendation(
        config=config,
        repository=repository,
        strategy_mode=mode,
        candidate_mode=candidate_mode,
        custom_symbols=custom_symbols,
        limit=limit,
    )
    print_recommendations(console, output)


@app.command("analyze-broker")
def analyze_broker_command(
    stock: Annotated[str, typer.Option("--stock", help="股票代號，例如 3228。")],
    broker: Annotated[str, typer.Option("--broker", help="券商分點名稱，例如 凱基台北。")],
    db_path: Annotated[str | None, typer.Option("--db-path", help="SQLite 資料庫路徑。")] = None,
) -> None:
    config = load_config()
    init_db(db_path or config.db_path)
    with connect(db_path or config.db_path) as conn:
        result = analyze_broker(conn, stock, broker)
    print_broker_analysis(console, result)


if __name__ == "__main__":
    app()
