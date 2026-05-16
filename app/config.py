from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
STATE_PATH = DATA_DIR / "state.json"
PARAMS_PATH = DATA_DIR / "strategy_params.json"
REPORT_PATH = REPORT_DIR / "simulator.html"

KST_TIMEZONE = "Asia/Seoul"

KRW_INITIAL_CASH = 10_000_000.0
USD_INITIAL_CASH = 10_000.0


KR_UNIVERSE = {
    "005930": "삼성전자",
    "000660": "SK하이닉스",
    "373220": "LG에너지솔루션",
    "207940": "삼성바이오로직스",
    "005380": "현대차",
    "000270": "기아",
    "068270": "셀트리온",
    "035420": "NAVER",
    "035720": "카카오",
    "105560": "KB금융",
    "055550": "신한지주",
    "005490": "POSCO홀딩스",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "028260": "삼성물산",
    "012330": "현대모비스",
    "066570": "LG전자",
    "096770": "SK이노베이션",
    "086790": "하나금융지주",
    "323410": "카카오뱅크",
    "247540": "에코프로비엠",
    "086520": "에코프로",
    "263750": "펄어비스",
    "293490": "카카오게임즈",
}


US_UNIVERSE = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "TSLA": "Tesla",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "NFLX": "Netflix",
    "COST": "Costco",
    "LLY": "Eli Lilly",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "MA": "Mastercard",
    "UNH": "UnitedHealth",
    "XOM": "Exxon Mobil",
    "CAT": "Caterpillar",
    "GE": "GE Aerospace",
    "SMCI": "Super Micro Computer",
    "PLTR": "Palantir",
    "CRWD": "CrowdStrike",
    "NOW": "ServiceNow",
    "SHOP": "Shopify",
    "UBER": "Uber",
}


@dataclass(frozen=True)
class RuntimeConfig:
    use_mock_data: bool = False
    allow_ai: bool = True


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_environment() -> None:
    load_dotenv(BASE_DIR / ".env", override=False)
