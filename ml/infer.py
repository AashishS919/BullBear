"""Run inference with the trained LSTMs and publish trend signals.
"""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import joblib
import numpy as np
from pymongo import ASCENDING, MongoClient
from pymongo.errors import OperationFailure
from tensorflow.keras.models import load_model

from config import ARTIFACTS_DIR, HORIZON, MONGO_DB, MONGO_URI, SYMBOLS, WINDOW
from data import load_closes_dated

MODEL_NAME = "lstm-v1"

# NEPSE currently trades Mon-Fri. It has not always: the exchange moved off a Sun-Thu week
# in April 2026 (last Sunday session 2026-04-05). Rather than hardcode the current rule and
# silently emit dates the market is shut on if it changes again, the forward calendar is
# read off the weekdays recently observed in the candle history.
DEFAULT_TRADING_WEEKDAYS = frozenset({0, 1, 2, 3, 4})  # Mon-Fri
CALENDAR_SAMPLE = 60  # sessions to infer the trading week from (~12 weeks)


def observed_trading_weekdays(dates, sample: int = CALENDAR_SAMPLE) -> frozenset:
    """Weekday numbers the market actually traded on across the last `sample` sessions.

    A weekday must appear in at least ~10% of the sample to count, so a one-off special
    session does not widen the week, and a weekday being phased out fades away on its own.
    Falls back to Mon-Fri when there is too little history to infer anything.
    """
    recent = [str(d)[:10] for d in dates[-sample:]]
    if len(recent) < 10:
        return DEFAULT_TRADING_WEEKDAYS
    counts = Counter(datetime.strptime(d, "%Y-%m-%d").date().weekday() for d in recent)
    threshold = max(2, len(recent) // 10)
    weekdays = frozenset(wd for wd, n in counts.items() if n >= threshold)
    return weekdays or DEFAULT_TRADING_WEEKDAYS


def _trading_days_after(date_str: str, n: int, weekdays=DEFAULT_TRADING_WEEKDAYS) -> str:
    """The nth trading date after date_str (YYYY-MM-DD) on the given weekly calendar."""
    d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    for _ in range(n):
        d += timedelta(days=1)
        while d.weekday() not in weekdays:
            d += timedelta(days=1)
    return d.isoformat()


def _next_business_day(date_str: str) -> str:
    return _trading_days_after(date_str, 1)


def _signal(last_close: float, predicted_close: float) -> dict:
    """Direction + confidence for one forecast step, measured against the last actual."""
    pct_change = (predicted_close - last_close) / last_close if last_close else 0.0
    return {
        "direction": "up" if pct_change >= 0 else "down",
        # Map move magnitude to a confidence in [0.5, 0.95].
        "confidence": round(min(0.95, 0.5 + abs(pct_change) * 9.0), 4),
    }


def _rollout(model, scaler, closes: np.ndarray, steps: int) -> list[float]:
    """Iteratively forecast `steps` days ahead, feeding each prediction back in.

    The window is rolled in *scaled* space and inverse-transformed once at the end, so
    no rounding drift accumulates across steps. Errors do compound - a day-5 value is
    built on four predicted inputs - which is why backtest.py measures each horizon.
    """
    window = scaler.transform(closes)[-WINDOW:].reshape(1, WINDOW, 1)
    scaled_path = []
    for _ in range(steps):
        pred_scaled = model.predict(window, verbose=0)
        scaled_path.append(float(pred_scaled[0, 0]))
        window = np.concatenate([window[:, 1:, :], pred_scaled.reshape(1, 1, 1)], axis=1)
    inverted = scaler.inverse_transform(np.array(scaled_path, dtype="float32").reshape(-1, 1))
    return [float(v) for v in inverted.flatten()]


def predict_symbol(symbol: str) -> dict | None:
    model_path = ARTIFACTS_DIR / f"{symbol}.keras"
    scaler_path = ARTIFACTS_DIR / f"{symbol}.scaler.pkl"
    if not model_path.exists() or not scaler_path.exists():
        print(f"  {symbol}: no artifacts, skipping")
        return None

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)

    closes, dates = load_closes_dated(symbol)
    last_close = float(closes[-1, 0])
    predicted = _rollout(model, scaler, closes, HORIZON)
    weekdays = observed_trading_weekdays(dates)

    path = [{
        "step": step,
        "target_date": _trading_days_after(dates[-1], step, weekdays),
        "predicted_close": round(close, 2),
        **_signal(last_close, close),
    } for step, close in enumerate(predicted, start=1)]

    head = path[0]
    return {
        "symbol": symbol,
        # Top-level fields stay the step-1 signal: unchanged contract for /overview.
        "direction": head["direction"],
        "confidence": head["confidence"],
        "horizon_days": 1,
        "model": MODEL_NAME,
        "last_close": round(last_close, 2),
        "predicted_close": head["predicted_close"],
        "target_date": head["target_date"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "path": path,
    }


def append_forecast_log(results: list[dict], client: MongoClient) -> None:
    """Append every forecast step to the forecast_log (Mongo + JSON).

    Re-running infer.py on later days accumulates a forward-tracking record that the
    API reconciles against the real close once it lands in market_candles. The key is
    (symbol, target_date, step) - `step` is load-bearing: tomorrow's step-1 forecast
    shares a target_date with today's step-2 forecast, and keying on the date alone
    would let one silently overwrite the other and mix horizons in the same series.
    """
    records = [{
        "symbol": r["symbol"],
        "target_date": p["target_date"],
        "step": p["step"],
        "predicted_close": p["predicted_close"],
        "last_close": r["last_close"],
        "generated_at": r["generated_at"],
    } for r in results for p in r["path"]]

    col = client[MONGO_DB]["forecast_log"]
    # The pre-multi-horizon unique index on (symbol, target_date) would reject steps 2..N.
    try:
        col.drop_index("symbol_1_target_date_1")
    except OperationFailure:
        pass  # already dropped, or a fresh database that never had it
    col.create_index(
        [("symbol", ASCENDING), ("target_date", ASCENDING), ("step", ASCENDING)],
        unique=True,
    )
    for rec in records:
        col.replace_one(
            {"symbol": rec["symbol"], "target_date": rec["target_date"], "step": rec["step"]},
            rec, upsert=True,
        )

    # JSON fallback: merge into the existing log keyed by (symbol, target_date, step).
    path = ARTIFACTS_DIR / "forecast_log.json"
    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text()).get("forecasts", [])
        except (ValueError, OSError):
            existing = []
    # Entries written before this change carry no step; they were all single-step.
    merged = {(e["symbol"], e["target_date"], e.get("step", 1)): e for e in existing}
    for rec in records:
        merged[(rec["symbol"], rec["target_date"], rec["step"])] = rec
    ordered = sorted(merged.values(),
                     key=lambda e: (e["symbol"], e["target_date"], e.get("step", 1)))
    path.write_text(json.dumps({"forecasts": ordered}, indent=2))


def main(argv: list[str]) -> None:
    symbols = [s.upper() for s in argv] or SYMBOLS
    results = [r for r in (predict_symbol(s) for s in symbols) if r]

    # Publish to MongoDB.
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
    col = client[MONGO_DB]["predictions"]
    col.create_index([("symbol", ASCENDING)], unique=True)
    for r in results:
        col.replace_one({"symbol": r["symbol"]}, r, upsert=True)
    append_forecast_log(results, client)
    client.close()

    # Publish JSON fallback.
    (ARTIFACTS_DIR / "predictions.json").write_text(
        json.dumps({"predictions": results}, indent=2)
    )

    for r in results:
        steps = "  ".join(
            f"d{p['step']}={p['predicted_close']}({p['direction'][0]})" for p in r["path"]
        )
        print(f"  {r['symbol']}: last={r['last_close']}  {steps}")
    print(f"\nPublished {len(results)} predictions "
          f"({HORIZON} steps each) to Mongo + predictions.json")


if __name__ == "__main__":
    main(sys.argv[1:])
