"""Seed the local MongoDB `bullbear` database (Phase 3).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import ASCENDING, MongoClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.repositories.memory import MemoryStore  # noqa: E402
import data_pipeline  # noqa: E402  (same scripts/ dir)


def seed() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    db = client[settings.mongo_db]

    # Build canonical seed data in memory, then mirror it into Mongo.
    store = MemoryStore()
    store.seed(settings.seed_admin_email, settings.seed_admin_password)

    # --- users (attach cash) ---
    db.users.drop()
    users = []
    for uid, u in store.users.items():
        users.append({**u, "cash": store.cash.get(uid, 0.0)})
    db.users.insert_many(users)
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("id", ASCENDING)], unique=True)

    # --- holdings (one doc per position) ---
    db.holdings.drop()
    holding_docs = []
    for uid, positions in store.holdings.items():
        for p in positions:
            holding_docs.append({"user_id": uid, **p})
    if holding_docs:
        db.holdings.insert_many(holding_docs)
    db.holdings.create_index([("user_id", ASCENDING), ("symbol", ASCENDING)], unique=True)

    # --- orders ---
    db.orders.drop()
    if store.orders:
        db.orders.insert_many([dict(o) for o in store.orders])
    db.orders.create_index([("user_id", ASCENDING), ("date", ASCENDING)])

    # --- datasets ---
    db.datasets.drop()
    db.datasets.insert_many([dict(d) for d in store.datasets])
    db.datasets.create_index([("id", ASCENDING)], unique=True)

    # --- counters (so generated ids continue cleanly) ---
    db["_counters"].drop()
    max_order = max(
        (int(o["id"].split("-")[1]) for o in store.orders if o["id"].startswith("TXN-")),
        default=10293,
    )
    db["_counters"].insert_many([
        {"_id": "users", "seq": 100},        # next registered user -> USR-101
        {"_id": "orders", "seq": max_order},  # next order -> TXN-(max+1)
    ])

    print(f"Seeded operational collections into '{settings.mongo_db}':")
    print(f"  users={db.users.count_documents({})} "
          f"holdings={db.holdings.count_documents({})} "
          f"orders={db.orders.count_documents({})} "
          f"datasets={db.datasets.count_documents({})}")

    client.close()

    # --- market_candles via the pipeline ---
    print("Loading market_candles via data pipeline ...")
    data_pipeline.run()

    # Verify candle counts + index.
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=4000)
    db = client[settings.mongo_db]
    total = db.market_candles.count_documents({})
    idx = [i for i in db.market_candles.index_information()]
    print(f"  market_candles total rows={total}; indexes={idx}")
    client.close()
    print("Seed complete.")


if __name__ == "__main__":
    seed()
