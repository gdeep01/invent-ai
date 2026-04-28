import logging
from datetime import datetime

from app.models import ForecastRun, ForecastRunStatus, SessionLocal
from app.services.forecasting import ForecasterService
from app.services.mandi_prices import MandiPriceService
from app.services.reorder import ReorderService

logger = logging.getLogger("inventai.tasks")


def _mark_forecast_run_failure(user_id: int, forecast_run_id: int | None, message: str) -> None:
    db = SessionLocal()
    try:
        forecast_run = db.query(ForecastRun).filter(ForecastRun.id == forecast_run_id, ForecastRun.user_id == user_id).first()
        if forecast_run:
            forecast_run.status = ForecastRunStatus.FAILURE.value
            forecast_run.error_message = message
            forecast_run.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


def execute_forecast_job(user_id: int, store_id: str, horizon: int = 7, sku_ids: list | None = None, model: str = "arima", forecast_run_id: int | None = None):
    db = SessionLocal()
    try:
        forecast_run = db.query(ForecastRun).filter(ForecastRun.id == forecast_run_id, ForecastRun.user_id == user_id).first()
        if forecast_run:
            forecast_run.status = ForecastRunStatus.STARTED.value
            db.commit()

        forecast_service = ForecasterService(db)
        forecasts = forecast_service.forecast_store(user_id=user_id, store_id=store_id, horizon=horizon, sku_ids=sku_ids, model=model)
        saved_count = forecast_service.save_forecasts(user_id=user_id, store_id=store_id, forecasts=forecasts, horizon=horizon, forecast_run=forecast_run)

        reorder_service = ReorderService(db)
        recommendations = reorder_service.generate_recommendations(user_id=user_id, store_id=store_id, horizon=horizon)
        reorder_service.save_recommendations(user_id=user_id, store_id=store_id, recommendations=recommendations)

        alert_count = forecast_service.generate_alerts(
            user_id=user_id,
            store_id=store_id,
            recommendations=recommendations,
            mandi_prices=MandiPriceService().get_latest_prices(),
        )

        if forecast_run:
            forecast_run.status = ForecastRunStatus.SUCCESS.value
            forecast_run.model_used = next(iter(forecasts.values()))["model_used"] if forecasts else model
            forecast_run.mae_score = None
            forecast_run.summary = f"Saved {saved_count} forecast rows and {alert_count} alerts."
            forecast_run.completed_at = datetime.utcnow()
            db.commit()

        logger.info(
            "forecast_completed",
            extra={
                "user_id": user_id,
                "store_id": store_id,
                "model_used": next(iter(forecasts.values()))["model_used"] if forecasts else model,
                "mae_score": None,
            },
        )
        return {
            "store_id": store_id,
            "forecasts_generated": len(forecasts),
            "reorder_recs_generated": len(recommendations),
            "alerts_generated": alert_count,
            "status": "completed",
        }
    finally:
        db.close()


def run_forecast_background(
    user_id: int,
    store_id: str,
    horizon: int = 7,
    sku_ids: list | None = None,
    model: str = "arima",
    forecast_run_id: int | None = None,
):
    try:
        return execute_forecast_job(
            user_id=user_id,
            store_id=store_id,
            horizon=horizon,
            sku_ids=sku_ids,
            model=model,
            forecast_run_id=forecast_run_id,
        )
    except Exception as exc:
        logger.exception("forecast_background_task_failed")
        _mark_forecast_run_failure(user_id, forecast_run_id, str(exc))
        raise
