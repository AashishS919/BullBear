"""Buy / sell / hold recommendations for the positions a user actually holds.
"""
HORIZON_DAYS = 5           # forecast day the call is based on
BUY_THRESHOLD = 2.0        # expected % move needed to call a BUY
SELL_THRESHOLD = -2.0      # ... and a SELL; between the two is treated as noise
TAKE_PROFIT_PNL = 10.0     # position already up this much -> frame a SELL as taking profit
CUT_LOSS_PNL = -10.0       # ... down this much -> frame it as cutting the loss
MIN_DIRECTIONAL_ACCURACY = 0.5  # at or below this, the model is not beating a coin flip

BUY = "BUY"
SELL = "SELL"
HOLD = "HOLD"


def _result(action: str, reason: str, *, reliable: bool = True, **extra) -> dict:
    return {
        "action": action,
        "reason": reason,
        "reliable": reliable,
        "horizon_days": HORIZON_DAYS,
        "expected_change_pct": None,
        "target_close": None,
        "confidence": None,
        "directional_accuracy": None,
        **extra,
    }


def decide(*, expected_change_pct: float, pnl_pct: float,
           directional_accuracy: float | None) -> dict:
    """Pure rule set: expected move + position P/L + model skill -> a call and a reason.

    Kept free of repositories so the thresholds can be tested directly.
    """
    move = f"{expected_change_pct:+.1f}% over {HORIZON_DAYS} trading days"

    # 1. Model skill gates everything. A strong signal from a ticker the model cannot call
    #    is still not a signal.
    if directional_accuracy is not None and directional_accuracy <= MIN_DIRECTIONAL_ACCURACY:
        return _result(
            HOLD,
            f"No directional call: the model backtests at "
            f"{directional_accuracy * 100:.0f}% on this ticker, at or below a coin flip. "
            f"It forecasts {move}, but that is not dependable enough to act on.",
            reliable=False,
        )

    # 2. Forecast decides the direction.
    if expected_change_pct >= BUY_THRESHOLD:
        return _result(BUY, f"Model forecasts {move}.")

    if expected_change_pct <= SELL_THRESHOLD:
        if pnl_pct >= TAKE_PROFIT_PNL:
            reason = (f"Model forecasts {move} while you are up {pnl_pct:+.1f}% "
                      f"- consider taking profit.")
        elif pnl_pct <= CUT_LOSS_PNL:
            reason = (f"Model forecasts {move} and you are already down {pnl_pct:+.1f}% "
                      f"- consider cutting the loss.")
        else:
            reason = f"Model forecasts {move}."
        return _result(SELL, reason)

    # 3. Inside the noise band.
    return _result(
        HOLD,
        f"Model forecasts {move}, inside the "
        f"{SELL_THRESHOLD:+.0f}% to {BUY_THRESHOLD:+.0f}% noise band.",
    )


def _directional_accuracy(predictions, symbol: str, horizon_days: int) -> float | None:
    """Backtested directional accuracy for this symbol at this horizon, if scored."""
    bt = predictions.get_backtest(symbol)
    if not bt:
        return None
    by_horizon = bt.get("metrics_by_horizon") or {}
    metrics = by_horizon.get(str(horizon_days))
    if metrics is None and horizon_days == 1:
        metrics = bt.get("metrics")  # artifacts predating the multi-horizon backtest
    if not metrics:
        return None
    value = metrics.get("directional_accuracy")
    return float(value) if value is not None else None


def _forecast_step(predictions, symbol: str, horizon_days: int) -> dict | None:
    pred = predictions.get(symbol)
    if not pred:
        return None
    for entry in pred.get("path") or []:
        if int(entry.get("step", 0)) == horizon_days:
            return entry
    return None


def for_position(*, position: dict, predictions, horizon_days: int = HORIZON_DAYS) -> dict:
    """Recommendation for one portfolio position (as built by compute_portfolio)."""
    symbol = position["symbol"]
    ltp = position.get("ltp")

    step = _forecast_step(predictions, symbol, horizon_days)
    if step is None or not ltp:
        return _result(
            HOLD,
            f"No {horizon_days}-day model forecast available for {symbol} "
            f"- run ml/infer.py to publish one.",
            reliable=False,
        )

    target_close = float(step["predicted_close"])
    expected_change_pct = (target_close - ltp) / ltp * 100.0
    accuracy = _directional_accuracy(predictions, symbol, horizon_days)

    result = decide(
        expected_change_pct=expected_change_pct,
        pnl_pct=float(position.get("pnl_pct") or 0.0),
        directional_accuracy=accuracy,
    )
    result.update({
        "expected_change_pct": round(expected_change_pct, 2),
        "target_close": round(target_close, 2),
        "confidence": float(step["confidence"]) if step.get("confidence") is not None else None,
        "directional_accuracy": accuracy,
    })
    return result
