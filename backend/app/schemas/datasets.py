"""Dataset management schemas (admin)."""
from pydantic import BaseModel, Field

from .common import DataSource, DatasetStatus


class DatasetOut(BaseModel):
    id: str
    symbol: str
    rows: int
    from_date: str = Field(serialization_alias="from")
    to_date: str = Field(serialization_alias="to")
    source: DataSource
    updated: str
    status: DatasetStatus

    model_config = {"populate_by_name": True}


class DatasetCreateIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=12)
    source: DataSource = DataSource.CSV
    from_date: str | None = None
    to_date: str | None = None


class UserUpdateIn(BaseModel):
    """Admin patch for a user account."""
    status: str | None = None
    role: str | None = None
