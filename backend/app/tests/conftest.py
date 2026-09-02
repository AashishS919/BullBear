"""Force the in-memory backend for tests so they stay hermetic regardless of .env
"""
import json
import os
import tempfile

os.environ["BB_DATA_BACKEND"] = "memory"
# Use a path that will not exist so /predict exercises the deterministic stub.
os.environ["BB_PREDICTIONS_PATH"] = "__no_predictions__.json"

# Write a small backtest fixture and point the API at it, so the prediction-series
# endpoint can be exercised without running the ML pipeline. NABIL has a series;
# other symbols fall through to 404.
_h1_points = [
    {"date": "2026-06-08", "actual": 470.0, "predicted": 468.5},
    {"date": "2026-06-09", "actual": 472.0, "predicted": 471.0},
]
_h5_points = [
    {"date": "2026-06-08", "actual": 470.0, "predicted": 459.0},
    {"date": "2026-06-09", "actual": 472.0, "predicted": 484.5},
]
_series_fixture = os.path.join(tempfile.gettempdir(), "bb_test_prediction_series.json")
with open(_series_fixture, "w", encoding="utf-8") as fh:
    json.dump({"series": [{
        "symbol": "NABIL",
        "model": "lstm-v1",
        # Top level stays the day-1 numbers; horizon maps carry every scored horizon.
        # The 5-day metrics are deliberately worse - that is the real shape of an
        # iterative rollout, and the endpoint must not serve day-1 accuracy for it.
        "metrics": {"mae": 4.2, "rmse": 5.1, "directional_accuracy": 0.58, "points": 2},
        "points": _h1_points,
        "metrics_by_horizon": {
            "1": {"mae": 4.2, "rmse": 5.1, "directional_accuracy": 0.58, "points": 2},
            "5": {"mae": 11.8, "rmse": 14.2, "directional_accuracy": 0.47, "points": 2},
        },
        "points_by_horizon": {"1": _h1_points, "5": _h5_points},
    }]}, fh)
os.environ["BB_PREDICTION_SERIES_PATH"] = _series_fixture

# Forecast log covering two runs. The stale run must be dropped wholesale by the
# newest-run filter (its 999.0 value would be obvious if it leaked), and the past-dated
# record must be dropped by the "beyond the last backtest day (2026-06-09)" filter.
# The current run is a 5-step rollout: horizon=1 exposes one marker, horizon=5 all five.
_log_fixture = os.path.join(tempfile.gettempdir(), "bb_test_forecast_log.json")
_stale_run = "2026-06-08T00:00:00+00:00"
_current_run = "2026-06-10T00:00:00+00:00"
with open(_log_fixture, "w", encoding="utf-8") as fh:
    json.dump({"forecasts": [
        {"symbol": "NABIL", "target_date": "2026-06-05", "step": 1, "predicted_close": 460.0,
         "last_close": 462.0, "generated_at": _stale_run},
        {"symbol": "NABIL", "target_date": "2026-06-12", "step": 3, "predicted_close": 999.0,
         "last_close": 462.0, "generated_at": _stale_run},
        {"symbol": "NABIL", "target_date": "2026-06-10", "step": 1, "predicted_close": 473.0,
         "last_close": 472.0, "generated_at": _current_run},
        {"symbol": "NABIL", "target_date": "2026-06-11", "step": 2, "predicted_close": 474.0,
         "last_close": 472.0, "generated_at": _current_run},
        {"symbol": "NABIL", "target_date": "2026-06-12", "step": 3, "predicted_close": 475.0,
         "last_close": 472.0, "generated_at": _current_run},
        {"symbol": "NABIL", "target_date": "2026-06-15", "step": 4, "predicted_close": 476.0,
         "last_close": 472.0, "generated_at": _current_run},
        {"symbol": "NABIL", "target_date": "2026-06-16", "step": 5, "predicted_close": 477.0,
         "last_close": 472.0, "generated_at": _current_run},
    ]}, fh)
os.environ["BB_FORECAST_LOG_PATH"] = _log_fixture
