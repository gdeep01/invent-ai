import json
from typing import Iterable

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.auth import get_current_user, get_request_user
from app.core.security import decrypt_value
from app.models import ForecastResult, ForecastRun, ReorderRecommendation, SKU, Store, User, UserSettings, get_db
from app.schemas import AIChatRequest
from app.services.mandi_prices import MandiPriceService

router = APIRouter(dependencies=[Depends(get_current_user)])
public_router = APIRouter()

SYSTEM_PROMPT = (
    "You are InventAI Assistant, an expert inventory advisor for Indian retail stores (kirana shops). "
    "You help vendors understand and maximize their sales data with powerful features:\n\n"
    "AVAILABLE FEATURES:\n"
    "1. **Demand Forecasting** - Uses ARIMA models to predict future demand for any product\n"
    "2. **Reorder Recommendations** - Smart suggestions for when and how much to reorder based on demand patterns\n"
    "3. **Mandi Price Tracking** - Real-time market prices for commodities to help with procurement decisions\n"
    "4. **Stock Management** - Track inventory levels, identify slow-moving items, and optimize stock allocation\n"
    "5. **Profitability Analysis** - Analyze which products are most profitable and which need attention\n"
    "6. **Smart Alerts** - Get notified about low stock, unusual demand spikes, or price changes\n"
    "7. **Festival Planning** - Special forecasts during festive seasons for better inventory planning\n\n"
    "YOUR ROLE:\n"
    "- Help users understand how to use their sales data to improve inventory management\n"
    "- Explain which features would benefit them based on their situation\n"
    "- Provide actionable insights from their data\n"
    "- Guide them on next steps (forecasting, reordering, tracking prices)\n"
    "- Be conversational and use simple language (Hindi context when relevant)\n\n"
    "CONTEXT PROVIDED: User's current products, stock levels, active reorders, latest forecasts, and market prices.\n"
    "Always be encouraging and show how InventAI can help increase their profits!"
)


def _sse(chunks: Iterable[str]):
    for chunk in chunks:
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"


def _candidate_gemini_models() -> list[str]:
    candidates = [
        settings.GEMINI_MODEL,
        "gemini-2.5-flash",
        "gemini-2.5-flash-preview-09-2025",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
    ]
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _format_reorder_response(reorders: list[ReorderRecommendation], products: list[SKU]) -> str:
    if not reorders:
        if not products:
            return "I do not see product data yet. Upload sales data and run a forecast first, then I can show what to reorder this week."
        return "I do not see reorder suggestions yet. Run a forecast first, then I can show this week's reorder list."

    sku_lookup = {product.id: product for product in products}
    lines = ["These are the main items to reorder this week:"]
    for reorder in reorders[:5]:
        sku = sku_lookup.get(reorder.sku_id)
        sku_name = sku.sku_name if sku else f"SKU {reorder.sku_id}"
        lines.append(
            f"- {sku_name}: reorder {reorder.reorder_qty} units, urgency {reorder.urgency}, current stock {reorder.current_stock or 0}. {reorder.reason}"
        )
    if len(reorders) > 5:
        lines.append(f"- Plus {len(reorders) - 5} more recommended items in the reorder list.")
    return "\n".join(lines)


def _format_forecast_response(
    message: str,
    forecast_rows: list[ForecastResult],
    stores: dict[int, Store],
    products: list[SKU],
    latest_run: ForecastRun | None,
) -> str:
    if not forecast_rows:
        if latest_run:
            return f"The latest forecast run is {latest_run.status}, but I do not see saved forecast details yet."
        return "No forecast is ready yet. Run a forecast first and I can show next week's or next month's demand."

    requested_month = any(term in (message or "").lower() for term in ["next month", "month", "30 day", "30-day"])
    target_horizon = 30 if requested_month else None
    filtered_rows = [row for row in forecast_rows if target_horizon is None or row.forecast_horizon == target_horizon]
    used_fallback_horizon = False
    if not filtered_rows:
        filtered_rows = forecast_rows
        used_fallback_horizon = requested_month

    sku_lookup = {product.id: product for product in products}
    total_predicted = round(sum(row.predicted_units for row in filtered_rows), 1)
    horizon = filtered_rows[0].forecast_horizon if filtered_rows else (latest_run.horizon if latest_run else None)

    totals_by_sku: dict[int, float] = {}
    for row in filtered_rows:
        totals_by_sku[row.sku_id] = totals_by_sku.get(row.sku_id, 0.0) + row.predicted_units

    top_items = sorted(totals_by_sku.items(), key=lambda item: item[1], reverse=True)[:5]
    lines = []
    if used_fallback_horizon:
        lines.append(
            "I do not see a saved 30-day forecast yet, so I am showing the latest forecast available."
        )
    lines.append(f"For the next {horizon} days, expected total sales are {total_predicted} units.")
    if latest_run and latest_run.summary:
        lines.append(f"Latest run: {latest_run.summary}")
    if top_items:
        lines.append("Items likely to sell most:")
        for sku_db_id, predicted_total in top_items:
            sku = sku_lookup.get(sku_db_id)
            sku_name = sku.sku_name if sku else f"SKU {sku_db_id}"
            store_name = stores.get(sku.store_id).name if sku and stores.get(sku.store_id) else "Unknown store"
            lines.append(f"- {sku_name} ({store_name}): {round(predicted_total, 1)} units")
    return "\n".join(lines)


