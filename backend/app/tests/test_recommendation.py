"""Rule-level tests for the buy/sell/hold recommendation.
"""
from app.services import recommendation as rec

GOOD_SKILL = 0.62  # comfortably above a coin flip


def test_strong_upside_is_a_buy():
    r = rec.decide(expected_change_pct=5.0, pnl_pct=0.0, directional_accuracy=GOOD_SKILL)
    assert r["action"] == "BUY"
    assert r["reliable"] is True


def test_downside_on_a_winning_position_suggests_taking_profit():
    r = rec.decide(expected_change_pct=-5.0, pnl_pct=15.0, directional_accuracy=GOOD_SKILL)
    assert r["action"] == "SELL"
    assert "taking profit" in r["reason"]


def test_downside_on_a_losing_position_suggests_cutting_the_loss():
    r = rec.decide(expected_change_pct=-5.0, pnl_pct=-15.0, directional_accuracy=GOOD_SKILL)
    assert r["action"] == "SELL"
    assert "cutting the loss" in r["reason"]


def test_downside_on_a_flat_position_sells_without_pnl_framing():
    r = rec.decide(expected_change_pct=-5.0, pnl_pct=2.0, directional_accuracy=GOOD_SKILL)
    assert r["action"] == "SELL"
    assert "taking profit" not in r["reason"]
    assert "cutting the loss" not in r["reason"]


def test_small_move_is_noise_and_holds():
    r = rec.decide(expected_change_pct=0.5, pnl_pct=0.0, directional_accuracy=GOOD_SKILL)
    assert r["action"] == "HOLD"
    assert r["reliable"] is True  # a genuine "sit tight", not a suppressed call


def test_unreliable_ticker_is_gated_even_with_a_strong_signal():
    # The gate must beat the signal: an 8% forecast means nothing from a model that
    # calls direction correctly only 34% of the time on this ticker.
    r = rec.decide(expected_change_pct=-8.0, pnl_pct=20.0, directional_accuracy=0.34)
    assert r["action"] == "HOLD"
    assert r["reliable"] is False
    assert "34%" in r["reason"]


def test_coin_flip_accuracy_is_gated_at_the_boundary():
    r = rec.decide(expected_change_pct=6.0, pnl_pct=0.0, directional_accuracy=0.5)
    assert r["action"] == "HOLD"
    assert r["reliable"] is False


def test_unscored_ticker_still_gets_a_call():
    # No backtest for this symbol is not evidence of a bad model, so the forecast stands.
    r = rec.decide(expected_change_pct=6.0, pnl_pct=0.0, directional_accuracy=None)
    assert r["action"] == "BUY"


class _StubPredictions:
    """Minimal stand-in for the predictions repository."""

    def __init__(self, pred=None, backtest=None):
        self._pred, self._backtest = pred, backtest

    def get(self, symbol):
        return self._pred

    def get_backtest(self, symbol):
        return self._backtest


def test_for_position_computes_expected_move_from_the_step_5_forecast():
    predictions = _StubPredictions(
        pred={"symbol": "NABIL", "path": [
            {"step": 1, "predicted_close": 505.0, "confidence": 0.55},
            {"step": 5, "predicted_close": 540.0, "confidence": 0.61},
        ]},
        backtest={"metrics_by_horizon": {"5": {"directional_accuracy": GOOD_SKILL}}},
    )
    position = {"symbol": "NABIL", "ltp": 500.0, "pnl_pct": 3.0}

    r = rec.for_position(position=position, predictions=predictions)

    assert r["action"] == "BUY"                  # +8% off the day-5 close, not the day-1
    assert r["expected_change_pct"] == 8.0
    assert r["target_close"] == 540.0
    assert r["horizon_days"] == 5
    assert r["directional_accuracy"] == GOOD_SKILL


def test_for_position_holds_when_no_forecast_exists():
    position = {"symbol": "NABIL", "ltp": 500.0, "pnl_pct": 3.0}
    r = rec.for_position(position=position, predictions=_StubPredictions())
    assert r["action"] == "HOLD"
    assert r["reliable"] is False
    assert r["expected_change_pct"] is None
