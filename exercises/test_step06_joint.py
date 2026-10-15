"""Automatic checks for the Step 6 exercises. Run: .venv/bin/pytest exercises -q

These tests need the processed data (make all, including make weather and make scenarios).
They live outside tests/, so CI does not run them: CI has no downloaded data.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step06_joint as ex  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ex.PROCESSED / "scenarios_2027.parquet").exists(),
    reason="scenario results missing: run `make weather` and `make scenarios` first",
)


def test_ex1_wind_moves_the_daily_price():
    r = ex.wind_price_response(ex.load("prices_hourly"), ex.load("generation_wind_park"), 2025)
    assert r["eur_per_0.1_cf"] == pytest.approx(-6.644, abs=0.01)
    assert r["correlation"] == pytest.approx(-0.579, abs=0.002)


def test_ex2_analog_days_of_a_june_day():
    features = ex.daily_weather()
    target = pd.Timestamp("2025-06-15")
    assert ex.analog_days(features, target)[0] == target          # its own weather is nearest
    picks = ex.analog_days(features, target, exclude=8)
    assert [d.strftime("%Y-%m-%d") for d in picks] == [
        "2024-06-26", "2024-06-29", "2025-06-26", "2024-07-11", "2025-07-06"]


def test_ex3_fair_prices_with_and_without_the_weather_link():
    fair = ex.fair_prices(ex.load("scenarios_2027"))
    assert fair.loc["solar_park", "linked"] == pytest.approx(95.61, abs=0.01)
    assert fair.loc["wind_park", "independent"] == pytest.approx(145.43, abs=0.01)
    assert fair.loc["wind_park", "linked"] == pytest.approx(131.13, abs=0.01)
