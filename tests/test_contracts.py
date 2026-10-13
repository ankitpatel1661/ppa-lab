"""PPA cash flows to the producer, interval by interval.

Running example (four intervals, a solar-like profile that produces in cheap hours):
    prices P = [50, -10, 100, 20] EUR/MWh
    energy q = [ 2,   4,   0,  4] MWh
    merchant cash flows P*q = [100, -40, 0, 80] EUR, total 140; capture price 14 EUR/MWh;
    time-weighted base price = 40 EUR/MWh.
Every expected value below is worked out by hand in the comments.
"""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.pricing.contracts import (
    baseload,
    cfd,
    collar,
    discount_factors,
    fair_baseload_price,
    fair_pay_as_produced_price,
    merchant,
    pay_as_produced,
)

P = np.array([50.0, -10.0, 100.0, 20.0])
Q = np.array([2.0, 4.0, 0.0, 4.0])
RNG = np.random.default_rng(7)


# --------------------------------------------------------------------------- #
# Cash flows of each structure
# --------------------------------------------------------------------------- #
def test_merchant_sells_everything_at_spot():
    assert merchant(P, Q).tolist() == [100.0, -40.0, 0.0, 80.0]


def test_pay_as_produced_pays_the_strike_for_every_mwh():
    # 30 x q = [60, 120, 0, 120]
    assert pay_as_produced(P, Q, strike=30.0).tolist() == [60.0, 120.0, 0.0, 120.0]


def test_negative_price_clause_removes_payment_in_negative_intervals():
    # The 4 MWh at -10 EUR/MWh are not paid (and assumed curtailed): [60, 0, 0, 120].
    cash = pay_as_produced(P, Q, strike=30.0, pay_at_negative_prices=False)
    assert cash.tolist() == [60.0, 0.0, 0.0, 120.0]


def test_a_price_of_exactly_zero_is_not_negative():
    # EEG section 51 and typical clauses refer to prices BELOW zero; 0 EUR/MWh is still paid.
    cash = pay_as_produced(np.array([0.0, -0.01]), np.array([5.0, 5.0]), strike=30.0,
                           pay_at_negative_prices=False)
    assert cash.tolist() == [150.0, 0.0]


def test_cfd_removes_price_risk_whatever_the_prices():
    prices = RNG.normal(60, 80, size=(500, 96))  # 500 random price paths
    volumes = RNG.uniform(0, 10, size=(500, 96))
    np.testing.assert_allclose(cfd(prices, volumes, strike=42.0), 42.0 * volumes)


def test_floor_never_lowers_value():
    prices = RNG.normal(40, 120, size=(500, 96))
    volumes = RNG.uniform(0, 10, size=(500, 96))
    assert (collar(prices, volumes, floor=0.0) >= merchant(prices, volumes)).all()


def test_floor_cap_and_collar_on_the_running_example():
    # floor 0:        max(P, 0) * q   = [100, 0, 0, 80]
    # cap 40:         min(P, 40) * q  = [80, -40, 0, 80]
    # collar 0..40:   clip(P, 0, 40)*q = [80, 0, 0, 80]
    assert collar(P, Q, floor=0.0).tolist() == [100.0, 0.0, 0.0, 80.0]
    assert collar(P, Q, cap=40.0).tolist() == [80.0, -40.0, 0.0, 80.0]
    assert collar(P, Q, floor=0.0, cap=40.0).tolist() == [80.0, 0.0, 0.0, 80.0]


def test_collar_with_floor_equal_to_cap_is_a_cfd():
    np.testing.assert_allclose(collar(P, Q, floor=30.0, cap=30.0), cfd(P, Q, strike=30.0))


def test_collar_rejects_a_floor_above_the_cap():
    with pytest.raises(ValueError, match="floor"):
        collar(P, Q, floor=50.0, cap=40.0)


def test_baseload_is_merchant_plus_a_baseload_swap():
    # Band 2.5 MWh per interval at 40 EUR/MWh: 40*2.5 + (q - 2.5)*P = [75, 85, -150, 130],
    # which equals merchant [100, -40, 0, 80] + 2.5*(40 - P) = 2.5*[-10, 50, -60, 20].
    cash = baseload(P, Q, strike=40.0, band_mwh=2.5)
    assert cash.tolist() == [75.0, 85.0, -150.0, 130.0]
    np.testing.assert_allclose(cash, merchant(P, Q) + 2.5 * (40.0 - P))


def test_contracts_keep_the_pandas_index():
    idx = pd.date_range("2025-06-01", periods=4, freq="15min", tz="UTC", name="ts_utc")
    cash = pay_as_produced(pd.Series(P, index=idx), pd.Series(Q, index=idx), strike=30.0)
    assert isinstance(cash, pd.Series) and cash.index.equals(idx)


def test_contracts_refuse_series_on_different_time_grids():
    idx = pd.date_range("2025-06-01", periods=4, freq="15min", tz="UTC")
    shifted = idx + pd.Timedelta(hours=1)  # a time-zone bug would look like this
    with pytest.raises(ValueError, match="same time"):
        merchant(pd.Series(P, index=idx), pd.Series(Q, index=shifted))


# --------------------------------------------------------------------------- #
# Fair (break-even) prices
# --------------------------------------------------------------------------- #
def test_fair_pay_as_produced_price_is_the_capture_price():
    # 140 EUR / 10 MWh = 14 EUR/MWh
    assert fair_pay_as_produced_price(P, Q) == pytest.approx(14.0)


def test_fair_price_is_a_ratio_of_expectations_not_an_average_of_ratios():
    # Scenario A: 2 MWh at 10 -> 20 EUR. Scenario B: 6 MWh at 100 -> 600 EUR.
    # E[sum qP] / E[sum q] = 620 / 8 = 77.5, not the mean capture price (10 + 100) / 2 = 55.
    prices = np.array([[10.0, 10.0], [100.0, 100.0]])
    volumes = np.array([[1.0, 1.0], [3.0, 3.0]])
    assert fair_pay_as_produced_price(prices, volumes) == pytest.approx(77.5)


def test_discounting_weights_later_cash_flows_less():
    # D = [1, 1, 0.5, 0.5]: sum DqP = 100 - 40 + 0 + 40 = 100; sum Dq = 2 + 4 + 0 + 2 = 8.
    d = np.array([1.0, 1.0, 0.5, 0.5])
    assert fair_pay_as_produced_price(P, Q, discount=d) == pytest.approx(12.5)


def test_fair_baseload_price_is_the_time_weighted_base_price():
    # (50 - 10 + 100 + 20) / 4 = 40, whatever the band size
    assert fair_baseload_price(P) == pytest.approx(40.0)


def test_at_the_fair_price_every_structure_earns_the_merchant_revenue_in_total():
    merchant_total = merchant(P, Q).sum()
    k_pap = fair_pay_as_produced_price(P, Q)
    k_base = fair_baseload_price(P)
    assert pay_as_produced(P, Q, strike=k_pap).sum() == pytest.approx(merchant_total)
    assert baseload(P, Q, strike=k_base, band_mwh=Q.sum() / len(Q)).sum() == pytest.approx(
        merchant_total
    )


def test_discount_factors_compound_annually_from_the_valuation_date():
    t0 = pd.Timestamp("2025-01-01", tz="UTC")
    times = pd.DatetimeIndex([t0, t0 + pd.Timedelta(days=365.25), t0 + pd.Timedelta(days=730.5)])
    np.testing.assert_allclose(
        discount_factors(times, valuation=t0, rate=0.10), [1.0, 1 / 1.1, 1 / 1.21]
    )
