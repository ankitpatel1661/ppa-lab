"""Weather -> power: a pvlib solar park and a windpowerlib wind park.

Solar uses the real ERA5 fixture (14-15 June 2025 at the solar site). Wind uses
hand-made wind speeds and the Vestas V126-3.45 power curve (rated at 12 m/s,
curve ends at 22.5 m/s).
"""

import math

import numpy as np
import pandas as pd
import pytest

from conftest import load_fixture
from ppa_lab.data.open_meteo import parse_hourly_payload, to_interval_beginning
from ppa_lab.weather.pv import solar_power_mw
from ppa_lab.weather.wind import hub_height_speed, shear_exponent, wind_power_mw

UTC = "UTC"
SOLAR = dict(latitude=51.75, longitude=14.25, capacity_mw=50.0, tilt_deg=25.0,
             azimuth_deg=180.0, dc_ac_ratio=1.2, losses_pct=10.0)


@pytest.fixture(scope="module")
def june_weather():
    raw, _ = parse_hourly_payload(load_fixture("open_meteo_era5_lusatia_2025-06-14_15.json"))
    return to_interval_beginning(raw)


# --------------------------------------------------------------------------- #
# Solar
# --------------------------------------------------------------------------- #
def test_solar_is_zero_at_night_and_never_above_the_inverter_limit(june_weather):
    mw = solar_power_mw(june_weather, **SOLAR)
    assert mw.index.equals(june_weather.index)
    assert mw[pd.Timestamp("2025-06-15 00:00", tz=UTC)] == 0.0   # 02:00 local, dark
    assert mw.max() <= 50.0 / 1.2 + 1e-9                         # AC limit 41.7 MW


def test_solar_produces_most_of_its_ac_capacity_on_a_sunny_june_noon(june_weather):
    # Row 10:00 UTC = 12:00-13:00 local, GHI about 750 W/m2.
    noon = solar_power_mw(june_weather, **SOLAR)[pd.Timestamp("2025-06-15 10:00", tz=UTC)]
    assert 0.5 * 50 / 1.2 < noon <= 50 / 1.2


def test_solar_scales_with_capacity(june_weather):
    small = solar_power_mw(june_weather, **SOLAR)
    big = solar_power_mw(june_weather, **{**SOLAR, "capacity_mw": 100.0})
    np.testing.assert_allclose(big, 2 * small)


def test_hotter_modules_produce_less(june_weather):
    hot = june_weather.assign(temp_air_c=june_weather["temp_air_c"] + 20.0)
    t = pd.Timestamp("2025-06-15 09:00", tz=UTC)  # strong sun, below the inverter limit
    assert solar_power_mw(hot, **SOLAR)[t] < solar_power_mw(june_weather, **SOLAR)[t]


# --------------------------------------------------------------------------- #
# Wind
# --------------------------------------------------------------------------- #
def test_shear_exponent_from_two_heights():
    # alpha = ln(7.5 / 5) / ln(100 / 10) = ln(1.5) / ln(10) = 0.176091
    assert shear_exponent(np.array([5.0]), np.array([7.5]))[0] == pytest.approx(0.176091, abs=1e-6)


def test_hub_height_speed_extrapolates_with_the_power_law():
    # 7.5 * (137 / 100) ** 0.176091 = 7.9275
    v = hub_height_speed(np.array([5.0]), np.array([7.5]), hub_height_m=137.0)
    assert v[0] == pytest.approx(7.9275, abs=1e-3)


def test_shear_is_clipped_to_a_physical_range():
    # Faster at 10 m than at 100 m (alpha < 0) -> 0: no extrapolation downwards.
    assert hub_height_speed(np.array([8.0]), np.array([6.0]), 137.0)[0] == pytest.approx(6.0)
    # Calm at 10 m (alpha -> infinity) -> capped at 0.6.
    v = hub_height_speed(np.array([0.0]), np.array([6.0]), 137.0)[0]
    assert v == pytest.approx(6.0 * 1.37 ** 0.6)


def test_wind_power_follows_the_power_curve_with_losses():
    # Equal speeds at 10 m and 100 m -> no shear: hub speed = 100 m speed.
    speeds = [2.0, 12.5, 15.0, 25.0]
    idx = pd.date_range("2025-01-01", periods=4, freq="h", tz=UTC, name="ts_utc")
    weather = pd.DataFrame({"wind_speed_10m_ms": speeds, "wind_speed_100m_ms": speeds}, index=idx)
    mw = wind_power_mw(weather, capacity_mw=30.0, turbine_type="V126/3450",
                       hub_height_m=137.0, losses_pct=12.0)
    # below cut-in: 0; above rated (12 m/s): 30 MW x (1 - 0.12) = 26.4; above cut-out: 0
    assert mw.tolist() == pytest.approx([0.0, 26.4, 26.4, 0.0])


def test_wind_power_rises_between_cut_in_and_rated():
    speeds = np.arange(3.0, 12.5, 0.5)
    idx = pd.date_range("2025-01-01", periods=len(speeds), freq="h", tz=UTC, name="ts_utc")
    weather = pd.DataFrame({"wind_speed_10m_ms": speeds, "wind_speed_100m_ms": speeds}, index=idx)
    mw = wind_power_mw(weather, 30.0, "V126/3450", 137.0, 12.0)
    assert (np.diff(mw.to_numpy()) >= 0).all() and not math.isclose(mw.iloc[0], mw.iloc[-1])
