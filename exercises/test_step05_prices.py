"""Automatic checks for the Step 5 exercises. Run: .venv/bin/pytest exercises -q

Exercises 1 and 3 need the processed prices (make all). Exercise 2 needs no data. These
tests live outside tests/, so CI does not run them: CI has no downloaded data.
"""

import sys
from functools import cache
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import step05_prices as ex  # noqa: E402

needs_data = pytest.mark.skipif(
    not (ex.PROCESSED / "prices_hourly.parquet").exists(),
    reason="processed prices missing: run `make all` first",
)


@pytest.fixture(scope="module")
def prices():
    return ex.load_hourly_prices()


@needs_data
def test_ex1_daily_mean_reversion_2024(prices):
    r = ex.daily_ar1(prices, ex.SCALE, 2024)
    assert r["phi"] == pytest.approx(0.5406, abs=1e-3)
    assert r["half_life_days"] == pytest.approx(1.127, abs=0.01)


@cache
def simulated():
    """Called inside each test (not a fixture), so an unsolved stub shows as not solved."""
    return ex.simulate_ar1(0.5, 0.2, n_days=365, n_paths=2000, seed=1)


def test_ex2_shape_and_reproducibility():
    paths = simulated()
    assert paths.shape == (2000, 365)
    np.testing.assert_array_equal(paths, ex.simulate_ar1(0.5, 0.2, 365, 2000, seed=1))
    assert not np.array_equal(paths, ex.simulate_ar1(0.5, 0.2, 365, 2000, seed=2))


def test_ex2_long_run_variance_and_persistence():
    paths = simulated()
    stationary = 0.2**2 / (1 - 0.5**2)
    assert paths.var() == pytest.approx(stationary, rel=0.05)
    lag1 = np.mean([np.corrcoef(row[1:], row[:-1])[0, 1] for row in paths])
    assert lag1 == pytest.approx(0.5, abs=0.02)


def test_ex2_first_day_is_already_stationary():
    assert simulated()[:, 0].var() == pytest.approx(0.2**2 / (1 - 0.5**2), rel=0.1)


@needs_data
def test_ex3_level_for_an_85_forward(prices):
    shape = ex.shape_of_year(prices, ex.SCALE, 2025)
    level = ex.level_for_forward(shape, ex.SCALE, 85.0)
    assert level == pytest.approx(0.63054, abs=1e-4)
    assert (ex.SCALE * np.sinh(level + shape)).mean() == pytest.approx(85.0, abs=1e-3)
