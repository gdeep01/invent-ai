from datetime import datetime, timedelta

import pandas as pd

from app.services.forecasting.arima import ARIMAForecaster


def _frame(days, start=10, step=0):
    today = datetime(2026, 1, 1)
    return pd.DataFrame(
        {
            "date": [today + timedelta(days=index) for index in range(days)],
            "units_sold": [start + (index * step) for index in range(days)],
        }
    )


def test_arima_falls_back_to_naive_for_short_series():
    forecast = ARIMAForecaster(_frame(10)).forecast(7)
    assert len(forecast) == 7
    assert all(point.predicted_units >= 0 for point in forecast)


def test_arima_uses_moving_average_for_mid_length_series():
    forecaster = ARIMAForecaster(_frame(35, start=5, step=1))
    assert forecaster.get_model_used() == "moving_average"
    assert len(forecaster.forecast(5)) == 5


def test_arima_uses_arima_for_long_series_when_available():
    forecaster = ARIMAForecaster(_frame(80, start=8, step=1))
    result = forecaster.forecast(3)
    assert len(result) == 3
    assert forecaster.get_model_used() in {"arima", "moving_average"}
