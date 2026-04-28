from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.models import Base, ForecastRun, Store, User
from app.tasks import (
    _mark_forecast_run_failure,
    run_forecast_background,
)


def _build_session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_run_forecast_background_is_callable():
    assert callable(run_forecast_background)


def test_mark_forecast_run_failure_updates_status(monkeypatch):
    session_factory = _build_session_factory()
    session = session_factory()
    user = User(email="tasks@example.com", google_sub="tasks-sub", name="Tasks")
    session.add(user)
    session.flush()

    store = Store(user_id=user.id, store_id="STORE-1", name="Main Store")
    session.add(store)
    session.flush()

    forecast_run = ForecastRun(
        user_id=user.id,
        store_id=store.id,
        task_id="task-1",
        horizon=7,
        status="pending",
    )
    session.add(forecast_run)
    session.commit()
    forecast_run_id = forecast_run.id
    user_id = user.id
    session.close()

    monkeypatch.setattr("app.tasks.SessionLocal", session_factory)

    _mark_forecast_run_failure(user_id, forecast_run_id, "timed out")

    check_session = session_factory()
    updated_forecast_run = check_session.get(ForecastRun, forecast_run_id)
    assert updated_forecast_run.status == "failure"
    assert updated_forecast_run.error_message == "timed out"
    assert isinstance(updated_forecast_run.completed_at, datetime)
