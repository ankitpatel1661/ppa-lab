"""Automatic checks for the Step 9 exercises. Run: .venv/bin/pytest exercises -q

Exercise 1 needs reports/results.json (committed), Exercise 2 the Step 6 scenario file.
These tests live outside tests/, so CI does not run them.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step09_memo as ex  # noqa: E402


def test_ex1_the_indicative_price_for_your_costs():
    results = ex.load_results()
    assert ex.indicative_price(results, "solar_park", 1.5, 1.0) == pytest.approx(
        results["parks"]["solar_park"]["stack_eur_mwh"]["indicative"])
    stack = results["parks"]["wind_park"]["stack_eur_mwh"]
    assert ex.indicative_price(results, "wind_park", 3.0, 2.0) == pytest.approx(
        stack["fair_price"] - stack["risk_premium"] - 5.0)


@pytest.mark.skipif(not (ex.PROCESSED / "scenarios_2027.parquet").exists(),
                    reason="scenario results missing: run `make scenarios` first")
def test_ex2_the_ppa_wins_about_half_of_the_years():
    table = ex.load_scenarios()
    assert ex.ppa_beats_merchant(table, "solar_park") == pytest.approx(0.5141, abs=1e-4)
    assert ex.ppa_beats_merchant(table, "wind_park") == pytest.approx(0.5121, abs=1e-4)