def _format_mandi_response(products: list[SKU], mandi_prices: list[dict]) -> str:
    if not mandi_prices:
        return "I could not find mandi price data right now, so I cannot tell which products are most affected."
    if not products:
        return "I do not see product data yet. Upload product or sales data first, then I can compare it with mandi items."

    matches = []
    for product in products:
        sku_name = (product.sku_name or "").lower()
        category = (product.category or "").lower()
        for mandi_row in mandi_prices:
            commodity = str(mandi_row.get("commodity", "")).strip()
            commodity_lower = commodity.lower()
            if not commodity_lower:
                continue
            if commodity_lower in sku_name or commodity_lower in category:
                matches.append((product, mandi_row))
                break

    if not matches:
        sample = ", ".join(str(row.get("commodity", "")).strip() for row in mandi_prices[:5] if row.get("commodity"))
        return (
            "I could not clearly match your products with the mandi items I have right now. "
            f"Available mandi items include: {sample}."
        )

    lines = ["These products look most affected by mandi price changes:"]
    for product, mandi_row in matches[:5]:
        commodity = mandi_row.get("commodity", "Unknown commodity")
        modal_price = mandi_row.get("modal_price", "N/A")
        market = mandi_row.get("market", "Unknown market")
        state = mandi_row.get("state", "Unknown state")
        lines.append(
            f"- {product.sku_name}: matched to {commodity}, modal mandi price {modal_price} at {market}, {state}."
        )
    if len(matches) > 5:
        lines.append(f"- Plus {len(matches) - 5} more product-to-commodity matches.")
    return "\n".join(lines)


def _format_festival_stock_response(
    forecast_rows: list[ForecastResult],
    products: list[SKU],
    stores: dict[int, Store],
    reorders: list[ReorderRecommendation],
) -> str:
    sku_lookup = {product.id: product for product in products}
    boosted_rows = [row for row in forecast_rows if row.festival_boost_applied]

    if boosted_rows:
        totals_by_sku: dict[int, float] = {}
        for row in boosted_rows:
            totals_by_sku[row.sku_id] = totals_by_sku.get(row.sku_id, 0.0) + row.predicted_units

        ranked = sorted(totals_by_sku.items(), key=lambda item: item[1], reverse=True)[:5]
        lines = ["For Diwali, these look like the best items to stock up on:"]
        for sku_db_id, predicted_total in ranked:
            sku = sku_lookup.get(sku_db_id)
            if not sku:
                continue
            store_name = stores.get(sku.store_id).name if stores.get(sku.store_id) else "Unknown store"
            lines.append(
                f"- {sku.sku_name} ({store_name}): forecast {round(predicted_total, 1)} units, current stock {sku.current_stock}."
            )
        return "\n".join(lines)

    if reorders:
        lines = ["I do not see festival-specific forecast boosts yet, but these reorder items are the best choices before Diwali:"]
        for reorder in reorders[:5]:
            sku = sku_lookup.get(reorder.sku_id)
            sku_name = sku.sku_name if sku else f"SKU {reorder.sku_id}"
            lines.append(
                f"- {sku_name}: reorder {reorder.reorder_qty} units, urgency {reorder.urgency}, current stock {reorder.current_stock or 0}."
            )
        return "\n".join(lines)

    low_stock = sorted(products, key=lambda product: product.current_stock)[:5]
    if low_stock:
        lines = ["I do not see festival-specific forecast boosts yet, so I would first check these low-stock products before Diwali:"]
        for product in low_stock:
            lines.append(f"- {product.sku_name}: {product.current_stock} units in stock")
        return "\n".join(lines)

    return "I do not have enough forecast or stock data yet to suggest what to stock up on before Diwali."


