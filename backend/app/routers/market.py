"""Market data and prediction routes (backend-agnostic via the container)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..container import Container
from ..deps import container
from ..schemas.market import (
    MAX_HORIZON_DAYS, OverviewItem, PredictionIn, PredictionOut, PredictionSeriesOut,
    QuoteOut, SeriesOut, TickerOut,
)
from ..services import prediction

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/tickers", response_model=list[TickerOut])
def tickers(c: Container = Depends(container)) -> list[dict]:
    return c.market.list_tickers()


@router.get("/quotes", response_model=list[QuoteOut])
def quotes(c: Container = Depends(container)) -> list[dict]:
    return c.market.get_market_quotes()


@router.get("/overview", response_model=list[OverviewItem])
def overview(c: Container = Depends(container)) -> list[dict]:
    """One call powering the dashboard: quote + sparkline + LSTM signal per ticker."""
    items = []
    for q in c.market.get_market_quotes():
        symbol = q["symbol"]
        spark = [r["close"] for r in c.market.get_series(symbol, "MAX")[-30:]]
        pred = c.predictions.get(symbol)
        items.append({
            **q,
            "spark": spark,
            "direction": pred["direction"] if pred else None,
            "confidence": float(pred["confidence"]) if pred else None,
            "model": pred.get("model") if pred else None,
        })
    return items


@router.get("/series/{symbol}", response_model=SeriesOut)
def series(
    symbol: str,
    range: str = Query("1Y", pattern="^(1M|6M|1Y|5Y|MAX)$"),
    c: Container = Depends(container),
) -> dict:
    candles = c.market.get_series(symbol.upper(), range)
    if not candles:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown symbol '{symbol}'")
    return {"symbol": symbol.upper(), "range": range, "candles": candles}


@router.get("/prediction-series/{symbol}", response_model=PredictionSeriesOut)
def prediction_series(
    symbol: str,
    horizon: int = Query(1, ge=1, le=MAX_HORIZON_DAYS),
    c: Container = Depends(container),
) -> dict:
    """Backtest series (predicted vs actual closes) plus the pending forecast path.
    """
    symbol = symbol.upper()
    bt = c.predictions.get_backtest(symbol)
    if not bt:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"No prediction series for '{symbol}'. Run ml/backtest.py.")

    # Pick the requested horizon, falling back to the day-1 series for older artifacts.
    key = str(horizon)
    metrics_by_h = bt.get("metrics_by_horizon") or {}
    points_by_h = bt.get("points_by_horizon") or {}
    if key in metrics_by_h:
        metrics, points, served = metrics_by_h[key], points_by_h.get(key, []), horizon
    else:
        metrics, points, served = bt["metrics"], bt.get("points", []), 1

    last_point_date = points[-1]["date"][:10] if points else ""

    log = c.predictions.get_forecast_log(symbol)
    # Keep only the newest rollout: a re-run writes a fresh path over the same target
    # dates, and mixing runs would draw a path stitched from different anchor days.
    # Records predating the change have no generated_at and all collapse into one group.
    if log:
        newest = max(str(f.get("generated_at", "")) for f in log)
        log = [f for f in log if str(f.get("generated_at", "")) == newest]

    # Keep only forecasts beyond the last backtest day (pending / future), and only the
    # steps up to the horizon being viewed.
    closes_by_date = {row["date"][:10]: row["close"] for row in c.market.get_series(symbol, "MAX")}
    forward = []
    for f in log:
        target = str(f.get("target_date", ""))[:10]
        if target <= last_point_date:
            continue
        step = f.get("step")
        if step is not None and int(step) > horizon:
            continue
        forward.append({
            "target_date": target,
            "predicted_close": f.get("predicted_close"),
            "last_close": f.get("last_close"),
            "actual_close": closes_by_date.get(target),
            "step": step,
        })

    return {
        "symbol": symbol,
        "model": bt.get("model", "lstm-v1"),
        "horizon_days": served,
        "metrics": metrics,
        "points": points,
        "forward": forward,
    }


@router.post("/predict", response_model=PredictionOut)
def predict(body: PredictionIn, c: Container = Depends(container)) -> dict:
    result = prediction.predict(
        predictions=c.predictions, market=c.market,
        symbol=body.symbol.upper(), horizon_days=body.horizon_days,
    )
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"No data to predict for '{body.symbol}'")
    return result
