from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import KRW_INITIAL_CASH, PARAMS_PATH, STATE_PATH, USD_INITIAL_CASH, ensure_dirs
from app.models import Portfolio, Position, SimulationState, StrategyParams, Trade


def _portfolio_from_dict(data: dict[str, Any]) -> Portfolio:
    return Portfolio(
        market=data["market"],
        cash=float(data["cash"]),
        positions=[Position(**item) for item in data.get("positions", [])],
    )


def load_state() -> SimulationState:
    ensure_dirs()
    if not STATE_PATH.exists():
        now = datetime.now().isoformat(timespec="seconds")
        return SimulationState(
            created_at=now,
            last_run_date=None,
            portfolios={
                "KR": Portfolio(market="KR", cash=KRW_INITIAL_CASH),
                "US": Portfolio(market="US", cash=USD_INITIAL_CASH),
            },
        )

    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return SimulationState(
        created_at=data["created_at"],
        last_run_date=data.get("last_run_date"),
        portfolios={key: _portfolio_from_dict(value) for key, value in data["portfolios"].items()},
        trades=[Trade(**item) for item in data.get("trades", [])],
        equity_curve=data.get("equity_curve", []),
        strategy_history=data.get("strategy_history", []),
    )


def save_state(state: SimulationState) -> None:
    ensure_dirs()
    STATE_PATH.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_params() -> StrategyParams:
    ensure_dirs()
    if not PARAMS_PATH.exists():
        params = StrategyParams()
        save_params(params)
        return params
    return StrategyParams(**json.loads(PARAMS_PATH.read_text(encoding="utf-8")))


def save_params(params: StrategyParams) -> None:
    ensure_dirs()
    PARAMS_PATH.write_text(
        json.dumps(asdict(params), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
