from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers.forecast import validate_forecast_request
from app.models.models import Base, SKU, SalesTransaction, Store, User
from app.schemas import ForecastRequest


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    return session


def _seed_store_with_sales(session, days: int):
    user = User(email=f"user-{days}@example.com", google_sub=f"sub-{days}", name="Tester")
    session.add(user)
    session.flush()

    store = Store(user_id=user.id, store_id="STORE-1", name="Main Store")
    session.add(store)
    session.flush()

    sku = SKU(user_id=user.id, store_id=store.id, sku_id="SKU-1", sku_name="Rice")
    session.add(sku)
    session.flush()

    start = date(2026, 1, 1)
    session.add_all(
        [
            SalesTransaction(
                user_id=user.id,
                store_id=store.id,
                sku_id=sku.id,
                date=start + timedelta(days=offset),
                units_sold=10 + offset,
                excluded_from_forecast=False,
            )
            for offset in range(days)
        ]
    )
    session.commit()
    session.refresh(user)
    return user, store


def test_validate_forecast_request_rejects_short_arima_history():
    session = _build_session()
    user, _ = _seed_store_with_sales(session, days=12)

    payload = ForecastRequest(store_id="STORE-1", horizon=7, model="arima")

    with pytest.raises(HTTPException) as exc_info:
        validate_forecast_request(session, user, payload)

    assert exc_info.value.status_code == 422
    assert "Use the baseline model instead" in exc_info.value.detail


def test_validate_forecast_request_allows_baseline_with_short_history():
    session = _build_session()
    user, store = _seed_store_with_sales(session, days=12)

    payload = ForecastRequest(store_id="STORE-1", horizon=7, model="baseline")

    validated_store = validate_forecast_request(session, user, payload)

    assert validated_store.id == store.id


def test_validate_forecast_request_allows_arima_with_enough_history():
    session = _build_session()
    user, store = _seed_store_with_sales(session, days=60)

    payload = ForecastRequest(store_id="STORE-1", horizon=7, model="arima")

    validated_store = validate_forecast_request(session, user, payload)

    assert validated_store.id == store.id
