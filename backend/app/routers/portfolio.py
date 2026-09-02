"""Portfolio route (current user's holdings, value and P/L)."""
from fastapi import APIRouter, Depends, File, UploadFile

from ..container import Container
from ..deps import container, get_current_user
from ..schemas.orders import PortfolioImportResult, PortfolioOut
from ..services import order_service, portfolio_import, recommendation

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOut)
def portfolio(
    user: dict = Depends(get_current_user),
    c: Container = Depends(container),
) -> dict:
    """Holdings with value/P&L, each annotated with a model-derived BUY/SELL/HOLD call.
    """
    result = order_service.compute_portfolio(
        holdings=c.holdings, market=c.market, user_id=user["id"],
    )
    for position in result["positions"]:
        position["recommendation"] = recommendation.for_position(
            position=position, predictions=c.predictions,
        )
    return result


@router.post("/import", response_model=PortfolioImportResult)
async def import_portfolio(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    c: Container = Depends(container),
) -> dict:
    """Upload a CSV or PDF portfolio and merge it into the user's holdings (cash unchanged)."""
    content = await file.read()
    rows, warnings = portfolio_import.parse_portfolio(file.filename, content)
    imported, import_warnings = portfolio_import.import_holdings(
        holdings=c.holdings, market=c.market, user_id=user["id"], rows=rows,
    )
    return {
        "imported": imported,
        "skipped": len(warnings),
        "warnings": warnings + import_warnings,
    }
