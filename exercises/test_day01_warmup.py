"""Automatic checks for the Day 1 warm-up. Run: .venv/bin/pytest exercises -q

These tests need the processed data (make all). They live outside tests/, so CI
does not run them: CI has no downloaded data.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import day01_warmup as ex  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ex.PROCESSED / "prices_hourly.parquet").exists(),
    reason="processed data missing: run `make all` first",
)


@pytest.fixture(scope="module")
def hourly():
    return ex.load_hourly_prices()


def test_ex1_peak_base_2025(hourly):
    result = ex.peak_base(hourly, 2025)
    assert set(result) == {"base", "peak", "offpeak"}
    assert result["base"] == pytest.approx(89.32, abs=0.01)
    assert result["peak"] == pytest.approx(92.35, abs=0.01)
    assert result["offpeak"] == pytest.approx(87.64, abs=0.01)


def test_ex1_peak_premium_shrank_since_2023(hourly):
    r23, r25 = ex.peak_base(hourly, 2023), ex.peak_base(hourly, 2025)
    assert r23["peak"] - r23["base"] > 3 * (r25["peak"] - r25["base"])


def test_ex2_extreme_hours_2025(hourly):
    result = ex.extreme_hours(hourly, 2025)
    assert result["min_time"] == pd.Timestamp("2025-05-11 13:00", tz="Europe/Berlin")
    assert result["min_price"] == pytest.approx(-250.32, abs=0.01)
    assert result["max_time"] == pd.Timestamp("2025-01-20 17:00", tz="Europe/Berlin")
    assert result["max_price"] == pytest.approx(583.40, abs=0.01)


def test_ex3_solar_energy_2025():
    assert ex.solar_twh(ex.load_power_15min(), 2025) == pytest.approx(70.1, abs=0.05)