def _local_chat_fallback(
    message: str,
    products: list[SKU],
    reorders: list[ReorderRecommendation],
    latest_run: ForecastRun | None,
    forecast_rows: list[ForecastResult],
    stores: dict[int, Store],
    mandi_prices: list[dict],
) -> str:
    normalized = (message or "").lower()
    if any(term in normalized for term in ["diwali", "festival", "festive", "before diwali"]):
        return _format_festival_stock_response(forecast_rows, products, stores, reorders)
    if any(term in normalized for term in ["reorder", "restock", "order this week", "which items need"]):
        return _format_reorder_response(reorders, products)
    if "forecast" in normalized:
        return _format_forecast_response(message, forecast_rows, stores, products, latest_run)
    if any(term in normalized for term in ["mandi", "price change", "price changes", "commodity price", "market price"]):
        return _format_mandi_response(products, mandi_prices)
    if any(term in normalized for term in ["stock", "inventory", "top products"]):
        if not products:
            return "I do not see product data yet. Upload sales or product data first, then I can summarize current stock."
        lines = ["Here is a simple stock view:"]
        for product in products[:5]:
            lines.append(f"- {product.sku_name}: {product.current_stock} units in stock")
        return "\n".join(lines)
    return (
        "I can still help using your store data. "
        "Try asking about reorder items, demand forecast, stock levels, or mandi prices."
    )


@router.post("/chat")
@public_router.post("/chat")
def chat(payload: AIChatRequest, current_user: User = Depends(get_request_user), db: Session = Depends(get_db)):
    all_products = (
        db.query(SKU)
        .filter(SKU.user_id == current_user.id)
        .order_by(SKU.current_stock.desc())
        .all()
    )
    products = all_products[:10]
    reorders = (
        db.query(ReorderRecommendation)
        .filter(ReorderRecommendation.user_id == current_user.id, ReorderRecommendation.is_active.is_(True))
        .order_by(ReorderRecommendation.generated_at.desc())
        .limit(5)
        .all()
    )
    latest_run = db.query(ForecastRun).filter(ForecastRun.user_id == current_user.id).order_by(ForecastRun.created_at.desc()).first()
    forecast_rows = (
        db.query(ForecastResult)
        .filter(ForecastResult.user_id == current_user.id)
        .order_by(ForecastResult.generated_at.desc())
        .limit(5000)
        .all()
    )
    store_ids = {product.store_id for product in all_products}
    stores = {
        store.id: store
        for store in db.query(Store).filter(Store.id.in_(list(store_ids))).all()
    } if store_ids else {}
    mandi_prices = MandiPriceService().get_latest_prices()

    context = {
        "top_products": [{"sku_name": product.sku_name, "stock": product.current_stock} for product in products],
        "total_products": len(products),
        "recent_reorders": [{"reason": reorder.reason, "qty": reorder.reorder_qty} for reorder in reorders],
        "active_reorder_count": len(reorders),
        "latest_forecast_summary": latest_run.summary if latest_run else "No forecast run yet.",
        "current_mandi_prices": mandi_prices[:5] if mandi_prices else [],
        "available_features": {
            "forecasting": "ARIMA-based demand prediction for up to 30 days",
            "reorder_optimization": "Smart reorder quantity calculations",
            "mandi_prices": "Real-time market prices for procurement planning",
            "stock_alerts": "Low stock and anomaly alerts",
            "profitability": "Product-wise margin analysis",
            "festival_planning": "Special forecasts for festive seasons"
        }
    }

    settings_row = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    api_key = decrypt_value(settings_row.encrypted_gemini_api_key if settings_row else None) or settings.GEMINI_API_KEY
    if not api_key:
        fallback = _local_chat_fallback(payload.message, all_products, reorders, latest_run, forecast_rows, stores, mandi_prices)
        return StreamingResponse(_sse([fallback]), media_type="text/event-stream")

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{json.dumps(context, default=str)}\n\nUser: {payload.message}"
        last_error: Exception | None = None
        for model_name in _candidate_gemini_models():
            try:
                model = genai.GenerativeModel(model_name)
                stream = model.generate_content(prompt, stream=True)
                return StreamingResponse(_sse([chunk.text for chunk in stream if getattr(chunk, 'text', None)]), media_type="text/event-stream")
            except Exception as exc:
                last_error = exc
        raise last_error or RuntimeError("No Gemini model could be used.")
    except Exception as exc:
        fallback = _local_chat_fallback(payload.message, all_products, reorders, latest_run, forecast_rows, stores, mandi_prices)
        return StreamingResponse(_sse([fallback]), media_type="text/event-stream")


__all__ = ["router", "public_router"]
