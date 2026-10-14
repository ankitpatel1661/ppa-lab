"""Automatic checks for the Step 8 exercises. Run: .venv/bin/pytest exercises -q

Exercise 1 needs the processed prices (make all); Exercises 2 and 3 need no data.
These tests live outside tests/, so CI does not run them.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step08_hedging as ex  # noqa: E402


@pytest.mark.skipif(not (ex.PROCESSED / "prices_hourly.parquet").exists(),
                    reason="processed prices missing: run `make all` first")
def test_ex1_a_hedge_wins_one_year_and_loses_the_next():
    prices = ex.load_hourly_prices()
    assert ex.hedge_pnl(prices, 2024, 5.0) == pytest.approx(731_857, abs=5)
    assert ex.hedge_pnl(prices, 2025, 5.0) == pytest.approx(-473_464, abs=5)


def test_ex2_minimum_variance_hedge():
    cash, payoff, average_mw = ex.toy_merchant()
    assert ex.min_variance_mw(cash, payoff) == pytest.approx(14.959, abs=1e-3)


def test_ex3_the_minimum_variance_hedge_is_the_most_effective():
    cash, payoff, average_mw = ex.toy_merchant()
    assert ex.effectiveness(cash, payoff, 0.0) == pytest.approx(0.0)
    assert ex.effectiveness(cash, payoff, average_mw) == pytest.approx(0.6713, abs=1e-4)
    assert ex.effectiveness(cash, payoff, 14.959) == pytest.approx(0.6725, abs=1e-4)
