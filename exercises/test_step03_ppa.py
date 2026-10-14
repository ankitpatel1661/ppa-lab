"""Automatic checks for the Step 3 exercises. Run: .venv/bin/pytest exercises -q

These tests need the processed data (make all). They live outside tests/, so CI
does not run them: CI has no downloaded data.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step03_ppa as ex  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ex.PROCESSED / "power_hourly.parquet").exists(),
    reason="processed data missing: run `make all` first",
)


@pytest.fixture(scope="module")
def data():
    return ex.load_hourly_prices(), ex.load_hourly_power()


def test_ex1_baseload_ppa_2025(data):
    # Solar lost against merchant (about 46) although the strike was "the base price".
    assert ex.baseload_revenue_per_mwh(*data, "solar_mw", 2025, 78.51) == pytest.approx(
        35.25, abs=0.01
    )
    assert ex.baseload_revenue_per_mwh(*data, "wind_onshore_mw", 2025, 78.51) == pytest.approx(
        66.46, abs=0.01
    )


def test_ex2_floor_values_2025(data):
    assert ex.floor_value_per_mwh(*data, "solar_mw", 2025, 0.0) == pytest.approx(3.30, abs=0.01)
    assert ex.floor_value_per_mwh(*data, "solar_mw", 2025, 20.0) == pytest.approx(10.70, abs=0.01)
    assert ex.floor_value_per_mwh(*data, "wind_onshore_mw", 2025, 0.0) == pytest.approx(
        0.44, abs=0.01
    )


def test_ex3_clause_raises_the_breakeven_strike(data):
    assert ex.breakeven_strike_with_clause(*data, "solar_mw", 2025) == pytest.approx(
        60.80, abs=0.01
    )
    assert ex.breakeven_strike_with_clause(*data, "wind_onshore_mw", 2025) == pytest.approx(
        83.68, abs=0.01
    )
