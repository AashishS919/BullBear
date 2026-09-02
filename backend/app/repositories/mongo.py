"""MongoDB (PyMongo) repository implementations
"""
from pymongo import ASCENDING, MongoClient

from . import market_data

_PROJECT = {"_id": 0}  # never leak Mongo's _id into API responses


class MongoStore:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        self.db = self.client[db_name]

    def next_id(self, name: str, prefix: str, width: int = 3) -> str:
        doc = self.db["_counters"].find_one_and_update(
            {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=True
        )
        return f"{prefix}-{doc['seq']:0{width}d}"

    def next_order_id(self) -> str:
        """Parity with MemoryStore.next_order_id (used by order_service)."""
        doc = self.db["_counters"].find_one_and_update(
            {"_id": "orders"}, {"$inc": {"seq": 1}}, upsert=True, return_document=True
        )
        return f"TXN-{doc['seq']}"


class MongoUserRepo:
    def __init__(self, store: MongoStore):
        self.db = store.db
        self.store = store

    def get_by_email(self, email: str) -> dict | None:
        return self.db.users.find_one({"email": email.lower()}, _PROJECT)

    def get_by_id(self, user_id: str) -> dict | None:
        return self.db.users.find_one({"id": user_id}, _PROJECT)

    def create(self, user: dict) -> dict:
        uid = self.store.next_id("users", "USR")
        record = {"id": uid, **user, "email": user["email"].lower(), "cash": 200000.0}
        self.db.users.insert_one(dict(record))
        return self.db.users.find_one({"id": uid}, _PROJECT)

    def list(self) -> list[dict]:
        return list(self.db.users.find({}, _PROJECT).sort("id", ASCENDING))

    def update(self, user_id: str, patch: dict) -> dict | None:
        clean = {k: v for k, v in patch.items() if v is not None}
        if clean:
            self.db.users.update_one({"id": user_id}, {"$set": clean})
        return self.get_by_id(user_id)

    def touch_last_seen(self, user_id: str, when: str) -> None:
        self.db.users.update_one({"id": user_id}, {"$set": {"last_seen": when}})


class MongoOrderRepo:
    def __init__(self, store: MongoStore):
        self.db = store.db
        self.store = store

    def add(self, order: dict) -> dict:
        self.db.orders.insert_one(dict(order))
        return self.db.orders.find_one({"id": order["id"]}, _PROJECT)

    def list_for_user(self, user_id: str) -> list[dict]:
        return list(
            self.db.orders.find({"user_id": user_id}, _PROJECT).sort("date", -1)
        )


class MongoHoldingRepo:
    def __init__(self, store: MongoStore):
        self.db = store.db

    def list_for_user(self, user_id: str) -> list[dict]:
        return list(self.db.holdings.find({"user_id": user_id}, _PROJECT))

    def get_cash(self, user_id: str) -> float:
        u = self.db.users.find_one({"id": user_id}, {"_id": 0, "cash": 1})
        return float(u.get("cash", 0.0)) if u else 0.0

    def set_cash(self, user_id: str, amount: float) -> None:
        self.db.users.update_one({"id": user_id}, {"$set": {"cash": amount}})

    def upsert(self, user_id: str, symbol: str, qty: int, avg_cost: float) -> None:
        if qty <= 0:
            self.db.holdings.delete_one({"user_id": user_id, "symbol": symbol})
            return
        self.db.holdings.update_one(
            {"user_id": user_id, "symbol": symbol},
            {"$set": {"qty": qty, "avg_cost": avg_cost}},
            upsert=True,
        )


class MongoDatasetRepo:
    def __init__(self, store: MongoStore):
        self.db = store.db

    def list(self) -> list[dict]:
        return list(self.db.datasets.find({}, _PROJECT).sort("id", ASCENDING))

    def create(self, dataset: dict) -> dict:
        self.db.datasets.replace_one({"id": dataset["id"]}, dict(dataset), upsert=True)
        return self.db.datasets.find_one({"id": dataset["id"]}, _PROJECT)

    def delete(self, dataset_id: str) -> bool:
        return self.db.datasets.delete_one({"id": dataset_id}).deleted_count > 0


class MongoMarketRepo:
    """Reads OHLCV from the indexed market_candles collection."""

    def __init__(self, store: MongoStore):
        self.db = store.db

    def list_tickers(self) -> list[dict]:
        return market_data.list_tickers()

    def _all(self, symbol: str) -> list[dict]:
        return list(
            self.db.market_candles.find({"symbol": symbol}, _PROJECT)
            .sort("date", ASCENDING)
        )

    def get_series(self, symbol: str, range_: str) -> list[dict]:
        full = self._all(symbol)
        rows = [{k: r[k] for k in ("date", "open", "high", "low", "close", "volume")}
                for r in full]
        return market_data.filter_by_range(tuple(rows), range_)

    def get_quote(self, symbol: str) -> dict | None:
        rows = self._all(symbol)
        if len(rows) < 2:
            return None
        last, prev = rows[-1], rows[-2]
        change = round(last["close"] - prev["close"], 2)
        change_pct = round((change / prev["close"]) * 100, 2) if prev["close"] else 0.0
        meta = next((t for t in market_data.TICKERS if t["symbol"] == symbol), {})
        return {
            "symbol": symbol,
            "name": meta.get("name", symbol),
            "sector": meta.get("sector", ""),
            "close": last["close"],
            "prev_close": prev["close"],
            "change": change,
            "change_pct": change_pct,
            "volume": last["volume"],
        }

    def get_market_quotes(self) -> list[dict]:
        return [q for q in (self.get_quote(t["symbol"]) for t in market_data.TICKERS) if q]


class MongoPredictionRepo:
    """Reads LSTM artifacts from Mongo: `predictions` (infer.py), `prediction_series`
    and `forecast_log` (backtest.py / infer.py)."""

    def __init__(self, store: MongoStore):
        self.db = store.db

    def get(self, symbol: str) -> dict | None:
        return self.db.predictions.find_one({"symbol": symbol}, _PROJECT)

    def get_backtest(self, symbol: str) -> dict | None:
        return self.db.prediction_series.find_one({"symbol": symbol}, _PROJECT)

    def get_forecast_log(self, symbol: str) -> list[dict]:
        return list(
            self.db.forecast_log.find({"symbol": symbol}, _PROJECT).sort("target_date", ASCENDING)
        )
