from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

from app.config import KRW_INITIAL_CASH, REPORT_PATH, USD_INITIAL_CASH, ensure_dirs
from app.models import StrategyParams, Trade


def _krw(value: float) -> str:
    return f"{value:,.0f}\uc6d0"


def _usd(value: float) -> str:
    return f"${value:,.2f}"


def _market_money(market: str, value: float) -> str:
    return _usd(value) if market == "US" else _krw(value)


def _pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}"


def _tone(value: float | None) -> str:
    if value is None:
        return "neutral"
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "neutral"


def _trade_rows(trades: list[Trade]) -> str:
    if not trades:
        return '<tr class="empty-row"><td colspan="8">&#50724;&#45720; &#44144;&#47000; &#50630;&#51020;</td></tr>'
    rows = []
    for trade in trades:
        rows.append(
            '<tr class="mobile-card">'
            f'<td data-label="&#44396;&#48516;"><span class="pill {trade.action.lower()}">{escape(trade.action)}</span></td>'
            f'<td data-label="&#49884;&#51109;">{escape(trade.market)}</td>'
            f'<td data-label="&#51333;&#47785;"><strong>{escape(trade.name)}</strong><small>{escape(trade.ticker)}</small></td>'
            f'<td data-label="&#49688;&#47049;">{trade.shares:,.0f}</td>'
            f'<td data-label="&#44032;&#44201;">{trade.price:,.2f}</td>'
            f'<td data-label="&#44552;&#50529;">{_market_money(trade.market, trade.amount)}</td>'
            f'<td data-label="&#49552;&#51061;&#47456;" class="{_tone(trade.pnl_pct)}">{_pct(trade.pnl_pct)}</td>'
            f'<td data-label="&#51060;&#50976;" class="reason">{escape(trade.reason)}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def _position_rows(snapshot: dict[str, Any]) -> str:
    rows = []
    for market, market_data in snapshot["markets"].items():
        for position in market_data["positions"]:
            pnl_pct = position["pnl_pct"]
            rows.append(
                '<tr class="mobile-card">'
                f'<td data-label="&#49884;&#51109;">{escape(market)}</td>'
                f'<td data-label="&#51333;&#47785;"><strong>{escape(position["name"])}</strong><small>{escape(position["ticker"])}</small></td>'
                f'<td data-label="&#49688;&#47049;">{position["shares"]:,.0f}</td>'
                f'<td data-label="&#54217;&#44512;&#45800;&#44032;">{position["avg_price"]:,.2f}</td>'
                f'<td data-label="&#54788;&#51116;&#44032;">{position["current_price"]:,.2f}</td>'
                f'<td data-label="&#54217;&#44032;&#44552;&#50529;">{_market_money(market, position["value"])}</td>'
                f'<td data-label="&#49688;&#51061;&#47456;" class="{_tone(pnl_pct)}">{_pct(pnl_pct)}</td>'
                f'<td data-label="&#48372;&#50976; &#51060;&#50976;" class="reason">{escape(position["thesis"])}</td>'
                "</tr>"
            )
    if not rows:
        return '<tr class="empty-row"><td colspan="8">&#48372;&#50976; &#51333;&#47785; &#50630;&#51020;</td></tr>'
    return "\n".join(rows)


def _visible_params(params: StrategyParams) -> dict[str, Any]:
    data = asdict(params)
    data.pop("min_holding_days", None)
    return data


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
<html lang="ko" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Invest Simulator</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap');
    :root {{
      color-scheme: dark;
      --bg:#090a08;
      --paper:#11130f;
      --panel:rgba(245,238,220,.075);
      --panel-strong:rgba(245,238,220,.12);
      --ink:#f4ecd8;
      --muted:#a79e8b;
      --line:rgba(244,236,216,.16);
      --accent:#d7ff64;
      --accent-2:#6ef3c5;
      --amber:#f7b955;
      --negative:#ff6b7a;
      --positive:#69f0ae;
      --shadow:0 20px 64px rgba(0,0,0,.38);
    }}
    html[data-theme="light"] {{
      color-scheme: light;
      --bg:#f4efe4;
      --paper:#fffaf0;
      --panel:rgba(35,31,24,.055);
      --panel-strong:rgba(35,31,24,.085);
      --ink:#201b13;
      --muted:#766b5a;
      --line:rgba(32,27,19,.15);
      --accent:#5b7f00;
      --accent-2:#087f63;
      --amber:#a76100;
      --negative:#b42335;
      --positive:#057a55;
      --shadow:0 18px 42px rgba(64,48,24,.12);
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0;
      min-height:100vh;
      font-family:'IBM Plex Sans KR', Arial, sans-serif;
      background:
        linear-gradient(135deg, rgba(215,255,100,.12), transparent 28%),
        linear-gradient(225deg, rgba(110,243,197,.10), transparent 32%),
        repeating-linear-gradient(90deg, transparent 0 38px, rgba(255,255,255,.025) 38px 39px),
        var(--bg);
      color:var(--ink);
      letter-spacing:0;
    }}
    body::before {{
      content:"";
      position:fixed;
      inset:0;
      pointer-events:none;
      background:linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px);
      background-size:100% 9px;
      mix-blend-mode:soft-light;
      opacity:.38;
    }}
    header, main {{
      width:min(1180px, 100%);
      margin:0 auto;
      padding-left:20px;
      padding-right:20px;
    }}
    header {{ padding-top:24px; }}
    .topbar {{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:14px;
      margin-bottom:18px;
    }}
    .brand-kicker {{
      font-family:'Chakra Petch', monospace;
      color:var(--accent);
      font-size:12px;
      font-weight:700;
      letter-spacing:.08em;
      text-transform:uppercase;
    }}
    h1 {{
      margin:2px 0 0;
      font-family:'Chakra Petch', 'IBM Plex Sans KR', sans-serif;
      font-size:28px;
      line-height:1;
      letter-spacing:0;
    }}
    .date {{
      color:var(--muted);
      font-size:13px;
      margin-top:6px;
    }}
    .theme-toggle {{
      border:1px solid var(--line);
      background:var(--panel);
      color:var(--ink);
      border-radius:6px;
      padding:10px 13px;
      font-family:'Chakra Petch', monospace;
      font-weight:700;
      cursor:pointer;
      box-shadow:var(--shadow);
    }}
    .hero {{
      position:relative;
      overflow:hidden;
      border:1px solid var(--line);
      border-radius:10px;
      background:linear-gradient(140deg, var(--panel-strong), rgba(215,255,100,.08)), var(--paper);
      padding:22px;
      box-shadow:var(--shadow);
    }}
    .hero::after {{
      content:"MARKET PAPER";
      position:absolute;
      right:-12px;
      top:12px;
      color:rgba(215,255,100,.12);
      font-family:'Chakra Petch', monospace;
      font-size:46px;
      font-weight:700;
      letter-spacing:0;
      pointer-events:none;
    }}
    .hero-label {{
      margin:0 0 8px;
      color:var(--muted);
      font-weight:700;
      font-size:13px;
    }}
    .hero-value {{
      margin:0;
      font-family:'Chakra Petch', monospace;
      font-size:56px;
      font-weight:700;
      line-height:.95;
      letter-spacing:0;
    }}
    .hero-sub {{
      max-width:680px;
      margin:14px 0 0;
      color:var(--muted);
      line-height:1.65;
      font-size:14px;
    }}
    main {{ padding-top:14px; padding-bottom:34px; }}
    .grid {{
      display:grid;
      grid-template-columns:1.25fr 1fr 1fr 1fr;
      gap:10px;
      margin:10px 0;
    }}
    .card, .section {{
      border:1px solid var(--line);
      background:var(--panel);
      border-radius:10px;
      box-shadow:var(--shadow);
      backdrop-filter:blur(14px);
    }}
    .metric {{
      min-height:112px;
      padding:15px;
      display:flex;
      flex-direction:column;
      justify-content:space-between;
    }}
    .label {{
      color:var(--muted);
      font-size:12px;
      font-weight:700;
    }}
    .value {{
      font-family:'Chakra Petch', monospace;
      font-size:25px;
      font-weight:700;
      line-height:1.1;
    }}
    .positive {{ color:var(--positive); }}
    .negative {{ color:var(--negative); }}
    .neutral {{ color:var(--muted); }}
    .section {{ margin-top:12px; overflow:hidden; }}
    .section-head {{
      padding:16px 16px 0;
      display:flex;
      justify-content:space-between;
      align-items:center;
    }}
    h2 {{
      margin:0;
      font-family:'Chakra Petch', 'IBM Plex Sans KR', sans-serif;
      font-size:18px;
      letter-spacing:0;
    }}
    .note {{
      padding:16px;
      line-height:1.72;
      color:var(--ink);
      white-space:pre-wrap;
    }}
    .table-wrap {{ padding:12px; overflow-x:auto; }}
    table {{
      width:100%;
      min-width:900px;
      border-collapse:separate;
      border-spacing:0 8px;
    }}
    th, td {{
      padding:11px 12px;
      text-align:left;
      vertical-align:top;
      font-size:14px;
    }}
    th {{
      color:var(--muted);
      font-size:12px;
      font-weight:700;
      font-family:'Chakra Petch', monospace;
    }}
    tbody tr {{ background:var(--panel-strong); }}
    tbody td:first-child {{ border-radius:8px 0 0 8px; }}
    tbody td:last-child {{ border-radius:0 8px 8px 0; }}
    td strong {{ display:block; font-weight:700; }}
    td small {{ display:block; margin-top:4px; color:var(--muted); font-family:'Chakra Petch', monospace; }}
    .reason {{ color:var(--muted); line-height:1.55; }}
    .pill {{
      display:inline-flex;
      min-width:52px;
      justify-content:center;
      border-radius:5px;
      padding:5px 8px;
      font-family:'Chakra Petch', monospace;
      font-size:12px;
      font-weight:700;
    }}
    .pill.buy {{ background:rgba(105,240,174,.14); color:var(--positive); }}
    .pill.sell {{ background:rgba(255,107,122,.14); color:var(--negative); }}
    .empty-row td {{ color:var(--muted); text-align:center; padding:24px; }}
    .params {{
      display:grid;
      grid-template-columns:repeat(4, minmax(0, 1fr));
      gap:10px;
      padding:14px;
    }}
    .param {{
      background:var(--panel-strong);
      border:1px solid var(--line);
      border-radius:8px;
      padding:11px;
      color:var(--muted);
      font-family:'Chakra Petch', 'IBM Plex Sans KR', sans-serif;
      font-size:13px;
      word-break:break-word;
    }}
    .param b {{ display:block; color:var(--ink); margin-bottom:5px; }}
    @media (max-width:860px) {{
      header, main {{ padding-left:14px; padding-right:14px; }}
      .grid {{ grid-template-columns:1fr 1fr; }}
      .params {{ grid-template-columns:1fr 1fr; }}
      .hero-value {{ font-size:44px; }}
    }}
    @media (max-width:640px) {{
      .topbar {{ align-items:flex-start; }}
      h1 {{ font-size:22px; }}
      .theme-toggle {{ padding:8px 10px; }}
      .hero {{ padding:18px; }}
      .hero::after {{ font-size:30px; top:8px; }}
      .hero-value {{ font-size:42px; }}
      .hero-sub {{ font-size:13px; }}
      .grid {{ grid-template-columns:1fr 1fr; gap:9px; }}
      .metric {{ min-height:96px; padding:13px; }}
      .value {{ font-size:21px; }}
      .table-wrap {{ overflow:visible; padding:10px; }}
      table, thead, tbody, th, td, tr {{ display:block; }}
      table {{ min-width:0; border-spacing:0; }}
      thead {{ display:none; }}
      tbody tr {{ background:transparent; }}
      .mobile-card {{
        margin-bottom:10px;
        padding:10px 12px;
        border:1px solid var(--line);
        border-radius:10px;
        background:var(--panel-strong);
      }}
      .mobile-card td {{
        display:grid;
        grid-template-columns:88px minmax(0, 1fr);
        gap:10px;
        padding:8px 0;
        border:0;
        font-size:13px;
      }}
      .mobile-card td::before {{
        content:attr(data-label);
        color:var(--muted);
        font-weight:700;
        font-size:12px;
      }}
      .mobile-card td.reason {{
        display:block;
        border-top:1px solid var(--line);
        margin-top:4px;
        padding-top:10px;
      }}
      .mobile-card td.reason::before {{ display:block; margin-bottom:6px; }}
      .params {{ grid-template-columns:1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <div class="brand-kicker">Adaptive Paper Trading</div>
        <h1>Invest Simulator</h1>
        <div class="date">{escape(today)} &#51333;&#44032; &#44592;&#51456; &#47532;&#54252;&#53944;</div>
      </div>
      <button class="theme-toggle" type="button" id="themeToggle">Light</button>
    </div>
    <section class="hero">
      <p class="hero-label">&#53685;&#54633; &#44592;&#51456; &#45572;&#51201; &#49688;&#51061;&#47456;</p>
      <p class="hero-value {_tone(cumulative_return)}">{cumulative_return:.2%}</p>
      <p class="hero-sub">&#44397;&#51109; 1,000&#47564;&#50896;&#44284; &#48120;&#51109; 10,000&#45804;&#47084;&#47484; &#48324;&#46020; &#50868;&#50857;&#54616;&#44256;, &#49884;&#51109;&#48324; &#49688;&#51061;&#47456;&#44284; &#53685;&#54633; &#49688;&#51061;&#47456;&#51012; &#54632;&#44760; &#52628;&#51201;&#54633;&#45768;&#45796;.</p>
    </section>
  </header>
  <main>
    <div class="grid">
      <div class="card metric"><div class="label">&#51068;&#51068; &#49688;&#51061;&#47456;</div><div class="value {_tone(daily_return)}">{daily_return:.2%}</div></div>
      <div class="card metric"><div class="label">&#44397;&#51109; &#49688;&#51061;&#47456;</div><div class="value {_tone(kr_return)}">{kr_return:.2%}</div></div>
      <div class="card metric"><div class="label">&#48120;&#51109; &#49688;&#51061;&#47456;</div><div class="value {_tone(us_return)}">{us_return:.2%}</div></div>
      <div class="card metric"><div class="label">&#50724;&#45720; &#44144;&#47000;</div><div class="value">{len(trades)}&#44148;</div></div>
    </div>

    <div class="grid">
      <div class="card metric"><div class="label">&#44397;&#51109; &#54217;&#44032;&#51088;&#49328;</div><div class="value">{_krw(kr['equity'])}</div></div>
      <div class="card metric"><div class="label">&#44397;&#51109; &#54788;&#44552;</div><div class="value">{_krw(kr['cash'])}</div></div>
      <div class="card metric"><div class="label">&#48120;&#51109; &#54217;&#44032;&#51088;&#49328;</div><div class="value">{_usd(us['equity'])}</div></div>
      <div class="card metric"><div class="label">&#48120;&#51109; &#54788;&#44552;</div><div class="value">{_usd(us['cash'])}</div></div>
    </div>

    <section class="section">
      <div class="section-head"><h2>AI &#54032;&#45800; &#50836;&#50557;</h2></div>
      <div class="note">{escape(str(ai_plan.get('summary', '')))}</div>
    </section>

    <section class="section">
      <div class="section-head"><h2>&#50724;&#45720;&#51032; &#47588;&#49688;/&#47588;&#46020;</h2></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>&#44396;&#48516;</th><th>&#49884;&#51109;</th><th>&#51333;&#47785;</th><th>&#49688;&#47049;</th><th>&#44032;&#44201;</th><th>&#44552;&#50529;</th><th>&#49552;&#51061;&#47456;</th><th>&#51060;&#50976;</th></tr></thead>
          <tbody>{_trade_rows(trades)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2>&#48372;&#50976; &#51333;&#47785;</h2></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>&#49884;&#51109;</th><th>&#51333;&#47785;</th><th>&#49688;&#47049;</th><th>&#54217;&#44512;&#45800;&#44032;</th><th>&#54788;&#51116;&#44032;</th><th>&#54217;&#44032;&#44552;&#50529;</th><th>&#49688;&#51061;&#47456;</th><th>&#48372;&#50976; &#51060;&#50976;</th></tr></thead>
          <tbody>{_position_rows(snapshot)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2>&#54788;&#51116; &#51204;&#47029; &#51312;&#44148;</h2></div>
      <div class="params">
        {''.join(f'<div class="param"><b>{escape(key)}</b>{escape(str(value))}</div>' for key, value in _visible_params(params).items())}
      </div>
    </section>
  </main>
  <script>
    const root = document.documentElement;
    const button = document.getElementById('themeToggle');
    const saved = localStorage.getItem('simulator-theme') || 'dark';
    function applyTheme(theme) {{
      root.dataset.theme = theme;
      button.textContent = theme === 'dark' ? 'Light' : 'Dark';
    }}
    button.addEventListener('click', () => {{
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('simulator-theme', next);
      applyTheme(next);
    }});
    applyTheme(saved);
  </script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path
