"""5-year market data pipeline utility (Phase 3).
"""
import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

# Make the app package importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import ASCENDING, MongoClient, UpdateOne  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.repositories import market_data  # noqa: E402

SOURCES = ("mock", "nepsealpha", "sharesansar")
SHARESANSAR_DIR = Path(__file__).resolve().parents[1] / "data" / "sharesansar"


def _business_days(start: str, end: str) -> list[str]:
    out = []
    d = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while d <= last:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def clean_and_align(raw: list[dict]) -> list[dict]:
    """Reindex to a continuous business-day calendar and forward-fill holiday gaps."""
    if not raw:
        return []
    by_date = {r["date"]: r for r in raw}
    calendar = _business_days(raw[0]["date"], raw[-1]["date"])

    cleaned = []
    prev = None
    for d in calendar:
        row = by_date.get(d)
        if row is None and prev is not None:
            # Market holiday on a weekday: carry the previous close forward.
            row = {"date": d, "open": prev["close"], "high": prev["close"],
                   "low": prev["close"], "close": prev["close"], "volume": 0,
                   "imputed": True}
        elif row is not None:
            row = {**row, "imputed": False}
        if row is not None:
            cleaned.append(row)
            prev = row
    return cleaned


def clean_real(raw: list[dict]) -> list[dict]:
    """Clean a real feed: keep the actual trading days, just dedupe by date and sort.
    """
    by_date = {r["date"]: {**r, "imputed": False} for r in raw}
    return [by_date[d] for d in sorted(by_date)]


def _load_sharesansar_csv(symbol: str, data_dir: Path = SHARESANSAR_DIR) -> list[dict]:
    """Read one ticker's CSV from scripts/fetch_sharesansar.py into feed row shape.
    """
    path = data_dir / f"{symbol}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found - run scripts/fetch_sharesansar.py {symbol} first"
        )
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append({
                "date": r["date"],
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(float(r["volume"] or 0)),
            })
    return rows


def run(symbols: list[str] | None = None, source: str | None = None) -> dict:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    db = client[settings.mongo_db]
    col = db["market_candles"]
    col.create_index([("symbol", ASCENDING), ("date", ASCENDING)], unique=True)

    tickers = symbols or [t["symbol"] for t in market_data.TICKERS]
    source = source or settings.market_source
    if source == "nepsealpha":
        from app.services import nepsealpha  # lazy: only needed for real ingestion
        if not nepsealpha.is_configured():
            print("  BB_PARSEBOT_API_KEY not set; falling back to mock data.")
            source = "mock"
    print(f"  market_source={source}")
    summary = {}
    for symbol in tickers:
        used_mock = source == "mock"
        if source == "nepsealpha":
            try:
                raw = nepsealpha.fetch_history(symbol)
            except nepsealpha.NepseAlphaError as exc:
                print(f"  {symbol}: nepsealpha unavailable ({exc}); using mock")
                raw = list(market_data.get_series(symbol))
                used_mock = True
        elif source == "sharesansar":
            try:
                raw = _load_sharesansar_csv(symbol)
            except (FileNotFoundError, ValueError, KeyError) as exc:
                # Skip rather than silently substituting mock data into a real dataset.
                print(f"  {symbol}: SKIPPED - {exc}")
                continue
        else:
            raw = list(market_data.get_series(symbol))
        # Mock data is a synthetic Mon-Fri grid and needs the calendar fill; a real feed
        # already carries its true trading days (and survived the April 2026 week change).
        cleaned = clean_and_align(raw) if used_mock else clean_real(raw)
        ops = [
            UpdateOne(
                {"symbol": symbol, "date": r["date"]},
                {"$set": {"symbol": symbol, **r}},
                upsert=True,
            )
            for r in cleaned
        ]
        if ops:
            col.bulk_write(ops, ordered=False)
        imputed = sum(1 for r in cleaned if r.get("imputed"))
        summary[symbol] = {"rows": len(cleaned), "imputed": imputed,
                           "last_date": cleaned[-1]["date"] if cleaned else None}
        span = f"{cleaned[0]['date']} -> {cleaned[-1]['date']}" if cleaned else "empty"
        print(f"  {symbol}: {len(cleaned)} rows ({imputed} imputed) upserted  {span}")

    client.close()
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ingest daily OHLCV into market_candles")
    ap.add_argument("symbols", nargs="*", help="tickers (default: all tracked)")
    ap.add_argument("--source", choices=SOURCES,
                    help="override BB_MARKET_SOURCE for this run")
    args = ap.parse_args()
    print("Running 5-year data pipeline -> market_candles ...")
    run(args.symbols or None, source=args.source)
    print("Done.")
