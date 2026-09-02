"""Order, position and portfolio schemas."""
from pydantic import BaseModel, Field

from .common import OrderStatus, OrderType, RecommendationAction, Side


class OrderIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    side: Side
    order_type: OrderType = OrderType.MARKET
    qty: int = Field(gt=0, description="Whole number of shares, must be > 0")
    limit_price: float | None = Field(default=None, gt=0)


class OrderOut(BaseModel):
    id: str
    date: str
    symbol: str
    side: Side
    order_type: OrderType
    qty: int
    price: float
    total: float
    status: OrderStatus


class RecommendationOut(BaseModel):
    """Model-derived action for a held position. Educational output, not advice."""
    action: RecommendationAction
    reason: str
    reliable: bool = True                      # False when the model is gated or absent
    horizon_days: int
    expected_change_pct: float | None = None   # forecast move from LTP, in percent
    target_close: float | None = None          # forecast close at that horizon
    confidence: float | None = None
    directional_accuracy: float | None = None  # backtested skill on this ticker


class PositionOut(BaseModel):
    symbol: str
    name: str
    qty: int
    avg_cost: float
    ltp: float
    day_change_pct: float
    invested: float
    market_value: float
    pnl: float
    pnl_pct: float
    recommendation: RecommendationOut | None = None


class PortfolioSummaryOut(BaseModel):
    invested: float
    market_value: float
    pnl: float
    pnl_pct: float
    cash: float
    net_worth: float


class PortfolioOut(BaseModel):
    positions: list[PositionOut]
    summary: PortfolioSummaryOut


class PortfolioImportResult(BaseModel):
    imported: int
    skipped: int
    warnings: list[str]
