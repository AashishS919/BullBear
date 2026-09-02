"""Market data and prediction schemas."""
from pydantic import BaseModel, Field

from .common import TrendDirection

# Longest forecast the ML layer publishes (ml/config.py HORIZON). Requests beyond this
# are rejected rather than silently answered with a shorter horizon.
MAX_HORIZON_DAYS = 5


class TickerOut(BaseModel):
    symbol: str
    name: str
    sector: str


class CandleOut(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class QuoteOut(BaseModel):
    symbol: str
    name: str
    sector: str
    close: float
    prev_close: float
    change: float
    change_pct: float
    volume: int


class SeriesOut(BaseModel):
    symbol: str
    range: str
    candles: list[CandleOut]


class PredictionIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    horizon_days: int = Field(default=1, ge=1, le=MAX_HORIZON_DAYS)


class ForecastStep(BaseModel):
    """One day of the multi-step forecast path (step 1 = next trading day)."""
    step: int = Field(ge=1)
    target_date: str
    predicted_close: float
    direction: TrendDirection
    confidence: float = Field(ge=0.0, le=1.0)


class PredictionOut(BaseModel):
    symbol: str
    direction: TrendDirection
    confidence: float = Field(ge=0.0, le=1.0)
    horizon_days: int
    model: str  # identifies the producing model (stub vs lstm-v1 in Phase 3)
    last_close: float | None = None       # last actual close (anchor for the line)
    predicted_close: float | None = None  # forecast target (None for the stub)
    target_date: str | None = None        # trading day the forecast lands on
    path: list[ForecastStep] = []         # full 1..N rollout (empty for the stub)


class PredictionPoint(BaseModel):
    date: str
    actual: float
    predicted: float


class BacktestMetrics(BaseModel):
    mae: float
    rmse: float
    directional_accuracy: float = Field(ge=0.0, le=1.0)
    points: int


class ForecastRecord(BaseModel):
    target_date: str
    predicted_close: float
    last_close: float | None = None
    actual_close: float | None = None  # filled once the real close lands
    step: int | None = None            # which rollout day this record came from


class PredictionSeriesOut(BaseModel):
    symbol: str
    model: str
    horizon_days: int = 1                    # horizon the metrics/points describe
    metrics: BacktestMetrics
    points: list[PredictionPoint]            # historical backtest (predicted vs actual)
    forward: list[ForecastRecord] = []       # logged forecasts reconciled vs real closes


class OverviewItem(BaseModel):
    symbol: str
    name: str
    sector: str
    close: float
    change: float
    change_pct: float
    volume: int
    spark: list[float]                 # recent closes for the row sparkline
    direction: TrendDirection | None = None
    confidence: float | None = None
    model: str | None = None
