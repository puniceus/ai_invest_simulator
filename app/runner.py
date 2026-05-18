from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from app.ai import ask_ai_for_plan, clamp_param_updates
from app.config import KRW_INITIAL_CASH, KST_TIMEZONE, USD_INITIAL_CASH, RuntimeConfig, ensure_dirs
from app.data_provider import load_universe
from app.report import build_report
from app.storage import load_params, load_state, save_params, save_state
from app.strategy import build_buy_orders, build_sell_orders, portfolio_snapshot, score_candidates


MarketArg = str | None


def _today_kst() -> str:
    return datetime.now(ZoneInfo(KST_TIMEZONE)).strftime("%Y-%m-%d")


def _already_ran_market(strategy_history: list[dict], today: str, market: str | None) -> bool:
    key = market or "ALL"
    return any(item.get("date") == today and item.get("market", "ALL") == key for item in strategy_history)


def _returns(snapshot: dict) -> tuple[float, float, float, float]:
    kr_equity = snapshot["markets"]["KR"]["equity"]
    us_equity = snapshot["markets"]["US"]["equity"]
    normalized_equity = (kr_equity / KRW_INITIAL_CASH) + (us_equity / USD_INITIAL_CASH)
    cumulative_return = normalized_equity / 2.0 - 1
    return kr_equity, us_equity, normalized_equity, cumulative_return


def run_once(config: RuntimeConfig, force: bool = False, market: MarketArg = None) -> dict[str, object]:
    ensure_dirs()
    today = _today_kst()
    state = load_state()
    params = load_params()
    market = market.upper() if market else None
    if market not in {None, "KR", "US"}:
        raise ValueError("market must be one of KR, US, or omitted")
    if _already_ran_market(state.strategy_history, today, market) and not force:
        return {
            "date": today,
            "market": market or "ALL",
            "skipped": True,
            "reason": "already_ran_today_market",
            "message": "This market has already run today. Skipped to prevent duplicate trading.",
        }

    history = load_universe(use_mock_data=config.use_mock_data)
    candidates = score_candidates(history, params)
    active_candidates = [candidate for candidate in candidates if market is None or candidate.market == market]
    pre_snapshot = portfolio_snapshot(state.portfolios, history)
    ai_plan = ask_ai_for_plan(
        today=today,
        candidates=active_candidates,
        snapshot=pre_snapshot,
        params=params,
        recent_trades=[asdict(item) for item in state.trades],
        allow_ai=config.allow_ai,
    )

    updated_params = clamp_param_updates(params, ai_plan.get("param_updates", {}) if isinstance(ai_plan, dict) else {})
    sells = build_sell_orders(today, state.portfolios, history, updated_params, ai_plan, market=market)
    buys = build_buy_orders(
        today,
        state.portfolios,
        active_candidates,
        updated_params,
        ai_plan,
        market=market,
        require_explicit_ai_buys=config.allow_ai,
    )
    trades = sells + buys
    state.trades.extend(trades)

    snapshot = portfolio_snapshot(state.portfolios, history)
    kr_equity, us_equity, normalized_equity, cumulative_return = _returns(snapshot)
    previous_normalized = state.equity_curve[-1]["normalized_equity"] if state.equity_curve else 2.0
    daily_return = normalized_equity / previous_normalized - 1 if previous_normalized else 0.0

    state.last_run_date = today
    state.equity_curve.append(
        {
            "date": today,
            "market": market or "ALL",
            "total_equity": snapshot["total_equity"],
            "normalized_equity": normalized_equity,
            "kr_equity": kr_equity,
            "us_equity": us_equity,
            "kr_return": kr_equity / KRW_INITIAL_CASH - 1,
            "us_return": us_equity / USD_INITIAL_CASH - 1,
            "daily_return": daily_return,
            "cumulative_return": cumulative_return,
        }
    )
    state.strategy_history.append({"date": today, "market": market or "ALL", "params": asdict(updated_params), "ai_plan": ai_plan})

    save_params(updated_params)
    save_state(state)
    report_path = build_report(today, snapshot, daily_return, cumulative_return, trades, ai_plan, updated_params)

    return {
        "date": today,
        "market": market or "ALL",
        "report_path": str(report_path),
        "trades": len(trades),
        "kr_equity": kr_equity,
        "us_equity": us_equity,
        "daily_return": daily_return,
        "cumulative_return": cumulative_return,
    }


def render_latest(config: RuntimeConfig) -> dict[str, object]:
    state = load_state()
    params = load_params()
    today = state.last_run_date or _today_kst()
    history = load_universe(use_mock_data=config.use_mock_data)
    snapshot = portfolio_snapshot(state.portfolios, history)
    latest_curve = state.equity_curve[-1] if state.equity_curve else {}
    daily_return = float(latest_curve.get("daily_return", 0.0))
    cumulative_return = float(latest_curve.get("cumulative_return", 0.0))
    latest_strategy = state.strategy_history[-1] if state.strategy_history else {}
    ai_plan = latest_strategy.get("ai_plan", {"summary": "No AI summary has been generated yet."})
    trades = [trade for trade in state.trades if trade.date == today]
    report_path = build_report(today, snapshot, daily_return, cumulative_return, trades, ai_plan, params)
    return {
        "date": today,
        "report_path": str(report_path),
        "trades": len(trades),
        "render_only": True,
    }
