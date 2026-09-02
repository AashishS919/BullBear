"""Admin routes - user management and dataset management. All require ADMIN role."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from ..container import Container
from ..deps import container, require_admin
from ..schemas.auth import UserOut
from ..schemas.datasets import DatasetCreateIn, DatasetOut, UserUpdateIn

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# --- Users -------------------------------------------------------------------
@router.get("/users", response_model=list[UserOut])
def list_users(c: Container = Depends(container)) -> list[dict]:
    return c.users.list()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str, body: UserUpdateIn, c: Container = Depends(container)
) -> dict:
    updated = c.users.update(user_id, body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return updated


# --- Datasets ----------------------------------------------------------------
@router.get("/datasets", response_model=list[DatasetOut])
def list_datasets(c: Container = Depends(container)) -> list[dict]:
    return c.datasets.list()


@router.post("/datasets", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(body: DatasetCreateIn, c: Container = Depends(container)) -> dict:
    symbol = body.symbol.upper()
    today = date.today().isoformat()
    dataset = {
        "id": f"DS-{symbol}",
        "symbol": symbol,
        "rows": 0,
        "from_date": body.from_date or today,
        "to_date": body.to_date or today,
        "source": body.source.value,
        "updated": today,
        "status": "PROCESSING",
    }
    return c.datasets.create(dataset)


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, c: Container = Depends(container)) -> None:
    if not c.datasets.delete(dataset_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dataset not found")
