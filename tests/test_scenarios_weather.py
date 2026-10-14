"""Weather helpers for the joint scenarios: daily features, day x hour matrices, calendars."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.scenarios.weather import (
    FEATURES,
    daily_features,
    day_hour_matrix,
    monthly_climatology,
    weather_days_for,
)

TZ = "Europe/Berlin"


def hourly(first_local: str, last_local_exclusive: str) -> pd.DatetimeIndex:
    idx = pd.date_range(first_local, last_local_exclusive, freq="h", tz=TZ, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


def test_daily_features_are_capacity_factors_and_mean_temperature_per_local_day():
    idx = hourly("2025-06-01", "2025-06-03")
    solar = pd.Series(np.where(idx.tz_convert(TZ).day == 1, 10.0, 20.0), index=idx)
    wind = pd.Series(15.0, index=idx)
    temp = pd.Series(np.where(idx.tz_convert(TZ).day == 1, 12.0, 18.0), index=idx)
    f = daily_features(solar, wind, temp, solar_capacity_mw=50.0, wind_capacity_mw=30.0, tz=TZ)
    assert list(f.columns) == list(FEATURES)
    assert list(f.index) == [pd.Timestamp("2025-06-01"), pd.Timestamp("2025-06-02")]
    assert f["solar"].tolist() == pytest.approx([0.2, 0.4])   # mean MW / capacity
    assert f["wind"].tolist() == pytest.approx([0.5, 0.5])
    assert f["temp"].tolist() == pytest.approx([12.0, 18.0])


def test_daily_features_use_local_days_across_daylight_saving():
    idx = hourly("2025-03-29", "2025-04-01")                  # 30 March has 23 local hours
    f = daily_features(pd.Series(5.0, index=idx), pd.Series(3.0, index=idx),
                       pd.Series(1.0, index=idx), 50.0, 30.0, TZ)
    assert len(f) == 3 and f["solar"].tolist() == pytest.approx([0.1] * 3)


def test_day_hour_matrix_handles_23_and_25_hour_days():
    idx = hourly("2025-03-30", "2025-03-31")                  # 23 hours: 02:00 does not exist
    local = idx.tz_convert(TZ)
    m = day_hour_matrix(pd.Series(local.hour.astype(float), index=idx), TZ)
    assert m.shape == (1, 24)
    assert m.loc[pd.Timestamp("2025-03-30"), 2] == pytest.approx(2.0)   # filled between 1 and 3

    idx = hourly("2025-10-26", "2025-10-27")                  # 25 hours: 02:00 twice
    values = pd.Series(np.arange(len(idx), dtype=float), index=idx)    # 0, 1, 2, 3, ...
    m = day_hour_matrix(values, TZ)
    assert m.loc[pd.Timestamp("2025-10-26"), 2] == pytest.approx(2.5)  # mean of both 02:00 hours
    assert m.loc[pd.Timestamp("2025-10-26"), 3] == pytest.approx(4.0)


def test_weather_days_keep_the_calendar_date_and_map_29_february():
    delivery = pd.DatetimeIndex(["2028-02-28", "2028-02-29", "2028-03-01"])   # 2028 is leap
    assert list(weather_days_for(delivery, 2001)) == [
        pd.Timestamp("2001-02-28"), pd.Timestamp("2001-02-28"), pd.Timestamp("2001-03-01")]
    delivery = pd.DatetimeIndex(["2027-02-28", "2027-03-01"])
    assert list(weather_days_for(delivery, 2004)) == [
        pd.Timestamp("2004-02-28"), pd.Timestamp("2004-03-01")]   # 29 Feb 2004 is unused


def test_monthly_climatology_averages_only_the_chosen_years():
    days = pd.date_range("2020-01-01", "2022-12-31", freq="D")
    f = pd.DataFrame({"solar": np.where(days.year == 2022, 9.0, 1.0), "wind": 0.3, "temp": 5.0},
                     index=days)
    clim = monthly_climatology(f, 2020, 2021)
    assert clim.shape == (12, 3)
    assert clim["solar"].tolist() == pytest.approx([1.0] * 12)
