from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.config import KR_UNIVERSE, US_UNIVERSE


KR_YFINANCE_SUFFIX = {
    "247540": ".KQ",
    "086520": ".KQ",
    "263750": ".KQ",
    "293490": ".KQ",
}


def _normalize_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = [str(col).lower() for col in df.columns]
    rename = {
        "종가": "close",
        "시가": "open",
        "고가": "high",
        "저가": "low",
        "거래량": "volume",
        "close": "close",
        "open": "open",
        "high": "high",
        "low": "low",
        "volume": "volume",
    }
    df = df.rename(columns=rename)
    keep = [col for col in ["open", "high", "low", "close", "volume"] if col in df.columns]
    return df[keep].dropna()


def fetch_kr_history(ticker: str, days: int = 90) -> pd.DataFrame:
    import yfinance as yf

    suffixes = [KR_YFINANCE_SUFFIX.get(ticker, ".KS")]
    suffixes.append(".KQ" if suffixes[0] == ".KS" else ".KS")
    for suffix in suffixes:
        yf_ticker = f"{ticker}{suffix}"
        df = yf.download(yf_ticker, period=f"{max(days, 30)}d", interval="1d", progress=False, auto_adjust=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        normalized = _normalize_frame(df).tail(days)
        if len(normalized) >= 25:
            return normalized

    try:
        from pykrx import stock

        end = date.today()
        start = end - timedelta(days=days * 2)
        df = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), ticker)
        normalized = _normalize_frame(df).tail(days)
        if len(normalized) >= 25:
            return normalized
    except Exception:
        pass
    return pd.DataFrame()


def fetch_us_history(ticker: str, days: int = 90) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(ticker, period=f"{max(days, 30)}d", interval="1d", progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    return _normalize_frame(df).tail(days)


def fetch_market_history(market: str, ticker: str, days: int = 90) -> pd.DataFrame:
    if market == "KR":
        return fetch_kr_history(ticker, days)
    if market == "US":
        return fetch_us_history(ticker, days)
    raise ValueError(f"Unsupported market: {market}")


def mock_history(ticker: str, days: int = 90, market: str = "KR") -> pd.DataFrame:
    seed = abs(hash(f"{market}:{ticker}")) % (2**32)
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="B")
    base = 50_000 if market == "KR" else 180
    returns = rng.normal(loc=0.001, scale=0.025, size=days)
    trend = np.linspace(-0.03, 0.08, days)
    close = base * np.cumprod(1 + returns + trend / days)
    volume = rng.integers(500_000, 8_000_000, size=days)
    return pd.DataFrame(
        {
            "open": close * rng.normal(0.998, 0.008, size=days),
            "high": close * rng.normal(1.012, 0.008, size=days),
            "low": close * rng.normal(0.988, 0.008, size=days),
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


def load_universe(use_mock_data: bool = False, days: int = 90) -> dict[str, dict[str, pd.DataFrame]]:
    result: dict[str, dict[str, pd.DataFrame]] = {"KR": {}, "US": {}}
    for market, universe in [("KR", KR_UNIVERSE), ("US", US_UNIVERSE)]:
        for ticker in universe:
            try:
                frame = mock_history(ticker, days, market) if use_mock_data else fetch_market_history(market, ticker, days)
            except Exception:
                frame = pd.DataFrame()
            if len(frame) >= 25:
                result[market][ticker] = frame
    return result
