"""Item 6: market values from the TSOs' extrapolation, and the cost of balancing."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.analysis.balancing import (
    bias_free,
    capture_prices,
    energy_mwh,
    imbalance_cost,
    imbalance_frame,
    quarter_hour_prices,
    window_cost,
)

TZ = "Europe/Berlin"


def quarter_hours(start, n):
    return pd.date_range(start, periods=n, freq="15min", tz="UTC")


def test_imbalance_cost_by_hand():
    idx = quarter_hours("2025-06-01 10:00", 4)
    actual = pd.Series([100.0, 100.0, 100.0, 100.0], index=idx)
    forecast = pd.Series([80.0, 120.0, 100.0, 100.0], index=idx)
    price = pd.Series(50.0, index=idx)
    short = pd.Series([90.0, 90.0, 0.0, 0.0], index=idx)     # paid when short
    long = pd.Series([20.0, 20.0, 0.0, 0.0], index=idx)      # received when long
    frame = imbalance_frame(actual, forecast, price, short, long, TZ, correct_bias=False)
    # long 20 MW for 15 min: sold 5 MWh at 20 instead of 50 -> 150 EUR lost;
    # short 20 MW: bought 5 MWh at 90 instead of 50 -> 200 EUR lost
    assert frame["cost_eur"].sum() == pytest.approx(350.0)
    cost = imbalance_cost(frame, TZ)
    assert cost.loc[2025, "cost_eur_mwh"] == pytest.approx(350.0 / 100.0)   # 100 MWh produced
    assert cost.loc[2025, "relative_error"] == pytest.approx(10.0 / 100.0)
    assert window_cost(frame, "2025-06-01", "2025-06-01", TZ) == pytest.approx(3.5)


def test_bias_is_removed_month_by_month():
    idx = quarter_hours("2025-01-31 22:00", 16)               # spans two local months
    actual = pd.Series(100.0, index=idx)
    forecast = pd.Series(110.0, index=idx)
    adjusted = bias_free(actual, forecast, TZ)
    np.testing.assert_allclose(adjusted.to_numpy(), 100.0)


def test_capture_prices_and_energy_at_any_resolution():
    hours = pd.date_range("2025-01-01", "2025-01-03", freq="1h", tz=TZ, inclusive="left")
    prices = pd.Series(np.where(hours.hour < 12, 20.0, 80.0), index=hours.tz_convert("UTC"))
    gen = pd.Series(np.where(hours.hour < 12, 3.0, 1.0), index=hours.tz_convert("UTC"))
    month = capture_prices(prices, gen, TZ, "M")
    assert month.iloc[0] == pytest.approx((3 * 20 + 1 * 80) / 4)
    quarter = pd.Series(10.0, index=pd.date_range("2025-01-01", periods=8, freq="15min",
                                                  tz="UTC"))
    assert energy_mwh(quarter, TZ).iloc[0] == pytest.approx(20.0)   # 2 hours at 10 MW


def test_hourly_prices_hold_for_their_quarter_hours():
    hourly = pd.Series([10.0, 20.0], index=pd.date_range("2025-01-01", periods=2, freq="1h",
                                                         tz="UTC"))
    grid = quarter_hours("2025-01-01", 8)
    assert quarter_hour_prices(hourly, grid).tolist() == [10.0] * 4 + [20.0] * 4
