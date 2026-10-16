"""The EEG market premium as a strip of puts on the market value (roadmap item 5)."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.pricing.eeg import basis_ratio, eeg_revenue, market_premium, month_codes

# One scenario, four hours: two in January, two in February.
MONTHS = np.array([1, 1, 2, 2])
PRICES = np.array([[40.0, 60.0, 100.0, 120.0]])
VOLUMES = np.array([[3.0, 1.0, 2.0, 2.0]])


def test_the_premium_is_a_put_on_each_months_market_value():
    # January market value (3x40 + 1x60) / 4 = 45: premium (70 - 45) x 4 MWh = 100
    # February 110: above the award, no premium
    assert market_premium(PRICES, VOLUMES, MONTHS, 70.0)[0] == pytest.approx(100.0)
    # the basis scales the market value: January 0.9 x 45 = 40.5 -> (70 - 40.5) x 4 = 118
    assert market_premium(PRICES, VOLUMES, MONTHS, 70.0, basis=0.9)[0] == pytest.approx(118.0)


def test_one_annual_put_is_worth_less_than_twelve_monthly_ones():
    # annual market value (120 + 60 + 200 + 240) / 8 = 77.5 > 70: nothing
    assert market_premium(PRICES, VOLUMES, MONTHS, 70.0, reference="year")[0] == 0.0
    rng = np.random.default_rng(1)
    p = rng.normal(70, 30, (200, 24))
    q = rng.uniform(0, 2, (200, 24))
    months = np.repeat(np.arange(1, 13), 2)
    monthly = market_premium(p, q, months, 70.0, curtail_below=None)
    annual = market_premium(p, q, months, 70.0, reference="year", curtail_below=None)
    assert (monthly >= annual - 1e-9).all() and monthly.mean() > annual.mean()


def test_no_premium_and_no_output_at_negative_prices():
    p = np.array([[-10.0, 30.0]])
    q = np.array([[2.0, 2.0]])
    months = np.array([1, 1])
    # market value (-20 + 60) / 4 = 10 on all output; premium on the 2 MWh sold at 30 only
    assert market_premium(p, q, months, 50.0)[0] == pytest.approx(40.0 * 2)
    assert eeg_revenue(p, q, months, 50.0)[0] == pytest.approx(30.0 * 2 + 80.0)
    assert market_premium(p, q, months, 50.0, curtail_below=None)[0] == pytest.approx(40.0 * 4)


def test_reference_must_be_month_or_year():
    with pytest.raises(ValueError, match="month"):
        market_premium(PRICES, VOLUMES, MONTHS, 70.0, reference="quarter")


def test_basis_ratio_compares_the_official_value_with_the_parks_capture_price():
    idx = pd.date_range("2025-01-01", "2025-03-01", freq="h", tz="Europe/Berlin",
                        inclusive="left").tz_convert("UTC")
    prices = pd.Series(100.0, index=idx)
    generation = pd.Series(5.0, index=idx)
    official = pd.Series([95.0, 90.0], index=pd.PeriodIndex(["2025-01", "2025-02"], freq="M"))
    b = basis_ratio(official, prices, generation, "Europe/Berlin")
    assert b["months"] == 2 and b["mean"] == pytest.approx(0.925)
    assert basis_ratio(official, prices, generation, "Europe/Berlin", "2025-02")["mean"] == 0.9
    assert list(np.unique(month_codes(idx, "Europe/Berlin"))) == [1, 2]
