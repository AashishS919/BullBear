"""Data access + preparation for the LSTM.

Reads cleaned OHLCV from the MongoDB `market_candles` collection (produced by the
backend data pipeline), MinMax-scales the close series, and builds look-back sequences
with a chronological train/validation split.
"""
import numpy as np
from pymongo import ASCENDING, MongoClient
from sklearn.preprocessing import MinMaxScaler

from config import MONGO_DB, MONGO_URI, TRAIN_SPLIT, WINDOW


def _load_rows(symbol: str) -> list[dict]:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
    try:
        return list(
            client[MONGO_DB].market_candles
            .find({"symbol": symbol}, {"_id": 0, "close": 1, "date": 1})
            .sort("date", ASCENDING)
        )
    finally:
        client.close()


def load_closes(symbol: str) -> np.ndarray:
    rows = _load_rows(symbol)
    return np.array([r["close"] for r in rows], dtype="float32").reshape(-1, 1)


def load_closes_dated(symbol: str):
    """Return (closes Nx1 float32, dates list[str]) aligned by index."""
    rows = _load_rows(symbol)
    closes = np.array([r["close"] for r in rows], dtype="float32").reshape(-1, 1)
    dates = [str(r["date"]) for r in rows]
    return closes, dates


def make_sequences(scaled: np.ndarray, window: int = WINDOW):
    X, y = [], []
    for i in range(window, len(scaled)):
        X.append(scaled[i - window:i, 0])
        y.append(scaled[i, 0])
    X = np.array(X).reshape(-1, window, 1)
    y = np.array(y)
    return X, y


def prepare(symbol: str, window: int = WINDOW):
    """Return (X_train, y_train, X_val, y_val, scaler, closes)."""
    closes = load_closes(symbol)
    if len(closes) <= window + 10:
        raise ValueError(f"Not enough data for {symbol}: {len(closes)} rows")

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(closes)

    X, y = make_sequences(scaled, window)
    split = int(len(X) * TRAIN_SPLIT)
    return X[:split], y[:split], X[split:], y[split:], scaler, closes
