"""Automatic checks for the Day 2 exercises. Run: .venv/bin/pytest exercises -q

These tests need the processed data (make all). They live outside tests/, so CI
does not run them: CI has no downloaded data.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import day02_capture as ex  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ex.PROCESSED / "power_hourly.parquet").exists(),
    reason="processed data missing: run `make all` first",
)


@pytest.fixture(scope="module")
def data():
    return ex.load_hourly_prices(), ex.load_hourly_power()


def test_ex1_solar_july_2024(data):
    # Official MW Solar July 2024 is 35.54 EUR/MWh; our generation data gives 35.82.
    assert ex.capture_price_month(*data, "solar_mw", 2024, 7) == pytest.approx(35.82, abs=0.01)


def test_ex1_wind_onshore_january_2025(data):
    assert ex.capture_price_month(*data, "wind_onshore_mw", 2025, 1) == pytest.approx(
        87.02, abs=0.01
    )


def test_ex2_solar_energy_at_negative_prices(data):
    assert ex.negative_price_energy_share(*data, "solar_mw", 2023) == pytest.approx(0.083, abs=1e-3)
    assert ex.negative_price_energy_share(*data, "solar_mw", 2025) == pytest.approx(
        0.2423, abs=1e-3
    )


def test_ex3_solar_profile_cost_tripled_from_2023_to_2025(data):
    cost_2023 = ex.profile_cost_eur_bn(*data, "solar_mw", 2023)
    cost_2025 = ex.profile_cost_eur_bn(*data, "solar_mw", 2025)
    assert cost_2023 == pytest.approx(1.236, abs=0.005)
    assert cost_2025 == pytest.approx(3.033, abs=0.005)
