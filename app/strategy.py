from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from app.config import KR_UNIVERSE, US_UNIVERSE
from app.models import Candidate, Portfolio, Position, StrategyParams, Trade


def _pct_change(series: pd.Series, days: int) -> float:
    if len(series) <= days:
        return 0.0
    before = float(series.iloc[-days - 1])
    now = float(series.iloc[-1])
    if before == 0:
        return 0.0
    return (now / before) - 1


def score_candidates(history: dict[str, dict[str, pd.DataFrame]], params: StrategyParams) -> list[Candidate]:
    candidates: list[Candidate] = []
    names = {"KR": KR_UNIVERSE, "US": US_UNIVERSE}
    for market, frames in history.items():
        for ticker, frame in frames.items():
            close = frame["close"].astype(float)
            volume = frame["volume"].astype(float)
            momentum_5 = _pct_change(close, 5)
            momentum_20 = _pct_change(close, 20)
            volatility_10 = float(close.pct_change().tail(10).std() or 0)
            recent_volume = float(volume.tail(5).mean() or 0)
            base_volume = float(volume.tail(20).mean() or 1)
            volume_ratio = recent_volume / base_volume if base_volume else 1.0

            if momentum_5 < params.min_momentum_5 or momentum_20 < params.min_momentum_20:
                continue

            low_vol_score = max(0.0, 1.0 - min(volatility_10, 0.08) / 0.08)
            score = (
                params.momentum_5_weight * momentum_5
                + params.momentum_20_weight * momentum_20
                + params.volume_weight * min(volume_ratio - 1.0, 1.5)
                + params.low_volatility_weight * low_vol_score
            )
            reason = (
                f"5일 모멘텀 {momentum_5:.1%}, 20일 모멘텀 {momentum_20:.1%}, "
                f"거래량 배율 {volume_ratio:.2f}, 10일 변동성 {volatility_10:.1%}"
            )
            candidates.append(
                Candidate(
                    market=market,  # type: ignore[arg-type]
                    ticker=ticker,
                    name=names[market][ticker],
                    close=float(close.iloc[-1]),
                    score=float(score),
                    momentum_5=float(momentum_5),
                    momentum_20=float(momentum_20),
                    volatility_10=float(volatility_10),
                    volume_ratio=float(volume_ratio),
                    reason=reason,
                )
            )
    return sorted(candidates, key=lambda item: item.score, reverse=True)


def _current_price(history: dict[str, dict[str, pd.DataFrame]], position: Position) -> float | None:
    frame = history.get(position.market, {}).get(position.ticker)
    if frame is None or frame.empty:
        return None
    return float(frame["close"].iloc[-1])


def build_sell_orders(
    today: str,
    portfolios: dict[str, Portfolio],
    history: dict[str, dict[str, pd.DataFrame]],
    params: StrategyParams,
    ai_plan: dict[str, Any] | None = None,
) -> list[Trade]:
    sells: list[Trade] = []
    sell_decisions = ai_plan.get("sell_decisions", {}) if isinstance(ai_plan, dict) else {}
    for portfolio in portfolios.values():
        remaining: list[Position] = []
        for position in portfolio.positions:
            price = _current_price(history, position)
            if price is None:
                remaining.append(position)
                continue
            position.days_held += 1
            pnl = (price - position.avg_price) * position.shares
            pnl_pct = price / position.avg_price - 1
            reason = ""
            if pnl_pct <= params.stop_loss_pct:
                reason = f"손절 기준 도달: {pnl_pct:.1%}"
            elif pnl_pct >= params.take_profit_pct:
                decision = sell_decisions.get(position.ticker, {})
                if isinstance(decision, dict) and str(decision.get("action", "")).upper() == "HOLD":
                    position.thesis = str(decision.get("reason") or f"익절 기준을 넘었지만 추가 상승 여지가 있어 홀딩: {pnl_pct:.1%}")
                    remaining.append(position)
                    continue
                reason = str(decision.get("reason") if isinstance(decision, dict) else "") or f"익절 기준 도달: {pnl_pct:.1%}"
            elif position.days_held >= params.max_holding_days:
                reason = f"최대 보유기간 {params.max_holding_days}일 도달"

            if reason:
                amount = price * position.shares
                portfolio.cash += amount
                sells.append(
                    Trade(
                        date=today,
                        action="SELL",
                        market=position.market,
                        ticker=position.ticker,
                        name=position.name,
                        price=price,
                        shares=position.shares,
                        amount=amount,
                        reason=reason,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                    )
                )
            else:
                remaining.append(position)
        portfolio.positions = remaining
    return sells


def build_buy_orders(
    today: str,
    portfolios: dict[str, Portfolio],
    candidates: list[Candidate],
    params: StrategyParams,
    ai_plan: dict[str, Any] | None = None,
) -> list[Trade]:
    allowed = params.max_new_buys_per_day
    if ai_plan and isinstance(ai_plan.get("buy_tickers"), list):
        rank = {ticker: idx for idx, ticker in enumerate(ai_plan["buy_tickers"])}
        candidates = sorted(candidates, key=lambda item: (rank.get(item.ticker, 999), -item.score))

    buys: list[Trade] = []
    held = {(pos.market, pos.ticker) for portfolio in portfolios.values() for pos in portfolio.positions}
    for candidate in candidates:
        if len(buys) >= allowed:
            break
        if (candidate.market, candidate.ticker) in held:
            continue
        portfolio = portfolios[candidate.market]
        investable = portfolio.cash * (1.0 - params.cash_reserve_pct)
        if investable <= 0:
            continue
        slots_left = max(1, allowed - len(buys))
        budget = investable / slots_left
        shares = int(budget // candidate.close)
        if shares <= 0:
            continue
        amount = shares * candidate.close
        portfolio.cash -= amount
        thesis = candidate.reason
        if ai_plan and isinstance(ai_plan.get("rationales"), dict):
            thesis = ai_plan["rationales"].get(candidate.ticker, thesis)
        portfolio.positions.append(
            Position(
                market=candidate.market,
                ticker=candidate.ticker,
                name=candidate.name,
                shares=shares,
                avg_price=candidate.close,
                entry_date=today,
                target_price=candidate.close * (1 + params.take_profit_pct),
                stop_price=candidate.close * (1 + params.stop_loss_pct),
                thesis=thesis,
            )
        )
        buys.append(
            Trade(
                date=today,
                action="BUY",
                market=candidate.market,
                ticker=candidate.ticker,
                name=candidate.name,
                price=candidate.close,
                shares=shares,
                amount=amount,
                reason=thesis,
            )
        )
    return buys


def portfolio_snapshot(portfolios: dict[str, Portfolio], history: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    markets: dict[str, Any] = {}
    total = 0.0
    for key, portfolio in portfolios.items():
        position_value = 0.0
        positions = []
        for position in portfolio.positions:
            price = _current_price(history, position) or position.avg_price
            value = price * position.shares
            position_value += value
            positions.append({**asdict(position), "current_price": price, "value": value, "pnl_pct": price / position.avg_price - 1})
        equity = portfolio.cash + position_value
        total += equity
        markets[key] = {"cash": portfolio.cash, "position_value": position_value, "equity": equity, "positions": positions}
    return {"total_equity": total, "markets": markets}
