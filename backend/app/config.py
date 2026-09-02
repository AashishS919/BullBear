"""Application settings loaded from environment / .env (pydantic-settings)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="BB_", extra="ignore"
    )

    # JWT
    jwt_secret: str = "dev-secret-change-me-please-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    # CORS (comma-separated string -> list)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Seed admin
    seed_admin_email: str = "aashish@gmail.com"
    seed_admin_password: str = "Admin@123"

    # Data backend: "memory" (Phase 2) | "mongo" (Phase 3)
    data_backend: str = "memory"

    # MongoDB (Phase 3)
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "bullbear"

    # Market data source: "mock" (deterministic generator) | "nepsealpha" (parse.bot).
    market_source: str = "mock"

    # parse.bot NepseAlpha API (used when market_source == "nepsealpha").
    parsebot_api_key: str = ""
    parsebot_scraper_id: str = "646d18ff-34ab-4123-becc-9b1b6b35031e"
    parsebot_base_url: str = "https://api.parse.bot"
    # Live/WS refresh cadence in seconds. Keep high on the free tier (100 credits/mo,
    # 5 req/min); lower only after upgrading. One poll = 1 credit for the whole board.
    live_poll_seconds: int = 900

    # Paths to the LSTM JSON fallbacks (written by ml/infer.py and ml/backtest.py).
    predictions_path: str = "../ml/artifacts/predictions.json"
    prediction_series_path: str = "../ml/artifacts/prediction_series.json"
    forecast_log_path: str = "../ml/artifacts/forecast_log.json"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
