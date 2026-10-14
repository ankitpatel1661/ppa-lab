"""The weather-price link: daily level responds to weather, intraday patterns from analog days.

Synthetic market with KNOWN effects: the daily level falls by 1.5 (transformed units) per
unit of wind capacity factor above the month's mean, the rest of the daily level is an
AR(1) with phi 0.5, and sunshine deepens the midday dip. The link must find them again.
"""

import numpy as np
import pandas as pd
import pytest

from conftest import PHI_R, SIGMA_R, WIND_RESPONSE, weather_market
from ppa_lab.scenarios.link import (
    analog_days,
    calibrate_linked_level,
    fit_link,
    restrict_pool,
    simulate_linked,
    weather_effect,
)
from ppa_lab.scenarios.weather import monthly_climatology

TZ = "Europe/Berlin"


def hourly(first_local: str, last_local_exclusive: str) -> pd.DatetimeIndex:
    idx = pd.date_range(first_local, last_local_exclusive, freq="h", tz=TZ, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


@pytest.fixture(scope="module")
def market():
    m = weather_market()
    link = fit_link(m["model"], m["prices"], m["features"],
                    monthly_climatology(m["features"], 2023, 2025), TZ, window_days=30, k=5)
    return m["prices"], m["features"], m["model"], link


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #
def test_link_recovers_the_wind_response(market):
    *_, link = market
    for season in ("winter", "spring", "summer", "autumn"):
        assert link.beta.loc[season, "wind"] == pytest.approx(WIND_RESPONSE, abs=0.2)
        assert link.beta.loc[season, "solar"] == pytest.approx(0.0, abs=0.3)  # no daily effect
    assert (link.r_squared > 0.3).all()


def test_link_keeps_the_memory_that_weather_does_not_explain(market):
    *_, link = market
    # Monthly demeaning biases phi down by about (1 + 3 phi) / 30.4 = 0.08 (Kendall).
    assert link.phi == pytest.approx(PHI_R - (1 + 3 * PHI_R) / 30.4, abs=0.07)
    assert float(link.sigma.mean()) == pytest.approx(SIGMA_R, abs=0.02)


def test_missing_weather_days_are_refused(market):
    prices, features, model, _ = market
    with pytest.raises(ValueError, match="weather"):
        fit_link(model, prices, features.iloc[10:], monthly_climatology(features, 2023, 2025), TZ)


# --------------------------------------------------------------------------- #
# Analog days
# --------------------------------------------------------------------------- #
def test_analog_days_are_the_nearest_within_the_seasonal_window(market):
    *_, link = market
    target = pd.Timestamp("2024-06-20")
    i = link.pool_days.get_loc(target)
    picks = analog_days(link, target, link.pool_features.iloc[i])
    assert picks[0] == i                                  # identical weather: itself is nearest
    assert len(picks) == link.k
    gap = np.abs(link.pool_days[picks].dayofyear - target.dayofyear)
    assert (np.minimum(gap, 365 - gap) <= link.window_days).all()


def test_analog_days_can_exclude_the_neighbourhood_of_the_target(market):
    *_, link = market
    target = pd.Timestamp("2024-06-20")
    i = link.pool_days.get_loc(target)
    picks = analog_days(link, target, link.pool_features.iloc[i], exclude_days=7)
    assert (np.abs((link.pool_days[picks] - target).days) > 7).all()


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def week_weather(features: pd.DataFrame, days: pd.DatetimeIndex, **shift) -> pd.DataFrame:
    """Climatological weather for the given days, shifted (e.g. wind=+0.2)."""
    clim = monthly_climatology(features, 2023, 2025)
    w = pd.DataFrame(clim.reindex(days.month).to_numpy(), index=days, columns=clim.columns)
    for name, value in shift.items():
        w[name] += value
    return w


def test_windy_weather_lowers_prices_in_a_future_year(market):
    _, features, model, link = market
    idx = hourly("2027-01-04", "2027-01-18")
    days = pd.date_range("2027-01-04", "2027-01-17", freq="D")
    calm = simulate_linked(model, link, idx, TZ, week_weather(features, days, wind=-0.15),
                           n_paths=200, annual_level=1.2, seed=4)
    windy = simulate_linked(model, link, idx, TZ, week_weather(features, days, wind=0.15),
                            n_paths=200, annual_level=1.2, seed=4)
    assert windy.mean() < calm.mean() - 10.0


def test_sunny_days_get_deeper_middays(market):
    _, features, model, link = market
    idx = hourly("2027-06-07", "2027-06-21")
    days = pd.date_range("2027-06-07", "2027-06-20", freq="D")
    hours = idx.tz_convert(TZ).hour
    midday = (hours >= 11) & (hours < 15)

    def midday_discount(weather):
        p = simulate_linked(model, link, idx, TZ, weather, n_paths=200, annual_level=1.2, seed=5)
        return p.mean() - p[:, midday].mean()

    sunny = midday_discount(week_weather(features, days, solar=0.12))
    cloudy = midday_discount(week_weather(features, days, solar=-0.12))
    assert sunny > cloudy + 5.0


def test_in_sample_effects_use_anomalies_within_the_month(market):
    # In-sample the fitted monthly levels already contain each month's average weather, so
    # only the deviation from the month's own mean may move the daily level.
    _, features, _, link = market
    days = pd.date_range("2024-03-01", "2024-03-31", freq="D")
    w = features.loc[days]
    base = weather_effect(link, w, in_sample=True)
    shifted = weather_effect(link, w.assign(wind=w["wind"] + 0.1), in_sample=True)
    np.testing.assert_allclose(shifted, base)
    future = weather_effect(link, w.assign(wind=w["wind"] + 0.1), in_sample=False)
    np.testing.assert_allclose(future - weather_effect(link, w, in_sample=False),
                               0.1 * link.beta.loc["spring", "wind"])


def test_linked_level_is_calibrated_to_the_forward_and_reproducible(market):
    _, features, model, link = market
    idx = hourly("2027-01-01", "2027-04-01")
    days = pd.date_range("2027-01-01", "2027-03-31", freq="D")
    w = week_weather(features, days)
    level = calibrate_linked_level(model, link, idx, TZ, w, target_price=85.0, n_paths=50, seed=6)
    a = simulate_linked(model, link, idx, TZ, w, n_paths=50, annual_level=level, seed=6)
    b = simulate_linked(model, link, idx, TZ, w, n_paths=50, annual_level=level, seed=6)
    assert a.mean() == pytest.approx(85.0, abs=0.05)
    np.testing.assert_array_equal(a, b)


def test_a_constant_feature_does_not_break_the_analog_search(market):
    # e.g. a site whose temperature series is flat: its standard deviation is 0.
    prices, features, model, _ = market
    flat = features.assign(temp=15.0)
    link = fit_link(model, prices, flat, monthly_climatology(flat, 2023, 2025), TZ, k=5)
    target = pd.Timestamp("2024-06-20")
    i = link.pool_days.get_loc(target)
    picks = analog_days(link, target, link.pool_features.iloc[i])
    assert picks[0] == i and len(picks) == 5


def test_the_analog_pool_can_be_restricted_to_recent_days(market):
    # Solar cannibalisation deepens year by year: recent days may represent a future
    # delivery year better than the whole calibration window.
    *_, link = market
    recent = restrict_pool(link, pd.Timestamp("2025-01-01"))
    assert recent.pool_days.min() >= pd.Timestamp("2025-01-01")
    n = len(recent.pool_days)
    assert recent.pool_features.shape[0] == n == len(recent.pool_xi) == recent.pool_u.shape[0]
    assert recent.phi == link.phi and len(link.pool_days) > n      # nothing else changes
