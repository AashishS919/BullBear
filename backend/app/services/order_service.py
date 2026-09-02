"""Simulated order execution and portfolio computation (backend-agnostic)."""
from datetime import date

from fastapi import HTTPException, status

BROKER_FEE = 0.0036  # 0.36% mock brokerage + SEBON fee (matches frontend OrderPanel)


def place_order(
    *, store, orders, holdings, market,
    user_id: str, symbol: str, side: str, order_type: str, qty: int,
    limit_price: float | None,
) -> dict:
    quote = market.get_quote(symbol)
    if quote is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown symbol '{symbol}'")

    if order_type == "LIMIT":
        if not limit_price or limit_price <= 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "Limit orders require a positive limit_price.")
        price = float(limit_price)
    else:
        price = quote["close"]

    subtotal = qty * price
    fee = subtotal * BROKER_FEE
    cash = holdings.get_cash(user_id)
    positions = holdings.list_for_user(user_id)
    position = next((p for p in positions if p["symbol"] == symbol), None)

    if side == "BUY":
        total = subtotal + fee
        if total > cash:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "Order exceeds available cash balance.")
        holdings.set_cash(user_id, round(cash - total, 2))
        if position:
            new_qty = position["qty"] + qty
            new_avg = (position["qty"] * position["avg_cost"] + qty * price) / new_qty
            holdings.upsert(user_id, symbol, new_qty, round(new_avg, 2))
        else:
            holdings.upsert(user_id, symbol, qty, round(price, 2))
    else:  # SELL
        held = position["qty"] if position else 0
        if qty > held:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                f"Cannot sell {qty} shares; only {held} held.")
        total = subtotal - fee
        holdings.set_cash(user_id, round(cash + total, 2))
        holdings.upsert(user_id, symbol, held - qty, position["avg_cost"] if position else 0.0)

    order = {
        "id": store.next_order_id(),
        "date": date.today().isoformat(),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "qty": qty,
        "price": round(price, 2),
        "total": round(total, 2),
        "status": "EXECUTED",
        "user_id": user_id,
    }
    return orders.add(order)


def compute_portfolio(*, holdings, market, user_id: str) -> dict:
    positions_out = []
    for h in holdings.list_for_user(user_id):
        quote = market.get_quote(h["symbol"])
        ltp = quote["close"] if quote else h["avg_cost"]
        invested = h["qty"] * h["avg_cost"]
        market_value = h["qty"] * ltp
        pnl = market_value - invested
        positions_out.append({
            "symbol": h["symbol"],
            "name": quote["name"] if quote else h["symbol"],
            "qty": h["qty"],
            "avg_cost": round(h["avg_cost"], 2),
            "ltp": round(ltp, 2),
            "day_change_pct": quote["change_pct"] if quote else 0.0,
            "invested": round(invested, 2),
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / invested) * 100, 2) if invested else 0.0,
        })

    invested = sum(p["invested"] for p in positions_out)
    market_value = sum(p["market_value"] for p in positions_out)
    pnl = market_value - invested
    cash = holdings.get_cash(user_id)
    return {
        "positions": positions_out,
        "summary": {
            "invested": round(invested, 2),
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / invested) * 100, 2) if invested else 0.0,
            "cash": round(cash, 2),
            "net_worth": round(market_value + cash, 2),
        },
    }
