from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from tw_stock_screener.broker_behavior import analyze_broker
from tw_stock_screener.config import load_config
from tw_stock_screener.database import connect, init_db
from tw_stock_screener.data_sources import DataRepository
from tw_stock_screener.screener import run_recommendation


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

app = FastAPI(
    title="台股混合型選股輔助系統",
    description="產生觀察名單，不作為投資建議。",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/recommend")
def recommend_api(
    mode: str = Query("momentum", pattern="^(accumulation|momentum)$"),
    candidate_mode: str = Query("mainstream", pattern="^(institution_accumulation|mainstream|custom)$"),
    symbols: str | None = Query(None),
    limit: int = Query(10, ge=5, le=10),
    sample: bool = Query(False),
) -> dict:
    config = load_config()
    repository = DataRepository(config.finmind_token, use_sample=sample)
    custom_symbols = [item.strip() for item in symbols.split(",") if item.strip()] if symbols else None
    if custom_symbols:
        candidate_mode = "custom"
    output = run_recommendation(
        config=config,
        repository=repository,
        strategy_mode=mode,
        candidate_mode=candidate_mode,
        custom_symbols=custom_symbols,
        limit=limit,
    )
    return {
        "disclaimer": "所有結果僅作為觀察名單，不作為投資建議；不承諾收益，請搭配自行研究與風險控管。",
        "recommendations": [_recommendation_to_dict(item) for item in output.recommendations],
        "excluded": output.excluded[:20],
        "warnings": output.warnings[:20],
        "api_errors": output.api_errors[:20],
    }


@app.get("/api/analyze-broker")
def analyze_broker_api(stock: str, broker: str) -> dict:
    config = load_config()
    init_db(config.db_path)
    with connect(config.db_path) as conn:
        return analyze_broker(conn, stock, broker)


def _recommendation_to_dict(item) -> dict:
    return {
        "stock_id": item.stock_id,
        "stock_name": item.stock_name,
        "price": item.price,
        "score_10": item.score.total_10,
        "fundamental_score": item.score.fundamental,
        "technical_score": item.score.technical,
        "chip_score": item.score.chip,
        "market_score": item.score.market,
        "grade": item.grade,
        "observation_zone": item.observation_zone,
        "stop_loss": item.stop_loss,
        "take_profit": item.take_profit,
        "risks": item.risks,
        "labels": item.score.labels,
        "data_status": item.data_status,
    }

