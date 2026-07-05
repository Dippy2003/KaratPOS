"""
Simple next-30-days sales forecast using a linear trend fit over the
last 90 days of actual daily sales (pandas). This is a lightweight
data-science bonus feature, not a production forecasting model --
it's a straight-line extrapolation intended to show a directional
trend on the Reports screen.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd

from app.services.report_service import get_date_range_sales_report


@dataclass(frozen=True)
class ForecastResult:
    historical: list[tuple[date, Decimal]]
    forecast: list[tuple[date, Decimal]]


def get_sales_forecast(history_days: int = 90, forecast_days: int = 30) -> ForecastResult:
    today = date.today()
    start = today - timedelta(days=history_days)
    report = get_date_range_sales_report(start, today)

    if len(report.daily_totals) < 2:
        # Not enough history to fit a trend -- flat forecast at the latest known value (or zero).
        last_value = report.daily_totals[-1][1] if report.daily_totals else Decimal("0")
        forecast = [(today + timedelta(days=i), last_value) for i in range(1, forecast_days + 1)]
        return ForecastResult(historical=report.daily_totals, forecast=forecast)

    df = pd.DataFrame(report.daily_totals, columns=["date", "total"])
    df["day_index"] = (df["date"] - df["date"].min()).apply(lambda d: d.days)

    x = df["day_index"].to_numpy(dtype=float)
    y = df["total"].astype(float).to_numpy()
    slope, intercept = np.polyfit(x, y, 1)

    last_index = int(df["day_index"].max())
    forecast = []
    for i in range(1, forecast_days + 1):
        predicted = max(slope * (last_index + i) + intercept, 0.0)
        forecast.append((today + timedelta(days=i), Decimal(str(round(predicted, 2)))))

    return ForecastResult(historical=report.daily_totals, forecast=forecast)
