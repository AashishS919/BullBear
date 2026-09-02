"""parse.bot NepseAlpha API client (Phase 3 real-data source).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import httpx

from ..config import get_settings

_TIMEOUT = httpx.Timeout(30.0)


class NepseAlphaError(RuntimeError):
    """Raised when the parse.bot API is unusable (missing key, HTTP error, bad shape)."""


def is_configured() -> bool:
    """True when an API key is present, so callers can fall back before calling out."""
    return bool(get_settings().parsebot_api_key)


def _endpoint_url(endpoint: str) -> str:
    s = get_settings()
    if not s.parsebot_api_key:
        raise NepseAlphaError(
            "BB_PARSEBOT_API_KEY is not set; cannot call the NepseAlpha (parse.bot) API."
        )
    base = s.parsebot_base_url.rstrip("/")
    return f"{base}/scraper/{s.parsebot_scraper_id}/{endpoint}"


def _headers() -> dict:
    return {
        "X-API-Key": get_settings().parsebot_api_key,
        "Content-Type": "application/json",
    }


def _call(endpoint: str, *, method: str = "GET", params: dict | None = None,
          body: dict | None = None) -> dict | list:
    url = _endpoint_url(endpoint)
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            if method == "POST":
                resp = client.post(url, headers=_headers(), json=body or {})
            else:
                resp = client.get(url, headers=_headers(), params=params or {})
    except httpx.HTTPError as exc:  # network/timeout
        raise NepseAlphaError(f"{endpoint}: request failed: {exc}") from exc

    if resp.status_code == 429:
        raise NepseAlphaError(f"{endpoint}: rate limited (429) — slow down or upgrade tier.")
    if resp.status_code >= 400:
        raise NepseAlphaError(
            f"{endpoint}: HTTP {resp.status_code}: {resp.text[:300]}"
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise NepseAlphaError(f"{endpoint}: response was not JSON: {resp.text[:200]}") from exc


def _unwrap(payload):
    """Peel common wrapper keys so callers get to the meaningful body."""
    seen = 0
    while isinstance(payload, dict) and seen < 4:
        for key in ("data", "result", "props", "response"):
            if key in payload and isinstance(payload[key], (dict, list)):
                payload = payload[key]
                break
        else:
            break
        seen += 1
    return payload


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- history

def fetch_history(symbol: str, resolution: str = "1D") -> list[dict]:
    """Return full daily OHLCV for `symbol` as canonical rows sorted ascending:

        {"date": "YYYY-MM-DD", "open", "high", "low", "close", "volume"}

    Uses get_tradingview_history (TradingView UDF-style parallel arrays o/h/l/c/v/t).
    """
    payload = _unwrap(_call("get_tradingview_history",
                            params={"symbol": symbol, "resolution": resolution}))
    if not isinstance(payload, dict):
        raise NepseAlphaError(f"get_tradingview_history({symbol}): unexpected shape {type(payload)}")

    status = str(payload.get("s") or payload.get("status") or "").lower()
    if status and status not in ("ok", "success"):
        raise NepseAlphaError(f"get_tradingview_history({symbol}): status={status!r}")

    times = payload.get("t") or payload.get("time") or []
    opens = payload.get("o") or payload.get("open") or []
    highs = payload.get("h") or payload.get("high") or []
    lows = payload.get("l") or payload.get("low") or []
    closes = payload.get("c") or payload.get("close") or []
    vols = payload.get("v") or payload.get("volume") or []
    if not times or not closes:
        raise NepseAlphaError(f"get_tradingview_history({symbol}): empty history")

    rows: list[dict] = []
    for i, ts in enumerate(times):
        d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date().isoformat()
        close = _num(closes[i]) if i < len(closes) else 0.0
        rows.append({
            "date": d,
            "open": round(_num(opens[i]) if i < len(opens) else close, 2),
            "high": round(_num(highs[i]) if i < len(highs) else close, 2),
            "low": round(_num(lows[i]) if i < len(lows) else close, 2),
            "close": round(close, 2),
            "volume": int(_num(vols[i]) if i < len(vols) else 0),
        })
    rows.sort(key=lambda r: r["date"])
    return rows


# ----------------------------------------------------------------------- live market

_SYMBOL_KEYS = ("symbol", "ticker", "scrip", "stockSymbol", "Symbol")
_PRICE_KEYS = ("ltp", "lastPrice", "last_price", "close", "price", "lastTradedPrice")
_CHANGE_KEYS = ("change", "pointChange", "point_change", "priceChange")
_PCT_KEYS = ("percentChange", "percent_change", "changePercent", "change_percent", "pChange")


def _iter_stock_dicts(payload):
    """Yield per-stock dicts from an arbitrarily-nested get_live_market payload."""
    payload = _unwrap(payload)
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if isinstance(payload, dict):
        # Prefer an obvious list-of-stocks under a likely key.
        for key in ("stocks", "liveMarket", "live_market", "marketWatch", "quotes", "prices"):
            val = payload.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        yield item
                return
        # Fallback: any nested list of dicts that look like stock rows.
        for val in payload.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                if any(k in val[0] for k in _SYMBOL_KEYS):
                    for item in val:
                        if isinstance(item, dict):
                            yield item
                    return


def _pick(d: dict, keys) -> object | None:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _live_price_rows(payload) -> list[dict]:
    """Locate the per-stock live board within a get_live_market payload.
    """
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        sl = data.get("stock_live")
        if isinstance(sl, dict) and isinstance(sl.get("prices"), list):
            return [r for r in sl["prices"] if isinstance(r, dict)]
    return list(_iter_stock_dicts(payload))


def fetch_live_market(symbols: set[str] | None = None) -> list[dict]:
    """Return live ticks `{"symbol","price","change","change_pct"}` for the board.
    """
    payload = _call("get_live_market")
    out: list[dict] = []
    for row in _live_price_rows(payload):
        sym = _pick(row, _SYMBOL_KEYS)
        price = _pick(row, _PRICE_KEYS)
        if sym is None or price is None:
            continue
        sym = str(sym).upper()
        if symbols is not None and sym not in symbols:
            continue
        price_f = _num(price)
        pct = _pick(row, _PCT_KEYS)
        pct_f = _num(pct) if pct is not None else 0.0
        change = _pick(row, _CHANGE_KEYS)
        if change is not None:
            change_f = _num(change)
        else:
            # Derive absolute change from close + percent change vs previous close.
            denom = 1 + pct_f / 100
            if abs(denom) > 1e-9:
                change_f = price_f - price_f / denom
            else:
                # -100%: value wiped out; prev price isn't recoverable from (price, pct)
                # alone, so report the full drop as best effort.
                change_f = -price_f
        out.append({
            "symbol": sym,
            "price": round(price_f, 2),
            "change": round(change_f, 2),
            "change_pct": round(pct_f, 2),
        })
    if not out:
        raise NepseAlphaError("get_live_market: no stock rows parsed from response")
    return out


def live_candles(symbols: set[str] | None = None, on_date: str | None = None) -> list[dict]:
    """Build today's candle rows from the live board for EOD upsert.
    """
    d = on_date or date.today().isoformat()
    payload = _call("get_live_market")
    rows = []
    for row in _live_price_rows(payload):
        sym = _pick(row, _SYMBOL_KEYS)
        close = _pick(row, _PRICE_KEYS)
        if sym is None or close is None:
            continue
        sym = str(sym).upper()
        if symbols is not None and sym not in symbols:
            continue
        c = _num(close)
        if c <= 0:
            continue  # no valid price today (untraded/suspended) -> no candle
        # Treat a missing OR non-positive O/H/L as the close (a flat candle) rather than
        # emitting a zero, which would corrupt the series and break chart scaling.
        def _pos(v: float) -> float:
            return v if v > 0 else c
        o = _pos(_num(_pick(row, ("open",))))
        hi = _pos(_num(_pick(row, ("high",))))
        lo = _pos(_num(_pick(row, ("low",))))
        vol = int(_num(_pick(row, ("volume",))))
        rows.append({
            "symbol": sym, "date": d,
            "open": round(o, 2), "high": round(hi, 2),
            "low": round(lo, 2), "close": round(c, 2), "volume": vol,
        })
    return rows
