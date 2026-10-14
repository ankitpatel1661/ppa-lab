"""Shared test helpers.

Fixtures in tests/fixtures/ are REAL API responses (saved 7 Oct 2026), chosen
because they contain the hard cases:
  price_DE-LU_2025-09-30_2025-10-01.json  hourly -> 15-minute switch
  price_DE-LU_2025-03-30.json             spring DST day, 23 hourly prices
  price_DE-LU_2025-10-26.json             autumn DST day, 100 quarter-hours
  public_power_de_2025-03-30.json         generation on the spring DST day
Data licence: CC BY 4.0, Bundesnetzagentur | SMARD.de via Energy-Charts.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date
from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib
import pytest

from ppa_lab.config import Settings, load_settings
from ppa_lab.data.energy_charts import parse_price_payload
from ppa_lab.timeutils import local_dates

FIXTURES = Path(__file__).parent / "fixtures"
TZ = "Europe/Berlin"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Real project settings, but writing into a temporary folder."""
    base = load_settings()
    return dataclasses.replace(
        base,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        reports_dir=tmp_path / "reports",
    )


@pytest.fixture
def switch_prices() -> pd.DataFrame:
    """Real prices for 30 Sep (hourly) and 1 Oct 2025 (quarter-hourly)."""
    return parse_price_payload(load_fixture("price_DE-LU_2025-09-30_2025-10-01.json"))


def make_power_frame(start: date, end: date) -> pd.DataFrame:
    """Synthetic but physically plausible 15-minute generation for local days start..end."""
    first = pd.Timestamp(start).tz_localize(TZ)
    last = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(TZ)
    idx = pd.date_range(first, last, freq="15min", inclusive="left").tz_convert("UTC")
    idx.name = "ts_utc"
    hour = idx.tz_convert(TZ).hour + idx.tz_convert(TZ).minute / 60
    solar = np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None) * 30_000  # peak at 12:00 local
    return pd.DataFrame(
        {
            "solar_mw": solar,
            "wind_onshore_mw": 15_000.0,
            "wind_offshore_mw": 3_000.0,
            "load_mw": 55_000.0,
        },
        index=idx,
    )


def write_synthetic_market(settings) -> None:
    """Processed prices (hourly) and power (15 min) for 2024-2025: cheap middays."""
    power = make_power_frame(date(2024, 1, 1), date(2025, 12, 31))
    hourly = power.index[::4]  # synthetic power starts on a full hour
    hour = hourly.tz_convert(TZ).hour
    price = np.where((hour >= 10) & (hour < 16), -5.0, 90.0)
    price = price + np.random.default_rng(2024).normal(0.0, 8.0, len(hourly))  # some randomness
    prices = pd.DataFrame({"price_eur_mwh": price, "interval_min": 60.0}, index=hourly)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(settings.processed_dir / "prices_native.parquet")
    power.to_parquet(settings.processed_dir / "power_15min.parquet")


class FakeWeatherClient:
    """Synthetic ERA5-like data with the API's real conventions: radiation labelled at the
    END of its hour (clear sky 30 min before the label), wind and temperature as instants."""

    base_url = "https://fake.open-meteo.test/v1"

    def __init__(self):
        self.calls = []

    def hourly(self, latitude, longitude, start, end):
        self.calls.append((latitude, longitude, start, end))
        idx = pd.date_range(pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(hours=23),
                            freq="h", tz="UTC", name="ts_utc")
        clear = pvlib.location.Location(latitude, longitude).get_clearsky(
            idx - pd.Timedelta(minutes=30))
        hour = idx.hour.to_numpy()
        wind = 6.0 + 3.0 * np.sin(2 * np.pi * hour / 24)
        frame = pd.DataFrame({
            "ghi_w_m2": clear["ghi"].to_numpy(), "dni_w_m2": clear["dni"].to_numpy(),
            "dhi_w_m2": clear["dhi"].to_numpy(), "temp_air_c": 15.0,
            "wind_speed_10m_ms": wind * 0.7, "wind_speed_100m_ms": wind,
        }, index=idx)
        return frame, {"latitude": latitude, "longitude": longitude, "elevation_m": 50.0}

    def sleep(self, seconds):
        pass


