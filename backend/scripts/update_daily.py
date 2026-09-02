"""Daily end-of-day market_candles updater (parse.bot NepseAlpha source).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import ASCENDING, MongoClient, UpdateOne  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.repositories import market_data  # noqa: E402
from app.services import nepsealpha  # noqa: E402


def run() -> dict:
    settings = get_settings()
    if settings.market_source != "nepsealpha":
        print(f"market_source={settings.market_source!r}; nothing to update. "
              "Set BB_MARKET_SOURCE=nepsealpha to pull live data.")
        return {}
    if not nepsealpha.is_configured():
        print("BB_PARSEBOT_API_KEY not set; skipping daily update.")
        return {}

    symbols = {t["symbol"] for t in market_data.TICKERS}
    today = date.today().isoformat()
    try:
        rows = nepsealpha.live_candles(symbols, on_date=today)  # 1 credit for the board
    except nepsealpha.NepseAlphaError as exc:
        print(f"Daily update skipped; nepsealpha unavailable: {exc}")
        return {}
    if not rows:
        print("No live rows returned; market may be closed or symbols unmatched.")
        return {}

    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    col = client[settings.mongo_db]["market_candles"]
    col.create_index([("symbol", ASCENDING), ("date", ASCENDING)], unique=True)

    ops = [
        UpdateOne(
            {"symbol": r["symbol"], "date": r["date"]},
            {"$set": {**r, "imputed": False}},
            upsert=True,
        )
        for r in rows
    ]
    result = col.bulk_write(ops, ordered=False)
    client.close()

    summary = {"date": today, "symbols": len(rows),
               "upserted": result.upserted_count, "modified": result.modified_count}
    print(f"Updated {len(rows)} candles for {today}: "
          f"{result.upserted_count} new, {result.modified_count} modified.")
    return summary


if __name__ == "__main__":
    run()
