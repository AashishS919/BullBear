"""Transaction history route."""
from fastapi import APIRouter, Depends, Query

from ..container import Container
from ..deps import container, get_current_user
from ..schemas.orders import OrderOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[OrderOut])
def transactions(
    side: str | None = Query(None, pattern="^(BUY|SELL)$"),
    user: dict = Depends(get_current_user),
    c: Container = Depends(container),
) -> list[dict]:
    rows = c.orders.list_for_user(user["id"])
    if side:
        rows = [r for r in rows if r["side"] == side]
    return rows
