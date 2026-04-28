from typing import List, Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models import ReorderRecommendation, SKU, Store, UrgencyLevel
from app.schemas import ReorderItem, ReorderSummary
from app.services.forecasting import ForecasterService


class ReorderService:
    def __init__(self, db: Session):
        self.db = db
        self.forecaster = ForecasterService(db)

    def generate_recommendations(
        self,
        user_id: int,
        store_id: str,
        horizon: int = 7,
        threshold_velocity_pct: float = 20.0,
    ) -> List[ReorderItem]:
        store = self.db.query(Store).filter(Store.user_id == user_id, Store.store_id == store_id).first()
        if not store:
            return []

        skus = self.db.query(SKU).filter(SKU.user_id == user_id, SKU.store_id == store.id).all()
        forecasts = self.forecaster.forecast_store(user_id=user_id, store_id=store_id, horizon=horizon)

        recommendations: List[ReorderItem] = []
        for sku in skus:
            forecast = forecasts.get(sku.sku_id)
            if not forecast:
                continue

            total_demand = sum(point.predicted_units for point in forecast["forecasts"])
            velocity_change = forecast.get("velocity_change", 0.0)
            reorder_qty, reason, urgency = self._calculate_reorder(
                forecasted_demand=total_demand,
                current_stock=sku.current_stock,
                velocity_change=velocity_change,
                threshold_velocity_pct=threshold_velocity_pct,
                horizon=horizon,
            )
            if reorder_qty <= 0:
                continue
            recommendations.append(
                ReorderItem(
                    sku_id=sku.sku_id,
                    sku_name=sku.sku_name,
                    reorder_qty=reorder_qty,
                    reason=reason,
                    urgency=urgency,
                    forecasted_demand=round(total_demand, 1),
                    current_stock=sku.current_stock,
                    velocity_change_pct=velocity_change,
                )
            )

        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda item: order.get(item.urgency, 4))
        return recommendations

    def _calculate_reorder(
        self,
        forecasted_demand: float,
        current_stock: int,
        velocity_change: float,
        threshold_velocity_pct: float,
        horizon: int,
    ) -> tuple[int, str, str]:
        safety_stock = int(forecasted_demand * (settings.SAFETY_STOCK_MULTIPLIER - 1))
        reorder_qty = max(0, int(forecasted_demand + safety_stock - current_stock))

        stock_coverage_days = float("inf")
        if forecasted_demand > 0:
            daily_demand = forecasted_demand / horizon
            stock_coverage_days = current_stock / daily_demand if daily_demand else float("inf")

        if current_stock == 0:
            return reorder_qty, "Out of stock. Immediate reorder needed.", UrgencyLevel.CRITICAL.value
        if stock_coverage_days < 3:
            return reorder_qty, f"Critical: only {stock_coverage_days:.1f} days of stock left.", UrgencyLevel.CRITICAL.value
        if stock_coverage_days < 7:
            return reorder_qty, f"Warning: only {stock_coverage_days:.1f} days of stock left.", UrgencyLevel.HIGH.value
        if velocity_change >= threshold_velocity_pct:
            return reorder_qty, f"{velocity_change:+.0f}% demand acceleration versus last week.", UrgencyLevel.HIGH.value
        if velocity_change >= threshold_velocity_pct / 2:
            return reorder_qty, f"{velocity_change:+.0f}% demand acceleration. Monitor closely.", UrgencyLevel.MEDIUM.value
        return reorder_qty, f"Baseline restock for the next {horizon} days.", UrgencyLevel.LOW.value

    def save_recommendations(self, user_id: int, store_id: str, recommendations: List[ReorderItem]) -> int:
        store = self.db.query(Store).filter(Store.user_id == user_id, Store.store_id == store_id).first()
        if not store:
            return 0

        self.db.query(ReorderRecommendation).filter(
            ReorderRecommendation.user_id == user_id,
            ReorderRecommendation.store_id == store.id,
            ReorderRecommendation.is_active.is_(True),
        ).update({"is_active": False}, synchronize_session=False)

        count = 0
        for rec in recommendations:
            sku = self.db.query(SKU).filter(SKU.user_id == user_id, SKU.store_id == store.id, SKU.sku_id == rec.sku_id).first()
            if not sku:
                continue
            self.db.add(
                ReorderRecommendation(
                    user_id=user_id,
                    store_id=store.id,
                    sku_id=sku.id,
                    reorder_qty=rec.reorder_qty,
                    reason=rec.reason,
                    urgency=rec.urgency,
                    forecasted_demand=rec.forecasted_demand,
                    current_stock=rec.current_stock,
                    safety_stock=int(rec.forecasted_demand * (settings.SAFETY_STOCK_MULTIPLIER - 1)),
                    velocity_change_pct=rec.velocity_change_pct,
                    is_active=True,
                )
            )
            count += 1

        self.db.commit()
        return count

    def get_summary(self, user_id: int, store_id: str) -> Optional[ReorderSummary]:
        store = self.db.query(Store).filter(Store.user_id == user_id, Store.store_id == store_id).first()
        if not store:
            return None

        recs = self.db.query(ReorderRecommendation).filter(
            ReorderRecommendation.user_id == user_id,
            ReorderRecommendation.store_id == store.id,
            ReorderRecommendation.is_active.is_(True),
        ).all()
        return ReorderSummary(
            total_items=len(recs),
            critical=sum(1 for rec in recs if rec.urgency == UrgencyLevel.CRITICAL.value),
            high=sum(1 for rec in recs if rec.urgency == UrgencyLevel.HIGH.value),
            medium=sum(1 for rec in recs if rec.urgency == UrgencyLevel.MEDIUM.value),
            low=sum(1 for rec in recs if rec.urgency == UrgencyLevel.LOW.value),
        )
