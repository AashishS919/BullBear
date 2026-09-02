"""Order placement and history routes (scoped to the authenticated user)."""
from fastapi import APIRouter, Depends, status

from ..container import Container
from ..deps import container, get_current_user
from ..schemas.orders import OrderIn, OrderOut
from ..services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def place_order(
    body: OrderIn,
    user: dict = Depends(get_current_user),
    c: Container = Depends(container),
) -> dict:
    return order_service.place_order(
        store=c.store, orders=c.orders, holdings=c.holdings, market=c.market,
        user_id=user["id"], symbol=body.symbol.upper(), side=body.side.value,
        order_type=body.order_type.value, qty=body.qty, limit_price=body.limit_price,
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    user: dict = Depends(get_current_user),
    c: Container = Depends(container),
) -> list[dict]:
    return c.orders.list_for_user(user["id"])
