"""Composition root: builds repositories per the configured data backend.

"""
from functools import lru_cache

from .config import get_settings
from .repositories.memory import (
    MemoryDatasetRepo,
    MemoryHoldingRepo,
    MemoryMarketRepo,
    MemoryOrderRepo,
    MemoryPredictionRepo,
    MemoryStore,
    MemoryUserRepo,
)


class Container:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.data_backend == "memory":
            self.store = MemoryStore()
            self.store.seed(settings.seed_admin_email, settings.seed_admin_password)
            self.users = MemoryUserRepo(self.store)
            self.orders = MemoryOrderRepo(self.store)
            self.holdings = MemoryHoldingRepo(self.store)
            self.datasets = MemoryDatasetRepo(self.store)
            self.market = MemoryMarketRepo()
            self.predictions = MemoryPredictionRepo(
                settings.predictions_path,
                settings.prediction_series_path,
                settings.forecast_log_path,
            )
        elif settings.data_backend == "mongo":
            from .repositories.mongo import (
                MongoDatasetRepo,
                MongoHoldingRepo,
                MongoMarketRepo,
                MongoOrderRepo,
                MongoPredictionRepo,
                MongoStore,
                MongoUserRepo,
            )

            self.store = MongoStore(settings.mongo_uri, settings.mongo_db)
            self.users = MongoUserRepo(self.store)
            self.orders = MongoOrderRepo(self.store)
            self.holdings = MongoHoldingRepo(self.store)
            self.datasets = MongoDatasetRepo(self.store)
            self.market = MongoMarketRepo(self.store)
            self.predictions = MongoPredictionRepo(self.store)
        else:
            raise ValueError(f"Unknown data_backend '{settings.data_backend}'")


@lru_cache
def get_container() -> Container:
    return Container()
