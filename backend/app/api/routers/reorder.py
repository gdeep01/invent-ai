from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_request_user
from app.models import ReorderRecommendation, SKU, Store, User, get_db
from app.schemas import ReorderItem, ReorderListResponse, ReorderSummary
from app.services.reorder import ReorderService

router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()


@router.get("/summary", response_model=ReorderSummary)
@public_router.get("/summary", response_model=ReorderSummary)
def get_summary(store_id: str, current_user: User = Depends(get_request_user), db: Session = Depends(get_db)):
    service = ReorderService(db)
    summary = service.get_summary(current_user.id, store_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return summary


@router.get("/list", response_model=ReorderListResponse)
@public_router.get("/list", response_model=ReorderListResponse)
def get_reorder_list(
    store_id: str,
    horizon: int = Query(default=7, ge=1, le=30),
    regenerate: bool = Query(default=True),
    current_user: User = Depends(get_request_user),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.user_id == current_user.id, Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    service = ReorderService(db)
    if regenerate:
        items = service.generate_recommendations(current_user.id, store_id, horizon)
        service.save_recommendations(current_user.id, store_id, items)
    else:
        rows = (
            db.query(ReorderRecommendation, SKU)
            .join(SKU, SKU.id == ReorderRecommendation.sku_id)
            .filter(
                ReorderRecommendation.user_id == current_user.id,
                ReorderRecommendation.store_id == store.id,
                ReorderRecommendation.is_active.is_(True),
            )
            .all()
        )
        items = [
            ReorderItem(
                sku_id=sku.sku_id,
                sku_name=sku.sku_name,
                reorder_qty=rec.reorder_qty,
                reason=rec.reason,
                urgency=rec.urgency,
                forecasted_demand=rec.forecasted_demand or 0,
                current_stock=rec.current_stock or 0,
                velocity_change_pct=rec.velocity_change_pct,
            )
            for rec, sku in rows
        ]
    return ReorderListResponse(
        store_id=store_id,
        store_name=store.name,
        generated_at=datetime.utcnow(),
        total_items=len(items),
        critical_items=sum(1 for item in items if item.urgency == "critical"),
        items=items,
    )


__all__ = ["router", "public_router"]
