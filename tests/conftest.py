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
from pathlib import Path

import numpy as np
import pandas as pd
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
