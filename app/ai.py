from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

from google import genai

from app.config import load_environment
from app.models import Candidate, StrategyParams


DEFAULT_MODEL = "gemini-3-flash-preview"


def _client() -> genai.Client | None:
    load_environment()
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None
    return genai.Client(api_key=key)


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        stripped = stripped[start : end + 1]
    return json.loads(stripped)


def ask_ai_for_plan(
    today: str,
    candidates: list[Candidate],
    snapshot: dict[str, Any],
    params: StrategyParams,
    recent_trades: list[dict[str, Any]],
    allow_ai: bool = True,
) -> dict[str, Any]:
    if not allow_ai:
        return {"summary": "AI 비활성화 상태라 정량 전략만 사용했습니다.", "buy_tickers": [], "rationales": {}, "param_updates": {}}
    client = _client()
    if client is None:
        return {"summary": "GEMINI_API_KEY가 없어 정량 전략만 사용했습니다.", "buy_tickers": [], "rationales": {}, "param_updates": {}}

    compact_candidates = [asdict(item) for item in candidates[:15]]
    prompt = f"""
너는 가상 투자 시뮬레이터의 전략 조정 엔진이다. 실제 주문은 없고, 종가 기준 시뮬레이션만 한다.
목표는 국장/미장 가상 포트폴리오의 성장이다. 현금 0~100%, 단일 종목 집중도 허용된다.
다만 하루 신규 매수는 최대 3개이고, 기본 매매는 3~20일 스윙이다.

날짜: {today}
현재 전략 파라미터: {json.dumps(asdict(params), ensure_ascii=False)}
현재 포트폴리오: {json.dumps(snapshot, ensure_ascii=False)}
최근 거래: {json.dumps(recent_trades[-20:], ensure_ascii=False)}
정량 후보 상위: {json.dumps(compact_candidates, ensure_ascii=False)}

아래 JSON만 반환해라.
{{
  "summary": "오늘 판단 요약",
  "buy_tickers": ["최대 3개 ticker"],
  "rationales": {{"ticker": "매수/보유 판단 이유"}},
  "param_updates": {{
    "momentum_5_weight": 0.35,
    "momentum_20_weight": 0.35,
    "volume_weight": 0.15,
    "low_volatility_weight": 0.15,
    "min_momentum_5": -0.03,
    "min_momentum_20": -0.08,
    "take_profit_pct": 0.09,
    "stop_loss_pct": -0.045,
    "max_holding_days": 20,
    "min_holding_days": 3,
    "cash_reserve_pct": 0.15
  }}
}}
"""
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
        return _extract_json(response.text or "{}")
    except Exception as exc:
        return {"summary": f"Gemini 호출 실패로 정량 전략만 사용했습니다: {exc}", "buy_tickers": [], "rationales": {}, "param_updates": {}}


def clamp_param_updates(params: StrategyParams, updates: dict[str, Any]) -> StrategyParams:
    data = asdict(params)
    ranges = {
        "momentum_5_weight": (0.0, 1.0),
        "momentum_20_weight": (0.0, 1.0),
        "volume_weight": (0.0, 1.0),
        "low_volatility_weight": (0.0, 1.0),
        "min_momentum_5": (-0.2, 0.15),
        "min_momentum_20": (-0.35, 0.25),
        "take_profit_pct": (0.02, 0.35),
        "stop_loss_pct": (-0.25, -0.01),
        "cash_reserve_pct": (0.0, 1.0),
    }
    for key, value in updates.items():
        if key in ranges:
            low, high = ranges[key]
            data[key] = min(high, max(low, float(value)))
        elif key == "max_holding_days":
            data[key] = int(min(20, max(3, int(value))))
        elif key == "min_holding_days":
            data[key] = int(min(10, max(1, int(value))))

    if data["min_holding_days"] > data["max_holding_days"]:
        data["min_holding_days"] = min(3, data["max_holding_days"])
    return StrategyParams(**data)

