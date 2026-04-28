from fastapi import APIRouter

from app.api.routers.ai import public_router as public_ai_router, router as ai_router
from app.api.routers.alerts import router as alerts_router
from app.api.routers.auth import router as auth_router
from app.api.routers.forecast import public_router as public_forecast_router, router as forecast_router
from app.api.routers.health import router as health_router
from app.api.routers.mandi import router as mandi_router
from app.api.routers.products import public_router as public_products_router, router as products_router
from app.api.routers.reorder import public_router as public_reorder_router, router as reorder_router
from app.api.routers.settings import router as settings_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(health_router, tags=["system"])
api_router.include_router(public_products_router, prefix="/products", tags=["products"])
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(public_forecast_router, prefix="/forecast", tags=["forecast"])
api_router.include_router(forecast_router, prefix="/forecast", tags=["forecast"])
api_router.include_router(public_reorder_router, prefix="/reorder", tags=["reorder"])
api_router.include_router(reorder_router, prefix="/reorder", tags=["reorder"])
api_router.include_router(mandi_router, prefix="/mandi", tags=["mandi"])
api_router.include_router(public_ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])

__all__ = ["api_router"]
