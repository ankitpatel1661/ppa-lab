"""Weather inputs for the joint scenarios, per LOCAL day.

The weather of a day is summarised by three features that drive German prices:
- solar: the solar park's capacity factor (mean MW / capacity), a proxy for national PV;
- wind: the wind park's capacity factor, a proxy for national wind;
- temp: the mean 2 m temperature at the solar site (heating demand in winter).

Generation is kept as a matrix local day x local hour (24 columns), so that any weather
day can be placed on any delivery day, whatever the daylight-saving calendar.
"""

from __future__ import annotations

import calendar

import numpy as np
import pandas as pd

FEATURES = ("solar", "wind", "temp")


def _local_days(index: pd.DatetimeIndex, tz: str) -> pd.DatetimeIndex:
    return index.tz_convert(tz).normalize().tz_localize(None)


def daily_features(solar_mw: pd.Series, wind_mw: pd.Series, temp_c: pd.Series,
                   solar_capacity_mw: float, wind_capacity_mw: float, tz: str) -> pd.DataFrame:
    """Capacity factors of both parks and the mean temperature, one row per local day."""
    def per_day(series: pd.Series) -> pd.Series:
        return series.groupby(_local_days(series.index, tz)).mean()

    return pd.DataFrame({
        "solar": per_day(solar_mw) / solar_capacity_mw,
        "wind": per_day(wind_mw) / wind_capacity_mw,
        "temp": per_day(temp_c),
    }).dropna().rename_axis("day")


def monthly_climatology(features: pd.DataFrame, first_year: int, last_year: int) -> pd.DataFrame:
    """Average of each feature per calendar month (1-12) over the given weather years."""
    period = features.loc[str(first_year):str(last_year)]
    return period.groupby(period.index.month).mean().rename_axis("month")


def day_hour_matrix(values: pd.Series, tz: str) -> pd.DataFrame:
    """Hourly values as local day x local hour 0-23.

    A 25-hour day (October) averages its two 02:00 hours; a 23-hour day (March) gets its
    missing 02:00 by linear interpolation between 01:00 and 03:00.
    """
    local = values.index.tz_convert(tz)
    frame = pd.DataFrame({"v": values.to_numpy(), "day": local.normalize().tz_localize(None),
                          "hour": local.hour})
    matrix = frame.groupby(["day", "hour"])["v"].mean().unstack("hour")
    matrix = matrix.reindex(columns=range(24))
    return matrix.interpolate(axis=1, limit_direction="both").rename_axis("day")


def weather_days_for(delivery_days: pd.DatetimeIndex, weather_year: int) -> pd.DatetimeIndex:
    """The day of `weather_year` with the same calendar date as each delivery day.

    29 February of a leap delivery year uses 28 February when the weather year has none.
    """
    leap = calendar.isleap(weather_year)
    days = [pd.Timestamp(weather_year, m, 28 if (m == 2 and d == 29 and not leap) else d)
            for m, d in zip(delivery_days.month, delivery_days.day, strict=True)]
    return pd.DatetimeIndex(days)


def place_on_delivery_hours(matrix: pd.DataFrame, weather_days: pd.DatetimeIndex,
                            codes: np.ndarray, hours: np.ndarray) -> np.ndarray:
    """Hourly values for the delivery index: row `weather_days[code]`, column local hour."""
    rows = matrix.reindex(weather_days).to_numpy()
    if np.isnan(rows).any():
        raise ValueError("weather days missing from the generation matrix")
    return rows[codes, hours]
