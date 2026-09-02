"""Shared enums used across schemas, mirroring the frontend domain vocabulary."""
from enum import Enum


class Role(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING = "PENDING"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    EXECUTED = "EXECUTED"
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


class DatasetStatus(str, Enum):
    READY = "READY"
    PROCESSING = "PROCESSING"
    STALE = "STALE"


class DataSource(str, Enum):
    CSV = "CSV"
    API = "API"


class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"


class RecommendationAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
