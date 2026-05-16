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


def run_once(config: RuntimeConfig, force: bool = False) -> dict[str, object]:
    ensure_dirs()
    today = datetime.now(ZoneInfo(KST_TIMEZONE)).strftime("%Y-%m-%d")
    state = load_state()
    params = load_params()
    if state.last_run_date == today and not force:
        return {
            "date": today,
            "skipped": True,
            "reason": "already_ran_today",
            "message": "오늘은 이미 실행했습니다. 중복 매매를 막기 위해 건너뜁니다.",
        }

    history = load_universe(use_mock_data=config.use_mock_data)
    candidates = score_candidates(history, params)
    pre_snapshot = portfolio_snapshot(state.portfolios, history)
    ai_plan = ask_ai_for_plan(
        today=today,
        candidates=candidates,
        snapshot=pre_snapshot,
        params=params,
        recent_trades=[asdict(item) for item in state.trades],
        allow_ai=config.allow_ai,
    )

    updated_params = clamp_param_updates(params, ai_plan.get("param_updates", {}) if isinstance(ai_plan, dict) else {})
    sells = build_sell_orders(today, state.portfolios, history, updated_params, ai_plan)
    buys = build_buy_orders(today, state.portfolios, candidates, updated_params, ai_plan)
    trades = sells + buys
    state.trades.extend(trades)

    snapshot = portfolio_snapshot(state.portfolios, history)
    kr_equity = snapshot["markets"]["KR"]["equity"]
    us_equity = snapshot["markets"]["US"]["equity"]
    normalized_equity = (kr_equity / KRW_INITIAL_CASH) + (us_equity / USD_INITIAL_CASH)
    previous_normalized = state.equity_curve[-1]["normalized_equity"] if state.equity_curve else 2.0
    daily_return = normalized_equity / previous_normalized - 1 if previous_normalized else 0.0
    cumulative_return = normalized_equity / 2.0 - 1

    state.last_run_date = today
    state.equity_curve.append(
        {
            "date": today,
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
    state.strategy_history.append({"date": today, "params": asdict(updated_params), "ai_plan": ai_plan})

    save_params(updated_params)
    save_state(state)
    report_path = build_report(today, snapshot, daily_return, cumulative_return, trades, ai_plan, updated_params)

    return {
        "date": today,
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
    today = state.last_run_date or datetime.now(ZoneInfo(KST_TIMEZONE)).strftime("%Y-%m-%d")
    history = load_universe(use_mock_data=config.use_mock_data)
    snapshot = portfolio_snapshot(state.portfolios, history)
    latest_curve = state.equity_curve[-1] if state.equity_curve else {}
    daily_return = float(latest_curve.get("daily_return", 0.0))
    cumulative_return = float(latest_curve.get("cumulative_return", 0.0))
    latest_strategy = state.strategy_history[-1] if state.strategy_history else {}
    ai_plan = latest_strategy.get("ai_plan", {"summary": "아직 생성된 AI 판단 요약이 없습니다."})
    trades = [trade for trade in state.trades if trade.date == today]
    report_path = build_report(today, snapshot, daily_return, cumulative_return, trades, ai_plan, params)
    return {
        "date": today,
        "report_path": str(report_path),
        "trades": len(trades),
        "render_only": True,
    }
