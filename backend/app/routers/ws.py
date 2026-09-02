"""WebSocket market stream backed by a single shared snapshot.
"""
import asyncio
import random
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..container import get_container
from ..services import nepsealpha

router = APIRouter(tags=["realtime"])

TICK_INTERVAL_SECONDS = 2.0


class LiveFeed:
    """Holds the latest snapshot and lets clients await the next one."""

    def __init__(self) -> None:
        self.ticks: list[dict] = []
        self.ts: str = ""
        self._cond = asyncio.Condition()
        self._version = 0

    async def publish(self, ticks: list[dict]) -> None:
        async with self._cond:
            self.ticks = ticks
            self.ts = datetime.now(timezone.utc).isoformat()
            self._version += 1
            self._cond.notify_all()

    async def wait(self, last_version: int) -> tuple[int, list[dict], str]:
        async with self._cond:
            await self._cond.wait_for(lambda: self._version != last_version)
            return self._version, self.ticks, self.ts

    async def snapshot(self) -> tuple[int, list[dict], str]:
        """Atomically read the current (version, ticks, ts) under the lock, so a caller's
        version always matches the ticks it saw and no interleaved publish is missed."""
        async with self._cond:
            return self._version, self.ticks, self.ts


_feed = LiveFeed()
_task: asyncio.Task | None = None


def _mock_tick(prices: dict[str, float], rng: random.Random) -> list[dict]:
    ticks = []
    for symbol, price in prices.items():
        drift = (rng.random() - 0.5) * 0.01  # +/- ~0.5% per tick
        new_price = max(1.0, round(price * (1 + drift), 2))
        change = round(new_price - price, 2)
        prices[symbol] = new_price
        ticks.append({
            "symbol": symbol,
            "price": new_price,
            "change": change,
            "change_pct": round((change / price) * 100, 2) if price else 0.0,
        })
    return ticks


async def _poll_loop() -> None:
    settings = get_settings()
    container = get_container()
    symbols = {t["symbol"] for t in container.market.list_tickers()}
    # Seed from the latest close per ticker so the stream starts near charted values.
    prices = {q["symbol"]: q["close"] for q in container.market.get_market_quotes()}
    rng = random.Random()

    # Live only when configured with a key; otherwise stay on the mock random walk so a
    # missing/invalid key degrades gracefully instead of streaming an empty feed.
    live = settings.market_source == "nepsealpha" and nepsealpha.is_configured()

    # Always publish an initial snapshot so clients have data even if the first live
    # fetch fails.
    await _feed.publish(_mock_tick(dict(prices), rng))

    last_ok = True  # throttle: only log on the transition into a failure state
    while True:
        if live:
            try:
                ticks = await asyncio.to_thread(nepsealpha.fetch_live_market, symbols)
                await _feed.publish(ticks)
                last_ok = True
            except nepsealpha.NepseAlphaError as exc:
                # Keep serving the last good snapshot; retry next interval.
                if last_ok:
                    print(f"[ws] live refresh failed, keeping last snapshot: {exc}")
                    last_ok = False
            await asyncio.sleep(max(30, settings.live_poll_seconds))
        else:
            await _feed.publish(_mock_tick(prices, rng))
            await asyncio.sleep(TICK_INTERVAL_SECONDS)


async def start_feed() -> None:
    """Start the shared poller (idempotent). Called from the app lifespan."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_poll_loop())


async def stop_feed() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None


@router.websocket("/ws/market")
async def market_stream(ws: WebSocket) -> None:
    await ws.accept()
    # Capture ticks + version atomically so the initial send can't miss a racing publish.
    version, ticks, ts = await _feed.snapshot()
    if ticks:
        await ws.send_json({"type": "tick", "ts": ts, "data": ticks})
    try:
        while True:
            version, ticks, ts = await _feed.wait(version)
            await ws.send_json({"type": "tick", "ts": ts, "data": ticks})
    except WebSocketDisconnect:
        return
