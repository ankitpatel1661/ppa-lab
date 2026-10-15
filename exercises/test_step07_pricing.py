"""Automatic checks for the Step 7 exercises. Run: .venv/bin/pytest exercises -q

Exercise 1 needs scenarios_2027.parquet (make scenarios); Exercises 2 and 3 need no data.
These tests live outside tests/, so CI does not run them.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step07_pricing as ex  # noqa: E402

needs_data = pytest.mark.skipif(
    not (ex.PROCESSED / "scenarios_2027.parquet").exists(),
    reason="scenario results missing: run `make scenarios` first",
)


@needs_data
def test_ex1_a_ppa_takes_most_of_the_risk_away():
    r = ex.cash_flow_at_risk(ex.load_scenarios(), "solar_park")
    assert r["merchant"] == pytest.approx(1_642_756, rel=1e-4)
    assert r["pay_as_produced"] == pytest.approx(454_373, rel=1e-4)


def test_ex2_ten_years_with_a_falling_capture_rate():
    assert ex.tenor_price(41.08, 85.42, 55_000, 2027, 10, 0.06, -0.01, 0.005) == pytest.approx(
        37.679, abs=1e-3)
    assert ex.tenor_price(41.08, 85.42, 55_000, 2027, 10, 0.06) == pytest.approx(41.08)


def test_ex3_the_hedge_shrinks_the_premium():
    p, q = ex.toy_market()
    assert ex.buyer_premium(p, q, hedge=False) == pytest.approx(28.610, abs=1e-3)
    assert ex.buyer_premium(p, q, hedge=True) == pytest.approx(9.644, abs=1e-3)
