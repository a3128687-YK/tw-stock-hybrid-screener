from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .models import Recommendation
from .screener import ScreeningOutput


DISCLAIMER = "所有結果僅作為觀察名單，不作為投資建議；不承諾收益，請搭配自行研究與風險控管。"


def print_recommendations(console: Console, output: ScreeningOutput) -> None:
    console.print(f"[bold yellow]{DISCLAIMER}[/bold yellow]")
    if not output.recommendations:
        console.print("[red]本次沒有符合條件的主名單。[/red]")
        if output.excluded:
            console.print("常見排除原因：")
            for item in output.excluded[:10]:
                console.print(f"- {item['stock_id']}: {item['reason']}")
        _print_errors(console, output.api_errors)
        return

    table = Table(title="台股混合型選股觀察名單")
    table.add_column("排名", justify="right")
    table.add_column("股票")
    table.add_column("現價", justify="right")
    table.add_column("綜合/10", justify="right")
    table.add_column("基本")
    table.add_column("技術")
    table.add_column("籌碼")
    table.add_column("市場")
    table.add_column("分級")
    table.add_column("主要風險")

    for idx, rec in enumerate(output.recommendations, 1):
        table.add_row(
            str(idx),
            f"{rec.stock_name} {rec.stock_id}",
            _money(rec.price),
            f"{rec.score.total_10:.1f}",
            f"{rec.score.fundamental:.1f}/30",
            f"{rec.score.technical:.1f}/30",
            f"{rec.score.chip:.1f}/30",
            f"{rec.score.market:.1f}/10",
            rec.grade,
            "、".join(rec.risks[:3]),
        )
    console.print(table)

    for rec in output.recommendations:
        console.print(f"\n[bold]{rec.stock_name} {rec.stock_id}[/bold]")
        console.print(f"進場觀察區：{rec.observation_zone}")
        console.print(f"停損參考：{rec.stop_loss}")
        console.print(f"停利參考：{rec.take_profit}")
        console.print(f"主要風險：{'、'.join(rec.risks)}")

    if output.warnings:
        console.print("\n[bold]標記提醒[/bold]")
        for warning in output.warnings[:10]:
            console.print(f"- {warning}")
    _print_errors(console, output.api_errors)


def print_broker_analysis(console: Console, result: dict) -> None:
    console.print(f"[bold yellow]{DISCLAIMER}[/bold yellow]")
    if result.get("data_status") != "OK":
        console.print(f"{result['stock_id']} / {result['broker']}：{result['data_status']}")
        console.print(result.get("message", ""))
        return
    table = Table(title=f"分點行為分析：{result['broker']} {result['stock_id']}")
    table.add_column("指標")
    table.add_column("數值", justify="right")
    labels = {
        "samples": "樣本數",
        "next_day_sell_rate": "隔日賣出率",
        "next_day_win_rate": "買超後隔日勝率",
        "win_rate_3d": "買超後 3 日勝率",
        "win_rate_5d": "買超後 5 日勝率",
        "avg_return_5d": "平均報酬",
        "avg_max_drawdown": "平均最大回撤",
        "suspected_day_trade_broker": "疑似隔日沖分點",
        "suspected_swing_broker": "疑似波段分點",
    }
    for key, label in labels.items():
        table.add_row(label, str(result.get(key)))
    console.print(table)


def _print_errors(console: Console, errors: list[str]) -> None:
    if errors:
        console.print("\n[bold]資料來源錯誤與 fallback 訊息[/bold]")
        for error in errors[:10]:
            console.print(f"- {error}")


def _money(value: float | None) -> str:
    return "資料不足" if value is None else f"{value:.2f}"
