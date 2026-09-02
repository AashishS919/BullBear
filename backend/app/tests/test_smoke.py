"""Smoke tests: auth flow, RBAC, market data, orders, prediction."""
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)
settings = get_settings()


def _login(email: str, password: str) -> str:
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_register_login_me():
    email = "newtrader@example.com"
    r = client.post("/api/auth/register", json={
        "name": "New Trader", "email": email, "password": "Trader@123",
    })
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    me = client.get("/api/auth/me", headers=_auth(token))
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == email and body["role"] == "USER"


def test_register_weak_password_rejected():
    r = client.post("/api/auth/register", json={
        "name": "Weak One", "email": "weak@example.com", "password": "alllowercase",
    })
    assert r.status_code == 422


def test_me_requires_token():
    assert client.get("/api/auth/me").status_code == 401


def test_rbac_admin_only():
    # Regular user is forbidden from admin routes.
    user_token = _login("newtrader@example.com", "Trader@123")
    assert client.get("/api/admin/users", headers=_auth(user_token)).status_code == 403

    # Seeded admin is allowed.
    admin_token = _login(settings.seed_admin_email, settings.seed_admin_password)
    r = client.get("/api/admin/users", headers=_auth(admin_token))
    assert r.status_code == 200
    assert any(u["role"] == "ADMIN" for u in r.json())


def test_market_series_five_years():
    r = client.get("/api/market/series/NABIL", params={"range": "MAX"})
    assert r.status_code == 200
    candles = r.json()["candles"]
    assert len(candles) > 1200  # ~5.5 years of trading days
    assert {"open", "high", "low", "close", "volume"} <= candles[0].keys()


def test_predict_contract():
    r = client.post("/api/market/predict", json={"symbol": "NTC", "horizon_days": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["direction"] in ("up", "down")
    assert 0.0 <= body["confidence"] <= 1.0
    assert body["model"]
    assert body["horizon_days"] == 1
    assert isinstance(body["path"], list)  # empty for the stub, 5 steps for a real model


def test_predict_accepts_five_day_horizon():
    r = client.post("/api/market/predict", json={"symbol": "NTC", "horizon_days": 5})
    assert r.status_code == 200, r.text
    assert r.json()["horizon_days"] == 5


def test_predict_rejects_horizon_beyond_max():
    # The schema used to accept up to 30 and silently answer with a 1-day forecast.
    r = client.post("/api/market/predict", json={"symbol": "NTC", "horizon_days": 6})
    assert r.status_code == 422


def test_prediction_series_contract():
    # NABIL has a backtest fixture (conftest): predicted-vs-actual points + metrics.
    r = client.get("/api/market/prediction-series/NABIL")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["symbol"] == "NABIL"
    assert {"mae", "rmse", "directional_accuracy"} <= body["metrics"].keys()
    assert len(body["points"]) == 2
    assert {"date", "actual", "predicted"} <= body["points"][0].keys()
    assert body["horizon_days"] == 1
    # forward holds only the newest run, beyond the last backtest day (2026-06-09), and
    # only steps within the requested horizon - so step 1 alone at the default horizon.
    assert [f["target_date"] for f in body["forward"]] == ["2026-06-10"]
    # The stale run also targeted 2026-06-12; the newest-run filter must have dropped it.
    assert 999.0 not in [f["predicted_close"] for f in body["forward"]]


def test_prediction_series_five_day_horizon():
    r = client.get("/api/market/prediction-series/NABIL", params={"horizon": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["horizon_days"] == 5
    # Metrics must come from the 5-day backtest, not be borrowed from the 1-day model.
    assert body["metrics"]["mae"] == 11.8
    assert body["points"][0]["predicted"] == 459.0
    # All five rollout steps are exposed, in date order.
    assert [f["step"] for f in body["forward"]] == [1, 2, 3, 4, 5]


def test_prediction_series_rejects_horizon_beyond_max():
    r = client.get("/api/market/prediction-series/NABIL", params={"horizon": 6})
    assert r.status_code == 422


def test_prediction_series_missing_is_404():
    # A symbol with no backtest series returns 404.
    assert client.get("/api/market/prediction-series/CHCL").status_code == 404


def test_order_validation_and_execution():
    admin_token = _login(settings.seed_admin_email, settings.seed_admin_password)

    # Oversize buy is rejected on cash balance.
    bad = client.post("/api/orders", headers=_auth(admin_token), json={
        "symbol": "NABIL", "side": "BUY", "order_type": "MARKET", "qty": 100000,
    })
    assert bad.status_code == 400

    # Non-positive quantity fails schema validation.
    invalid = client.post("/api/orders", headers=_auth(admin_token), json={
        "symbol": "NABIL", "side": "BUY", "order_type": "MARKET", "qty": 0,
    })
    assert invalid.status_code == 422

    # Valid small buy executes.
    ok = client.post("/api/orders", headers=_auth(admin_token), json={
        "symbol": "NABIL", "side": "BUY", "order_type": "MARKET", "qty": 1,
    })
    assert ok.status_code == 201, ok.text
    assert ok.json()["status"] == "EXECUTED"


def test_portfolio_shape():
    admin_token = _login(settings.seed_admin_email, settings.seed_admin_password)
    r = client.get("/api/portfolio", headers=_auth(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert "positions" in body and "summary" in body
    assert "net_worth" in body["summary"]

    # Every position carries a recommendation. This env points BB_PREDICTIONS_PATH at a
    # missing file, so it pins the no-forecast fallback: HOLD, never a directional call.
    assert body["positions"], "seed data should leave the admin holding something"
    for p in body["positions"]:
        rec = p["recommendation"]
        assert rec["action"] in ("BUY", "SELL", "HOLD")
        assert rec["action"] == "HOLD" and rec["reliable"] is False
        assert rec["expected_change_pct"] is None
