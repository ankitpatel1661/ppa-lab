"""Automatic checks for the Step 4 exercises. Run: .venv/bin/pytest exercises -q

These tests need the processed data (make all, including make weather). They live
outside tests/, so CI does not run them: CI has no downloaded data.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step04_generation as ex  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ex.PROCESSED / "generation_solar_park.parquet").exists(),
    reason="generation data missing: run `make weather` first",
)


@pytest.fixture(scope="module")
def parks():
    return ex.load_generation("solar_park"), ex.load_generation("wind_park")


def test_ex1_specific_yield_2024(parks):
    solar, wind = parks
    assert ex.specific_yield(solar, ex.SOLAR_MWP, 2024) == pytest.approx(1141.2, abs=0.1)
    assert ex.specific_yield(wind, ex.WIND_MW, 2024) == pytest.approx(3691.5, abs=0.1)


def test_ex2_p50_p90_of_the_solar_park(parks):
    stats = ex.p50_p90(ex.annual_mwh(parks[0]).loc[1995:2025])
    assert stats["p50"] == pytest.approx(55098.8, abs=0.5)
    assert stats["p90"] == pytest.approx(51498.1, abs=0.5)


def test_ex3_portfolio_capture_rate(parks):
    prices = ex.load_hourly_prices()
    assert ex.portfolio_capture_rate(prices, *parks, 2025) == pytest.approx(0.7637, abs=1e-3)
