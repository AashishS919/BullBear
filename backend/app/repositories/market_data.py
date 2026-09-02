"""Deterministic 5-year daily OHLCV generator.
"""
from datetime import date, timedelta
from functools import lru_cache

TICKERS = [
    {"symbol": "NABIL", "name": "Nabil Bank Limited", "sector": "Commercial Bank", "base": 520},
    {"symbol": "NICA", "name": "NIC Asia Bank Limited", "sector": "Commercial Bank", "base": 760},
    {"symbol": "NTC", "name": "Nepal Telecom", "sector": "Telecommunication", "base": 980},
    {"symbol": "NRIC", "name": "Nepal Reinsurance Company", "sector": "Investment", "base": 740},
    {"symbol": "UPPER", "name": "Upper Tamakoshi Hydropower", "sector": "Hydropower", "base": 480},
    {"symbol": "CHCL", "name": "Chilime Hydropower", "sector": "Hydropower", "base": 540},
    {"symbol": "VLBS", "name": "Vijaya Laghubitta Bittiya Sanstha Limited", "sector": "Microfinance", "base": 750},
    {"symbol": "SBL", "name": "Siddhartha Bank Limited", "sector": "Commercial Bank", "base": 340},
    {"symbol": "AHL", "name": "Asian Hydropower Limited", "sector": "Hydropower", "base": 250},
    {"symbol": "ADBL", "name": "Agricultural Development Bank Limited", "sector": "Commercial Bank", "base": 300},
]

_TICKER_BY_SYMBOL = {t["symbol"]: t for t in TICKERS}

START = date(2021, 1, 1)
END = date.today()  # series runs to the current date; advances as the calendar does

_UINT32 = 0xFFFFFFFF


def _mulberry32(seed: int):
    state = seed & _UINT32

    def rand() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & _UINT32
        t = state
        t = (t ^ (t >> 15)) * (t | 1) & _UINT32
        t ^= (t + ((t ^ (t >> 7)) * (t | 61) & _UINT32)) & _UINT32
        t &= _UINT32
        return ((t ^ (t >> 14)) & _UINT32) / 4294967296.0

    return rand


def _seed_from_string(s: str) -> int:
    h = 1779033703 ^ len(s)
    for ch in s:
        h = (h ^ ord(ch)) & _UINT32
        h = (h * 3432918353) & _UINT32
        h = ((h << 13) | (h >> 19)) & _UINT32
    h ^= h >> 16
    return h & _UINT32


def _trading_days() -> list[str]:
    days = []
    d = START
    while d <= END:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def _round2(n: float) -> float:
    return round(n * 100) / 100


@lru_cache(maxsize=None)
def get_series(symbol: str) -> tuple[dict, ...]:
    ticker = _TICKER_BY_SYMBOL.get(symbol)
    if ticker is None:
        return tuple()

    rand = _mulberry32(_seed_from_string(symbol))
    days = _trading_days()
    out = []
    price = float(ticker["base"])
    drift = (rand() - 0.45) * 0.0006

    for d in days:
        shock = (rand() - 0.5) * 0.04
        change = drift + shock
        open_ = price
        close = max(10.0, open_ * (1 + change))
        high = max(open_, close) * (1 + rand() * 0.012)
        low = min(open_, close) * (1 - rand() * 0.012)
        volume = int(40000 + rand() * 260000)
        out.append({
            "date": d,
            "open": _round2(open_),
            "high": _round2(high),
            "low": _round2(low),
            "close": _round2(close),
            "volume": volume,
        })
        price = close
    return tuple(out)


def list_tickers() -> list[dict]:
    return [{"symbol": t["symbol"], "name": t["name"], "sector": t["sector"]} for t in TICKERS]


def get_quote(symbol: str) -> dict | None:
    s = get_series(symbol)
    if len(s) < 2:
        return None
    last, prev = s[-1], s[-2]
    change = _round2(last["close"] - prev["close"])
    change_pct = _round2((change / prev["close"]) * 100) if prev["close"] else 0.0
    meta = _TICKER_BY_SYMBOL[symbol]
    return {
        "symbol": symbol,
        "name": meta["name"],
        "sector": meta["sector"],
        "close": last["close"],
        "prev_close": prev["close"],
        "change": change,
        "change_pct": change_pct,
        "volume": last["volume"],
    }


def get_market_quotes() -> list[dict]:
    return [q for q in (get_quote(t["symbol"]) for t in TICKERS) if q]


_RANGE_DAYS = {"1M": 22, "6M": 132, "1Y": 252}


def filter_by_range(series: tuple[dict, ...], range_: str) -> list[dict]:
    if not series or range_ in ("MAX", "5Y"):
        return list(series)
    n = _RANGE_DAYS.get(range_)
    return list(series[-n:]) if n else list(series)
