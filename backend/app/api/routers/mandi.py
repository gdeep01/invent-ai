from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models import User
from app.services.mandi_prices import MandiPriceService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/prices")
def get_mandi_prices(
    commodity: str | None = None,
    state: str | None = None,
    market: str | None = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
):
    payload = MandiPriceService().fetch_latest_prices(
        commodity=commodity,
        state=state,
        market=market,
        limit=limit,
    )
    return {
        "success": payload["live"],
        **payload,
    }