class FakeClient:
    """Stands in for EnergyChartsClient: same methods, no network."""

    base_url = "https://fake.energy-charts.test"

    def __init__(self) -> None:
        self.calls: list[tuple[str, date, date]] = []
        self._prices = parse_price_payload(load_fixture("price_DE-LU_2025-09-30_2025-10-01.json"))

    def day_ahead_prices(self, bidding_zone: str, start: date, end: date) -> pd.DataFrame:
        self.calls.append(("prices", start, end))
        days = local_dates(self._prices.index, TZ)
        return self._prices[(days >= start) & (days <= end)]

    def public_power(self, country: str, start: date, end: date) -> pd.DataFrame:
        self.calls.append(("power", start, end))
        return make_power_frame(start, end)

    def sleep(self, seconds: float) -> None:  # no waiting in tests
        pass


# --------------------------------------------------------------------------- #
# Synthetic weather-driven market (Step 6 tests)
# --------------------------------------------------------------------------- #
WIND_RESPONSE, PHI_R, SIGMA_R = -1.5, 0.5, 0.1
SOLAR_CLIM = {m: 0.05 + 0.2 * np.sin(np.pi * (m - 0.5) / 12) for m in range(1, 13)}


def _ar1(phi: float, sigma: float, n: int, seed: int) -> np.ndarray:
    x = np.zeros(n)
    eps = np.random.default_rng(seed).normal(0, sigma, n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t]
    return x


def _midday_bump(hours: np.ndarray) -> np.ndarray:
    g = np.clip(np.cos(np.pi * (hours - 13) / 8), 0, None)
    return g - g.mean()


@cache
def weather_market() -> dict:
    """Three years (2023-2025) of synthetic daily weather and hourly prices with KNOWN links:
    the daily level falls by WIND_RESPONSE per unit of wind capacity factor above the month's
    mean, the rest of the daily level is an AR(1) (PHI_R, SIGMA_R), and sunshine above the
    month's normal deepens the midday dip. Also day x hour generation of both parks."""
    from ppa_lab.prices.model import fit, inverse

    idx = pd.date_range("2023-01-01", "2026-01-01", freq="h", tz=TZ, inclusive="left")
    idx = idx.tz_convert("UTC").rename("ts_utc")
    local = idx.tz_convert(TZ)
    codes, days = pd.factorize(local.normalize().tz_localize(None))
    days = pd.DatetimeIndex(days, name="day")
    rng = np.random.default_rng(31)
    clim_solar = np.array([SOLAR_CLIM[m] for m in days.month])
    wind = np.clip(0.3 + 0.12 * _ar1(0.6, 0.8, len(days), seed=32), 0.02, 0.95)
    solar = np.clip(clim_solar + rng.normal(0, 0.05, len(days)), 0.0, 0.6)
    temp = 10 + 8 * np.sin(2 * np.pi * (days.dayofyear - 110) / 365) + rng.normal(0, 2, len(days))
    features = pd.DataFrame({"solar": solar, "wind": wind, "temp": temp}, index=days)
    month_mean = features["wind"].groupby([days.year, days.month]).transform("mean").to_numpy()
    daily = WIND_RESPONSE * (wind - month_mean) + _ar1(PHI_R, SIGMA_R, len(days), seed=33)
    hours = local.hour.to_numpy()
    bump = _midday_bump(np.arange(24))[hours]
    y = (1.2 + 0.4 * np.sin(2 * np.pi * hours / 24) + daily[codes]
         - 4.0 * (solar - clim_solar)[codes] * bump + rng.normal(0, 0.05, len(idx)))
    prices = pd.Series(inverse(y, 50.0), index=idx, name="price_eur_mwh")

    shape = np.clip(np.sin(np.pi * (np.arange(24) - 6) / 14), 0, None)
    shape = shape / shape.mean()                         # daily mean 1
    generation = {
        "solar_park": pd.DataFrame(50.0 * solar[:, None] * shape[None, :], index=days,
                                   columns=range(24)),
        "wind_park": pd.DataFrame(np.repeat(30.0 * wind[:, None], 24, axis=1), index=days,
                                  columns=range(24)),
    }
    return {"prices": prices, "features": features, "generation": generation,
            "model": fit(prices, TZ, 50.0)}
