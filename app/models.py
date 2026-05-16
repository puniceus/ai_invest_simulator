from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal


Market = Literal["KR", "US"]


@dataclass
class Position:
    market: Market
    ticker: str
    name: str
    shares: float
    avg_price: float
    entry_date: str
    target_price: float
    stop_price: float
    thesis: str
    days_held: int = 0


@dataclass
class Trade:
    date: str
    action: Literal["BUY", "SELL"]
    market: Market
    ticker: str
    name: str
    price: float
    shares: float
    amount: float
    reason: str
    pnl: float | None = None
    pnl_pct: float | None = None


@dataclass
class Portfolio:
    market: Market
    cash: float
    positions: list[Position] = field(default_factory=list)


@dataclass
class SimulationState:
    created_at: str
    last_run_date: str | None
    portfolios: dict[str, Portfolio]
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    strategy_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Candidate:
    market: Market
    ticker: str
    name: str
    close: float
    score: float
    momentum_5: float
    momentum_20: float
    volatility_10: float
    volume_ratio: float
    reason: str


@dataclass
class StrategyParams:
    momentum_5_weight: float = 0.35
    momentum_20_weight: float = 0.35
    volume_weight: float = 0.15
    low_volatility_weight: float = 0.15
    min_momentum_5: float = -0.03
    min_momentum_20: float = -0.08
    take_profit_pct: float = 0.09
    stop_loss_pct: float = -0.045
    max_holding_days: int = 20
    min_holding_days: int = 3
    cash_reserve_pct: float = 0.15
    max_new_buys_per_day: int = 3

