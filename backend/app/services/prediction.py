"""Trend-prediction service.
"""
STUB_MODEL = "stub-deterministic-v0"


def _step_for(pred: dict, horizon_days: int) -> dict | None:
    """The rollout entry for the requested day, or None if the path cannot serve it."""
    path = pred.get("path") or []
    for entry in path:
        if int(entry.get("step", 0)) == horizon_days:
            return entry
    return None


def predict(*, predictions, market, symbol: str, horizon_days: int = 1) -> dict | None:
    # 1. Prefer the real LSTM prediction.
    pred = predictions.get(symbol)
    if pred and "direction" in pred and "confidence" in pred:
        path = pred.get("path") or []
        step = _step_for(pred, horizon_days)
        if step is not None:
            direction = step["direction"]
            confidence = float(step["confidence"])
            predicted_close = step.get("predicted_close")
            target_date = step.get("target_date")
            served_horizon = horizon_days
        else:
            # Pre-multi-horizon record (or a horizon this run did not produce): fall back
            # to the stored single-step signal and report the horizon it actually covers.
            direction = pred["direction"]
            confidence = float(pred["confidence"])
            predicted_close = pred.get("predicted_close")
            target_date = pred.get("target_date")
            served_horizon = int(pred.get("horizon_days", 1))
        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "horizon_days": served_horizon,
            "model": pred.get("model", "lstm-v1"),
            "last_close": pred.get("last_close"),
            "predicted_close": predicted_close,
            "target_date": target_date,
            "path": path,
        }

    # 2. Deterministic fallback from recent momentum.
    series = market.get_series(symbol, "MAX")
    if len(series) < 30:
        return None

    window = series[-20:]
    first_close = window[0]["close"]
    last_close = window[-1]["close"]
    momentum = (last_close - first_close) / first_close if first_close else 0.0
    direction = "up" if momentum >= 0 else "down"
    base = 0.55 + min(abs(momentum) * 4.0, 0.3)
    offset = (ord(symbol[0]) % 7) / 100.0
    confidence = round(min(0.92, base + offset), 4)

    return {
        "symbol": symbol,
        "direction": direction,
        "confidence": confidence,
        "horizon_days": horizon_days,
        "model": STUB_MODEL,
        "last_close": round(last_close, 2),
        "predicted_close": None,
        "target_date": None,
        "path": [],
    }
