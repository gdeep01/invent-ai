from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_request_user
from app.core.rate_limit import limiter
from app.models import ForecastResult, ForecastRun, SKU, SalesTransaction, Store, User, get_db
from app.schemas import ForecastRequest, ForecastResponse, ForecastResultSchema, ForecastTaskResponse, ForecastTaskStatusResponse
from app.services.forecasting import ForecasterService
from app.services.forecasting.arima import ARIMAForecaster
from app.tasks import run_forecast_background

router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()


def validate_forecast_request(db: Session, current_user: User, payload: ForecastRequest) -> Store:
    store = db.query(Store).filter(Store.user_id == current_user.id, Store.store_id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    normalized_model = (payload.model or "arima").lower()
    if normalized_model != "arima":
        return store

    sku_query = db.query(SKU).filter(SKU.user_id == current_user.id, SKU.store_id == store.id)
    if payload.sku_ids:
        sku_query = sku_query.filter(SKU.sku_id.in_(payload.sku_ids))
    skus = sku_query.all()
    if not skus:
        raise HTTPException(status_code=422, detail="No matching SKUs found for this forecast request.")

    sku_ids_by_db_id = {sku.id: sku.sku_id for sku in skus}
    ranges = (
        db.query(
            SalesTransaction.sku_id,
            func.min(SalesTransaction.date),
            func.max(SalesTransaction.date),
        )
        .filter(
            SalesTransaction.user_id == current_user.id,
            SalesTransaction.store_id == store.id,
            SalesTransaction.sku_id.in_(list(sku_ids_by_db_id.keys())),
            SalesTransaction.excluded_from_forecast.is_(False),
        )
        .group_by(SalesTransaction.sku_id)
        .all()
    )
    range_by_sku = {
        sku_db_id: ((max_date - min_date).days + 1) if min_date and max_date else 0
        for sku_db_id, min_date, max_date in ranges
    }

    insufficient = []
    for sku_db_id, sku_id in sku_ids_by_db_id.items():
        days_of_history = range_by_sku.get(sku_db_id, 0)
        if days_of_history < ARIMAForecaster.MIN_DAYS_FOR_ARIMA:
            insufficient.append(f"{sku_id} ({days_of_history} days)")

    if insufficient:
        raise HTTPException(
            status_code=422,
            detail=(
                f"ARIMA requires at least {ARIMAForecaster.MIN_DAYS_FOR_ARIMA} days of sales history per SKU. "
                f"Not enough data for: {', '.join(insufficient[:5])}. Use the baseline model instead."
            ),
        )

    return store


@router.post("/run", response_model=ForecastTaskResponse, status_code=202)
@public_router.post("/run", response_model=ForecastTaskResponse, status_code=202)
@limiter.limit("5/minute")
def run_forecast(
    background_tasks: BackgroundTasks,
    request: Request,
    payload: ForecastRequest,
    current_user: User = Depends(get_request_user),
    db: Session = Depends(get_db),
):
    store = validate_forecast_request(db, current_user, payload)

    forecast_run = ForecastRun(
        user_id=current_user.id,
        store_id=store.id,
        task_id=f"bg-{store.id}-{datetime.utcnow().timestamp()}",
        horizon=payload.horizon,
        status="pending",
    )
    db.add(forecast_run)
    db.flush()
    db.commit()
    background_tasks.add_task(
        run_forecast_background,
        user_id=current_user.id,
        store_id=payload.store_id,
        horizon=payload.horizon,
        sku_ids=payload.sku_ids,
        model=payload.model,
        forecast_run_id=forecast_run.id,
    )
    return ForecastTaskResponse(success=True, task_id=forecast_run.task_id, status="queued", forecast_run_id=forecast_run.id)


@router.get("/status/{task_id}", response_model=ForecastTaskStatusResponse)
@public_router.get("/status/{task_id}", response_model=ForecastTaskStatusResponse)
def forecast_status(task_id: str, current_user: User = Depends(get_request_user), db: Session = Depends(get_db)):
    forecast_run = db.query(ForecastRun).filter(ForecastRun.user_id == current_user.id, ForecastRun.task_id == task_id).first()
    if not forecast_run:
        raise HTTPException(status_code=404, detail="Task not found")

    result_payload = None
    if forecast_run.status in {"success", "failure"}:
        result_payload = {"status": forecast_run.status, "summary": forecast_run.summary}
    return ForecastTaskStatusResponse(
        task_id=task_id,
        status=forecast_run.status or "pending",
        error_message=forecast_run.error_message,
        result=result_payload if isinstance(result_payload, dict) else None,
    )


@router.get("", response_model=ForecastResponse)
@public_router.get("", response_model=ForecastResponse)
def get_forecast(
    store_id: str,
    horizon: int = Query(default=7, ge=1, le=30),
    sku_id: str | None = None,
    current_user: User = Depends(get_request_user),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.user_id == current_user.id, Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    query = (
        db.query(ForecastResult)
        .filter(
            ForecastResult.user_id == current_user.id,
            ForecastResult.store_id == store.id,
            ForecastResult.forecast_horizon == horizon,
        )
        .order_by(ForecastResult.forecast_date)
    )
    if sku_id:
        sku = next((item for item in store.skus if item.sku_id == sku_id), None)
        if sku:
            query = query.filter(ForecastResult.sku_id == sku.id)

    results = query.all()
    sku_lookup = {sku.id: sku for sku in store.skus}
    response_rows = [
        ForecastResultSchema(
            sku_id=sku_lookup[result.sku_id].sku_id,
            sku_name=sku_lookup[result.sku_id].sku_name,
            forecast_date=result.forecast_date,
            predicted_units=result.predicted_units,
            confidence_lower=result.confidence_lower,
            confidence_upper=result.confidence_upper,
            model_used=result.model_used,
            health_score=result.health_score,
            festival_boost_applied=result.festival_boost_applied,
        )
        for result in results
        if result.sku_id in sku_lookup
    ]
    latest_run = (
        db.query(ForecastRun)
        .filter(ForecastRun.user_id == current_user.id, ForecastRun.store_id == store.id)
        .order_by(ForecastRun.created_at.desc())
        .first()
    )
    service = ForecasterService(db)
    return ForecastResponse(
        store_id=store_id,
        horizon=horizon,
        generated_at=latest_run.completed_at if latest_run and latest_run.completed_at else datetime.utcnow(),
        total_predicted=sum(row.predicted_units for row in response_rows),
        forecasts=response_rows,
        insights=service.generate_insights_from_results(results),
        mae_score=latest_run.mae_score if latest_run else None,
        last_run_at=latest_run.completed_at if latest_run else None,
    )


__all__ = ["router", "public_router"]
