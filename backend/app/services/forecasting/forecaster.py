import logging
from collections import defaultdict
from datetime import date
from typing import List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    FestivalMultiplier,
    ForecastResult,
    ForecastRun,
    SKU,
    SalesTransaction,
    Store,
    UserSettings,
)
from app.services.festivals import FestivalService
from app.services.forecasting.baseline import BaselineForecaster, calculate_velocity_change
from app.services.forecasting.arima import ARIMAForecaster

logger = logging.getLogger("inventai.forecast")


class ForecasterService:
    def __init__(self, db: Session):
        self.db = db

    def forecast_store(
        self,
        user_id: int,
        store_id: str,
        horizon: int = 7,
        sku_ids: Optional[List[str]] = None,
        model: str = "arima",
    ) -> dict:
        store = self.db.query(Store).filter(Store.user_id == user_id, Store.store_id == store_id).first()
        if not store:
            return {}

        sku_query = self.db.query(SKU).filter(SKU.user_id == user_id, SKU.store_id == store.id)
        if sku_ids:
            sku_query = sku_query.filter(SKU.sku_id.in_(sku_ids))
        skus = sku_query.all()
        sku_map = {sku.id: sku for sku in skus}
        if not sku_map:
            return {}

        transactions = (
            self.db.query(SalesTransaction)
            .filter(
                SalesTransaction.user_id == user_id,
                SalesTransaction.store_id == store.id,
                SalesTransaction.sku_id.in_(list(sku_map.keys())),
                SalesTransaction.excluded_from_forecast.is_(False),
            )
            .order_by(SalesTransaction.date)
            .all()
        )

        festival_service = FestivalService(self.db)
        upcoming_festivals = festival_service.get_upcoming_festivals(date.today(), horizon)
        multiplier_lookup = self._category_multiplier_lookup(user_id)

        data_by_sku = defaultdict(list)
        for transaction in transactions:
            data_by_sku[transaction.sku_id].append({"date": transaction.date, "units_sold": transaction.units_sold})

        results = {}
        for sku_db_id, sku in sku_map.items():
            records = data_by_sku.get(sku_db_id, [])
            if not records:
                continue
            frame = pd.DataFrame(records)
            forecast_points, model_used = self._forecast_points_for_model(frame, horizon, model)
            velocity_change = calculate_velocity_change(frame)
            festival_boost_applied = False
            multiplier = multiplier_lookup.get((sku.category or "").lower(), 1.0)
            if upcoming_festivals and multiplier > 1.0:
                festival_boost_applied = True
                for point in forecast_points:
                    point.predicted_units = round(point.predicted_units * multiplier, 2)
                    if point.confidence_lower is not None:
                        point.confidence_lower = round(point.confidence_lower * multiplier, 2)
                    if point.confidence_upper is not None:
                        point.confidence_upper = round(point.confidence_upper * multiplier, 2)

            results[sku.sku_id] = {
                "sku_name": sku.sku_name,
                "forecasts": forecast_points,
                "model_used": model_used,
                "velocity_change": velocity_change,
                "festival_boost_applied": festival_boost_applied,
                "health_score": self._health_score(sku.current_stock, forecast_points, velocity_change),
            }

        return results

    def save_forecasts(self, user_id: int, store_id: str, forecasts: dict, horizon: int, forecast_run: ForecastRun | None = None) -> int:
        store = self.db.query(Store).filter(Store.user_id == user_id, Store.store_id == store_id).first()
        if not store:
            return 0

        sku_lookup = {
            sku.sku_id: sku
            for sku in self.db.query(SKU).filter(SKU.user_id == user_id, SKU.store_id == store.id).all()
        }

        if sku_lookup:
            self.db.query(ForecastResult).filter(
                ForecastResult.user_id == user_id,
                ForecastResult.store_id == store.id,
                ForecastResult.sku_id.in_([sku.id for sku in sku_lookup.values()]),
                ForecastResult.forecast_horizon == horizon,
            ).delete(synchronize_session=False)

        forecast_objects: List[ForecastResult] = []
        for sku_id, data in forecasts.items():
            sku = sku_lookup.get(sku_id)
            if not sku:
                continue
            for point in data["forecasts"]:
                confidence_upper = point.confidence_upper or point.predicted_units
                confidence_lower = point.confidence_lower or point.predicted_units
                spread = max(confidence_upper - confidence_lower, 0)
                confidence = max(0.0, round(1 - (spread / max(point.predicted_units or 1, 1)), 2))
                forecast_objects.append(
                    ForecastResult(
                        user_id=user_id,
                        store_id=store.id,
                        sku_id=sku.id,
                        forecast_run_id=forecast_run.id if forecast_run else None,
                        forecast_date=point.date,
                        predicted_units=point.predicted_units,
                        confidence_lower=point.confidence_lower,
                        confidence_upper=point.confidence_upper,
                        model_used=data["model_used"],
                        forecast_horizon=horizon,
                        health_score=data.get("health_score"),
                        forecast_confidence=confidence,
                        festival_boost_applied=data.get("festival_boost_applied", False),
                    )
                )

        if forecast_objects:
            self.db.bulk_save_objects(forecast_objects)
            self.db.commit()
        return len(forecast_objects)

    def generate_alerts(self, user_id: int, store_id: str, recommendations, mandi_prices: list[dict]) -> int:
        store = self.db.query(Store).filter(Store.user_id == user_id, Store.store_id == store_id).first()
        if not store:
            return 0

        self.db.query(Alert).filter(Alert.user_id == user_id, Alert.store_id == store.id).delete(synchronize_session=False)
        mandi_price_lookup = {item.get("commodity", "").lower(): item for item in mandi_prices}
        created = 0
        for recommendation in recommendations:
            price_data = mandi_price_lookup.get(recommendation.sku_name.lower()) or {}
            price = price_data.get("modal_price", "N/A")
            message = (
                f"{recommendation.sku_name} stock is running low. "
                f"Reorder {recommendation.reorder_qty} units now. "
                f"Mandi price: Rs. {price}."
            )
            self.db.add(
                Alert(
                    user_id=user_id,
                    store_id=store.id,
                    message=message,
                    severity=recommendation.urgency,
                )
            )
            created += 1
        self.db.commit()
        return created

    def generate_insights_from_results(self, results: list[ForecastResult]) -> list[str]:
        if not results:
            return ["No forecast data available yet."]
        total = sum(result.predicted_units for result in results)
        boosted = sum(1 for result in results if result.festival_boost_applied)
        return [
            f"Projected demand totals {int(total)} units for the selected horizon.",
            f"Festival boost applied to {boosted} forecast points." if boosted else "No festival demand boost was applied.",
        ]

    def calculate_mae(self, transactions: list[SalesTransaction], forecasts: dict) -> float:
        actuals = {(transaction.sku_id, transaction.date): transaction.units_sold for transaction in transactions}
        errors = []
        for _, data in forecasts.items():
            for point in data["forecasts"]:
                for actual in actuals.values():
                    errors.append(abs(point.predicted_units - actual))
                    break
        return round(sum(errors) / len(errors), 2) if errors else 0.0

    def _forecast_points_for_model(self, frame: pd.DataFrame, horizon: int, model: str) -> tuple[list, str]:
        normalized_model = (model or "arima").lower()
        if normalized_model == "baseline":
            forecaster = BaselineForecaster(frame)
            return forecaster.moving_average_forecast(horizon), "baseline"

        forecaster = ARIMAForecaster(frame)
        return forecaster.forecast(horizon), forecaster.get_model_used()

    def _category_multiplier_lookup(self, user_id: int) -> dict[str, float]:
        settings_row = self.db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if not settings_row:
            return {}
        rows = self.db.query(FestivalMultiplier).filter(FestivalMultiplier.settings_id == settings_row.id).all()
        return {(row.category or "").lower(): row.multiplier for row in rows}

    def _health_score(self, current_stock: int, forecast_points, velocity_change: float) -> float:
        avg_demand = sum(point.predicted_units for point in forecast_points) / max(len(forecast_points), 1)
        days_of_stock = current_stock / avg_demand if avg_demand else 30
        stock_component = min(days_of_stock / 14, 1) * 40
        confidence_component = 35
        trend_component = max(0, 25 - min(abs(velocity_change), 25))
        return round(stock_component + confidence_component + trend_component, 1)
