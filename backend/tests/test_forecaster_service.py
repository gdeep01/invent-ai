from datetime import datetime, timedelta

import pandas as pd

from app.services.forecasting.forecaster import ForecasterService


def _frame(days, start=10, step=1):
    today = datetime(2026, 1, 1)
    return pd.DataFrame(
        {
            "date": [today + timedelta(days=index) for index in range(days)],
            "units_sold": [start + (index * step) for index in range(days)],
        }
    )


def test_forecast_points_for_baseline_uses_baseline_label():
    service = ForecasterService(db=None)

    forecast_points, model_used = service._forecast_points_for_model(_frame(35), 5, "baseline")

    assert model_used == "baseline"
    assert len(forecast_points) == 5


def test_forecast_points_for_arima_path_reports_actual_model_used():
    service = ForecasterService(db=None)

    forecast_points, model_used = service._forecast_points_for_model(_frame(10), 5, "arima")

    assert len(forecast_points) == 5
    assert model_used == "naive"
