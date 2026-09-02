"""In-memory repository implementations seeded to mirror the frontend mocks.
"""
import json
from datetime import date
from pathlib import Path

from ..security import hash_password
from . import market_data


class MemoryStore:
    """Holds all in-memory collections and seeds them once."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.orders: list[dict] = []
        self.holdings: dict[str, list[dict]] = {}   # user_id -> positions
        self.cash: dict[str, float] = {}            # user_id -> cash balance
        self.datasets: list[dict] = []
        self._order_seq = 10293

    # --- seeding -------------------------------------------------------------
    def seed(self, admin_email: str, admin_password: str) -> None:
        if self.users:
            return
        today = date.today().isoformat()

        seed_users = [
            ("USR-001", "Aashish Shrestha", admin_email, "ADMIN", "ACTIVE", "2024-11-02", today, admin_password),
            ("USR-014", "Sita Karki", "sita.k@example.com", "USER", "ACTIVE", "2025-01-18", "2026-06-08", "User@123"),
            ("USR-027", "Bibek Thapa", "bibek.t@example.com", "USER", "ACTIVE", "2025-03-04", today, "User@123"),
            ("USR-039", "Puja Gurung", "puja.g@example.com", "USER", "SUSPENDED", "2025-05-21", "2026-05-30", "User@123"),
            ("USR-048", "Ramesh Adhikari", "ramesh.a@example.com", "USER", "ACTIVE", "2025-08-09", "2026-06-07", "User@123"),
            ("USR-052", "Nisha Maharjan", "nisha.m@example.com", "USER", "PENDING", "2026-06-01", "2026-06-02", "User@123"),
        ]
        for uid, name, email, role, status, joined, last_seen, pw in seed_users:
            self.users[uid] = {
                "id": uid, "name": name, "email": email.lower(), "role": role,
                "status": status, "joined": joined, "last_seen": last_seen,
                "password_hash": hash_password(pw),
            }

        # Seed the admin's portfolio (mirrors frontend/src/mock/portfolio.js).
        admin_id = "USR-001"
        self.holdings[admin_id] = [
            {"symbol": "NABIL", "qty": 120, "avg_cost": 470.0},
            {"symbol": "NICA", "qty": 80, "avg_cost": 690.5},
            {"symbol": "NTC", "qty": 50, "avg_cost": 905.0},
            {"symbol": "UPPER", "qty": 200, "avg_cost": 512.25},
        ]
        self.cash[admin_id] = 185400.0

        self.orders = [
            {"id": "TXN-10293", "date": "2026-06-06", "symbol": "NABIL", "side": "BUY", "order_type": "MARKET", "qty": 40, "price": 511.0, "total": 20440.0, "status": "EXECUTED", "user_id": admin_id},
            {"id": "TXN-10288", "date": "2026-06-04", "symbol": "NTC", "side": "SELL", "order_type": "MARKET", "qty": 25, "price": 972.5, "total": 24312.5, "status": "EXECUTED", "user_id": admin_id},
            {"id": "TXN-10277", "date": "2026-05-29", "symbol": "NICA", "side": "BUY", "order_type": "MARKET", "qty": 30, "price": 742.0, "total": 22260.0, "status": "EXECUTED", "user_id": admin_id},
            {"id": "TXN-10269", "date": "2026-05-22", "symbol": "UPPER", "side": "BUY", "order_type": "MARKET", "qty": 100, "price": 498.75, "total": 49875.0, "status": "EXECUTED", "user_id": admin_id},
        ]

        self.datasets = [
            {"id": "DS-NABIL", "symbol": "NABIL", "rows": 1375, "from_date": "2021-01-04", "to_date": "2026-06-09", "source": "CSV", "updated": "2026-06-09", "status": "READY"},
            {"id": "DS-NICA", "symbol": "NICA", "rows": 1375, "from_date": "2021-01-04", "to_date": "2026-06-09", "source": "CSV", "updated": "2026-06-09", "status": "READY"},
            {"id": "DS-NTC", "symbol": "NTC", "rows": 1375, "from_date": "2021-01-04", "to_date": "2026-06-09", "source": "API", "updated": "2026-06-08", "status": "READY"},
            {"id": "DS-UPPER", "symbol": "UPPER", "rows": 1340, "from_date": "2021-02-15", "to_date": "2026-06-09", "source": "CSV", "updated": "2026-06-05", "status": "PROCESSING"},
            {"id": "DS-CHCL", "symbol": "CHCL", "rows": 1120, "from_date": "2021-06-01", "to_date": "2026-06-09", "source": "CSV", "updated": "2026-05-28", "status": "STALE"},
        ]

    def next_order_id(self) -> str:
        self._order_seq += 1
        return f"TXN-{self._order_seq}"


# --- Repository facades over the store ---
class MemoryUserRepo:
    def __init__(self, store: MemoryStore):
        self.store = store
        self._seq = 100

    def get_by_email(self, email: str) -> dict | None:
        email = email.lower()
        return next((u for u in self.store.users.values() if u["email"] == email), None)

    def get_by_id(self, user_id: str) -> dict | None:
        return self.store.users.get(user_id)

    def create(self, user: dict) -> dict:
        self._seq += 1
        uid = f"USR-{self._seq}"
        record = {"id": uid, **user, "email": user["email"].lower()}
        self.store.users[uid] = record
        self.store.holdings[uid] = []
        self.store.cash[uid] = 200000.0  # starting simulated cash
        return record

    def list(self) -> list[dict]:
        return list(self.store.users.values())

    def update(self, user_id: str, patch: dict) -> dict | None:
        u = self.store.users.get(user_id)
        if not u:
            return None
        u.update({k: v for k, v in patch.items() if v is not None})
        return u

    def touch_last_seen(self, user_id: str, when: str) -> None:
        if user_id in self.store.users:
            self.store.users[user_id]["last_seen"] = when


class MemoryOrderRepo:
    def __init__(self, store: MemoryStore):
        self.store = store

    def add(self, order: dict) -> dict:
        self.store.orders.insert(0, order)
        return order

    def list_for_user(self, user_id: str) -> list[dict]:
        return [o for o in self.store.orders if o.get("user_id") == user_id]


class MemoryHoldingRepo:
    def __init__(self, store: MemoryStore):
        self.store = store

    def list_for_user(self, user_id: str) -> list[dict]:
        return self.store.holdings.get(user_id, [])

    def get_cash(self, user_id: str) -> float:
        return self.store.cash.get(user_id, 0.0)

    def set_cash(self, user_id: str, amount: float) -> None:
        self.store.cash[user_id] = amount

    def upsert(self, user_id: str, symbol: str, qty: int, avg_cost: float) -> None:
        positions = self.store.holdings.setdefault(user_id, [])
        existing = next((p for p in positions if p["symbol"] == symbol), None)
        if qty <= 0:
            if existing:
                positions.remove(existing)
            return
        if existing:
            existing["qty"] = qty
            existing["avg_cost"] = avg_cost
        else:
            positions.append({"symbol": symbol, "qty": qty, "avg_cost": avg_cost})


class MemoryDatasetRepo:
    def __init__(self, store: MemoryStore):
        self.store = store

    def list(self) -> list[dict]:
        return list(self.store.datasets)

    def create(self, dataset: dict) -> dict:
        self.store.datasets.append(dataset)
        return dataset

    def delete(self, dataset_id: str) -> bool:
        before = len(self.store.datasets)
        self.store.datasets = [d for d in self.store.datasets if d["id"] != dataset_id]
        return len(self.store.datasets) < before


class MemoryMarketRepo:
    """Serves market data from the deterministic in-process generator."""

    def list_tickers(self) -> list[dict]:
        return market_data.list_tickers()

    def get_series(self, symbol: str, range_: str) -> list[dict]:
        full = market_data.get_series(symbol)
        return market_data.filter_by_range(full, range_) if full else []

    def get_quote(self, symbol: str) -> dict | None:
        return market_data.get_quote(symbol)

    def get_market_quotes(self) -> list[dict]:
        return market_data.get_market_quotes()


class MemoryPredictionRepo:
    """Reads LSTM artifacts (predictions / backtest series / forecast log) from JSON.
    """

    def __init__(self, predictions_path: str, series_path: str = "", forecast_log_path: str = ""):
        self._path = Path(predictions_path)
        self._series_path = Path(series_path) if series_path else None
        self._log_path = Path(forecast_log_path) if forecast_log_path else None

    @staticmethod
    def _read(path) -> dict | None:
        if not path or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None

    def _load(self) -> dict:
        data = self._read(self._path)
        if not data:
            return {}
        try:
            return {p["symbol"]: p for p in data.get("predictions", [])}
        except (KeyError, TypeError):
            return {}

    def get(self, symbol: str) -> dict | None:
        return self._load().get(symbol)

    def get_backtest(self, symbol: str) -> dict | None:
        data = self._read(self._series_path)
        if not data:
            return None
        for s in data.get("series", []):
            if s.get("symbol") == symbol:
                return s
        return None

    def get_forecast_log(self, symbol: str) -> list[dict]:
        data = self._read(self._log_path)
        if not data:
            return []
        return [f for f in data.get("forecasts", []) if f.get("symbol") == symbol]
