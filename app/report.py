from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

from app.config import KRW_INITIAL_CASH, REPORT_PATH, USD_INITIAL_CASH, ensure_dirs
from app.models import StrategyParams, Trade


def _krw(value: float) -> str:
    return f"{value:,.0f}원"


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _market_money(market: str, value: float) -> str:
    return _usd(value) if market == "US" else _krw(value)


def _pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}"


def _trade_rows(trades: list[Trade]) -> str:
    if not trades:
        return '<tr><td colspan="8" class="muted">오늘 거래 없음</td></tr>'
    rows = []
    for trade in trades:
        rows.append(
            "<tr>"
            f"<td>{escape(trade.action)}</td>"
            f"<td>{escape(trade.market)}</td>"
            f"<td>{escape(trade.name)} <span>{escape(trade.ticker)}</span></td>"
            f"<td>{trade.shares:,.0f}</td>"
            f"<td>{trade.price:,.2f}</td>"
            f"<td>{_market_money(trade.market, trade.amount)}</td>"
            f"<td>{_pct(trade.pnl_pct)}</td>"
            f"<td>{escape(trade.reason)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _position_rows(snapshot: dict[str, Any]) -> str:
    rows = []
    for market, market_data in snapshot["markets"].items():
        for position in market_data["positions"]:
            rows.append(
                "<tr>"
                f"<td>{escape(market)}</td>"
                f"<td>{escape(position['name'])} <span>{escape(position['ticker'])}</span></td>"
                f"<td>{position['shares']:,.0f}</td>"
                f"<td>{position['avg_price']:,.2f}</td>"
                f"<td>{position['current_price']:,.2f}</td>"
                f"<td>{_market_money(market, position['value'])}</td>"
                f"<td>{_pct(position['pnl_pct'])}</td>"
                f"<td>{escape(position['thesis'])}</td>"
                "</tr>"
            )
    if not rows:
        return '<tr><td colspan="8" class="muted">보유 종목 없음</td></tr>'
    return "\n".join(rows)


def build_report(
    today: str,
    snapshot: dict[str, Any],
    daily_return: float,
    cumulative_return: float,
    trades: list[Trade],
    ai_plan: dict[str, Any],
    params: StrategyParams,
    output_path: Path = REPORT_PATH,
) -> Path:
    ensure_dirs()
    kr = snapshot["markets"]["KR"]
    us = snapshot["markets"]["US"]
    kr_return = kr["equity"] / KRW_INITIAL_CASH - 1
    us_return = us["equity"] / USD_INITIAL_CASH - 1
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Invest Simulator</title>
  <style>
    :root {{ color-scheme: light; --ink:#18212f; --muted:#657184; --line:#d9e0ea; --bg:#f5f7fa; --panel:#ffffff; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial, 'Malgun Gothic', sans-serif; background:var(--bg); color:var(--ink); }}
    header {{ background:#101828; color:white; padding:28px 32px; }}
    header h1 {{ margin:0 0 8px; font-size:28px; }}
    header p {{ margin:0; color:#cbd5e1; }}
    main {{ max-width:1240px; margin:0 auto; padding:24px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:14px; margin-bottom:18px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }}
    .label {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
    .value {{ font-size:24px; font-weight:700; }}
    .section {{ margin-top:18px; }}
    h2 {{ font-size:18px; margin:0 0 12px; }}
    table {{ width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:14px; }}
    th {{ background:#edf2f7; font-size:13px; color:#344054; }}
    td span {{ color:var(--muted); font-size:12px; }}
    .muted {{ color:var(--muted); }}
    .note {{ line-height:1.6; white-space:pre-wrap; }}
    .params {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:8px; font-size:13px; }}
    .param {{ background:#f8fafc; border:1px solid var(--line); border-radius:6px; padding:8px; }}
    @media (max-width:900px) {{ .grid, .params {{ grid-template-columns:1fr 1fr; }} main {{ padding:16px; }} }}
    @media (max-width:620px) {{ .grid, .params {{ grid-template-columns:1fr; }} th, td {{ font-size:12px; padding:8px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>AI Invest Simulator</h1>
    <p>{escape(today)} 종가 기준 가상 투자 리포트</p>
  </header>
  <main>
    <div class="grid">
      <div class="card"><div class="label">통합 기준 수익률</div><div class="value">{cumulative_return:.2%}</div></div>
      <div class="card"><div class="label">일일 수익률</div><div class="value">{daily_return:.2%}</div></div>
      <div class="card"><div class="label">국장 수익률</div><div class="value">{kr_return:.2%}</div></div>
      <div class="card"><div class="label">미장 수익률</div><div class="value">{us_return:.2%}</div></div>
    </div>

    <div class="grid">
      <div class="card"><div class="label">국장 평가자산</div><div class="value">{_krw(kr['equity'])}</div></div>
      <div class="card"><div class="label">국장 현금</div><div class="value">{_krw(kr['cash'])}</div></div>
      <div class="card"><div class="label">미장 평가자산</div><div class="value">{_usd(us['equity'])}</div></div>
      <div class="card"><div class="label">미장 현금</div><div class="value">{_usd(us['cash'])}</div></div>
    </div>

    <section class="section card">
      <h2>AI 판단 요약</h2>
      <div class="note">{escape(str(ai_plan.get('summary', '')))}</div>
    </section>

    <section class="section">
      <h2>오늘의 매수/매도</h2>
      <table>
        <thead><tr><th>구분</th><th>시장</th><th>종목</th><th>수량</th><th>가격</th><th>금액</th><th>손익률</th><th>이유</th></tr></thead>
        <tbody>{_trade_rows(trades)}</tbody>
      </table>
    </section>

    <section class="section">
      <h2>보유 종목</h2>
      <table>
        <thead><tr><th>시장</th><th>종목</th><th>수량</th><th>평균단가</th><th>현재가</th><th>평가금액</th><th>수익률</th><th>보유 이유</th></tr></thead>
        <tbody>{_position_rows(snapshot)}</tbody>
      </table>
    </section>

    <section class="section card">
      <h2>현재 전략 조건</h2>
      <div class="params">
        {''.join(f'<div class="param"><b>{escape(key)}</b><br>{escape(str(value))}</div>' for key, value in asdict(params).items())}
      </div>
    </section>
  </main>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
