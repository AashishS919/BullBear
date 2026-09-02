"""Backtest the trained LSTMs: predicted close vs actual close over the holdout window.
"""
import json
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
from pymongo import ASCENDING, MongoClient
from tensorflow.keras.models import load_model

from config import ARTIFACTS_DIR, HORIZON, MONGO_DB, MONGO_URI, SYMBOLS, TRAIN_SPLIT, WINDOW
from data import load_closes_dated, make_sequences

MODEL_NAME = "lstm-v1"
HORIZONS = sorted({1, HORIZON})  # day counts to score, e.g. (1, 5)


def _rollout_batch(model, X: np.ndarray, steps: int) -> np.ndarray:
    """Roll every sequence in X forward `steps` days. Returns scaled preds, shape (N, steps).

    One batched predict per step (not per row), so scoring 5 horizons over the whole
    holdout costs 5 model calls. Mirrors infer._rollout: the window is rolled in scaled
    space, feeding each prediction back in as the next input.
    """
    window = X.copy()
    out = []
    for _ in range(steps):
        pred = model.predict(window, verbose=0)
        out.append(pred[:, 0])
        window = np.concatenate([window[:, 1:, :], pred.reshape(-1, 1, 1)], axis=1)
    return np.stack(out, axis=1)


def _metrics(actuals: list[float], predicteds: list[float], anchors: list[float]) -> dict:
    """MAE / RMSE / directional accuracy. Direction is scored against `anchors` - the
    last real close before the forecast window - so it means 'did the model call the
    move from the last known price', consistently across horizons."""
    a = np.array(actuals)
    p = np.array(predicteds)
    pa = np.array(anchors)
    mae = float(np.mean(np.abs(p - a))) if len(a) else 0.0
    rmse = float(np.sqrt(np.mean((p - a) ** 2))) if len(a) else 0.0
    dir_acc = float(np.mean(np.sign(p - pa) == np.sign(a - pa))) if len(a) else 0.0
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "directional_accuracy": round(dir_acc, 4),
        "points": len(a),
    }


def backtest_symbol(symbol: str) -> dict | None:
    model_path = ARTIFACTS_DIR / f"{symbol}.keras"
    scaler_path = ARTIFACTS_DIR / f"{symbol}.scaler.pkl"
    if not model_path.exists() or not scaler_path.exists():
        print(f"  {symbol}: no artifacts, skipping")
        return None

    model = load_model(model_path)
    scaler = joblib.load(scaler_path)

    closes, dates = load_closes_dated(symbol)
    if len(closes) <= WINDOW + 10:
        print(f"  {symbol}: not enough data, skipping")
        return None

    scaled = scaler.transform(closes)
    X, _ = make_sequences(scaled, WINDOW)
    # Mirror data.prepare's chronological split: backtest only the unseen validation tail.
    split = int(len(X) * TRAIN_SPLIT)
    X_val = X[split:]

    max_steps = max(HORIZONS)
    rolled = _rollout_batch(model, X_val, max_steps)  # (N, max_steps), scaled

    points_by_horizon, metrics_by_horizon = {}, {}
    for h in HORIZONS:
        # Column h-1 is the h-day-ahead prediction; inverse-scale that column alone.
        pred_close = scaler.inverse_transform(rolled[:, h - 1].reshape(-1, 1)).flatten()

        points, actuals, predicteds, anchors = [], [], [], []
        for k, j in enumerate(range(split, len(X))):
            idx = j + WINDOW + h - 1  # sequence j, rolled h steps, lands on closes[idx]
            if idx >= len(closes):
                break  # the tail sequences run past the end of the series
            actual = float(closes[idx, 0])
            predicted = float(pred_close[k])
            points.append({
                "date": dates[idx],
                "actual": round(actual, 2),
                "predicted": round(predicted, 2),
            })
            actuals.append(actual)
            predicteds.append(predicted)
            anchors.append(float(closes[j + WINDOW - 1, 0]))  # last real close pre-forecast

        points_by_horizon[str(h)] = points
        metrics_by_horizon[str(h)] = _metrics(actuals, predicteds, anchors)

    return {
        "symbol": symbol,
        "model": MODEL_NAME,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        # Day-1 stays at the top level: unchanged shape for existing readers.
        "metrics": metrics_by_horizon["1"],
        "points": points_by_horizon["1"],
        "metrics_by_horizon": metrics_by_horizon,
        "points_by_horizon": points_by_horizon,
    }


def main(argv: list[str]) -> None:
    symbols = [s.upper() for s in argv] or SYMBOLS
    results = [r for r in (backtest_symbol(s) for s in symbols) if r]

    # Publish to MongoDB.
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
    col = client[MONGO_DB]["prediction_series"]
    col.create_index([("symbol", ASCENDING)], unique=True)
    for r in results:
        col.replace_one({"symbol": r["symbol"]}, r, upsert=True)
    client.close()

    # Publish JSON fallback.
    (ARTIFACTS_DIR / "prediction_series.json").write_text(
        json.dumps({"series": results}, indent=2)
    )

    for r in results:
        for h in HORIZONS:
            m = r["metrics_by_horizon"][str(h)]
            print(f"  {r['symbol']} h={h}d: {m['points']} pts  mae={m['mae']} "
                  f"rmse={m['rmse']} dir_acc={m['directional_accuracy']}")
    print(f"\nPublished {len(results)} backtest series "
          f"(horizons {HORIZONS}) to Mongo + prediction_series.json")


if __name__ == "__main__":
    main(sys.argv[1:])
