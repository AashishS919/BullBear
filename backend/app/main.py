"""FastAPI application factory for the BullBear backend (Phase 2)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .container import get_container
from .routers import admin, auth, market, orders, portfolio, transactions, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build + seed the data container at startup.
    get_container()
    # Start the shared market-stream poller (mock random walk or parse.bot live feed).
    await ws.start_feed()
    try:
        yield
    finally:
        await ws.stop_feed()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="BullBear Stock API",
        version=__version__,
        description="Controller/Middleware layer for the Nepalese stock prediction "
                    "and simulated-trading platform.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "version": __version__, "data_backend": settings.data_backend}

    for r in (auth, market, portfolio, orders, transactions, admin, ws):
        app.include_router(r.router)

    return app


app = create_app()
