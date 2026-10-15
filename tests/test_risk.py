"""Risk measures on scenarios: premium, CFaR, buyer value, premia split, structures, tenor."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.pricing.risk import (
    buyer_value,
    cash_flow_at_risk,
    premium,
    risk_premia,
    structure_table,
    tenor_price,
)


def test_premium_and_cfar_by_hand():
    values = np.arange(1.0, 101.0)                    # 1 .. 100, mean 50.5
    q05 = np.quantile(values, 0.05)                   # 5.95 with linear interpolation
    assert cash_flow_at_risk(values) == pytest.approx(50.5 - q05)
    energy = np.full(100, 10.0)
    assert premium(values, energy) == pytest.approx((50.5 - q05) / 10.0)


SOLAR = np.clip(np.sin(2 * np.pi * (np.arange(48) - 6) / 24), 0, None)   # two sunny days


def level_and_shape(n_scen=400, seed=1):
    """Prices = scenario level + a midday dip whose depth differs between scenarios."""
    rng = np.random.default_rng(seed)
    level = 80.0 + 15.0 * rng.standard_normal((n_scen, 1))
    dip = 20.0 + 10.0 * rng.standard_normal((n_scen, 1))
    return level - dip * SOLAR[None, :]


def test_the_buyer_breaks_even_at_the_fair_price():
    p = level_and_shape()
    q = np.tile(SOLAR, (400, 1))
    k = (p * q).sum() / q.sum()
    assert buyer_value(p, q, k).mean() == pytest.approx(0.0, abs=1e-6)
    # the baseload hedge is fair too when struck at the average price
    f, band = p.mean(), q.sum(axis=1).mean() / p.shape[1]
    assert buyer_value(p, q, k, forward=f, band_mw=band).mean() == pytest.approx(0.0, abs=1e-6)


def test_a_baseload_hedge_removes_the_level_risk_of_flat_volumes():
    p = level_and_shape()
    flat = np.full_like(p, 5.0)
    premia = risk_premia(p, flat)
    assert premia["unhedged"] > 10.0                   # the level moves ±15 EUR/MWh
    assert premia["joint"] == pytest.approx(0.0, abs=1e-6)   # flat = baseload: fully hedged
    assert premia["profile"] == pytest.approx(0.0, abs=1e-6)


def test_profile_and_volume_parts_of_the_premium():
    p = level_and_shape()
    rng = np.random.default_rng(2)
    # Volumes scale with a weather factor that is NEGATIVELY related to the price level:
    # sunny scenarios are cheap ones.
    weather = 1.0 - 0.01 * (p[:, :1] - 80.0) + 0.05 * rng.standard_normal((400, 1))
    q = weather * SOLAR[None, :]
    premia = risk_premia(p, q)
    assert premia["profile"] > 0                       # deeper dips in some scenarios
    assert premia["volume"] == pytest.approx(premia["joint"] - premia["profile"])
    assert premia["volume"] > 0                        # more MWh exactly when they are cheap
    assert premia["fair_price"] == pytest.approx((p * q).sum() / q.sum())


def test_structures_move_risk_from_the_producer():
    p = level_and_shape() - 70.0                       # deep middays go negative
    q = np.tile(SOLAR, (400, 1))
    t = structure_table(p, q, floor=0.0)
    assert list(t.index) == ["merchant", "pay_as_produced", "pay_as_produced_clause",
                             "merchant_floor", "baseload"]
    # Same expected revenue at fair prices, very different risk.
    merchant = t.loc["merchant", "expected_revenue_eur"]
    assert t.loc["pay_as_produced", "expected_revenue_eur"] == pytest.approx(merchant)
    assert t.loc["baseload", "expected_revenue_eur"] == pytest.approx(merchant)
    assert t.loc["merchant_floor", "expected_revenue_eur"] == pytest.approx(merchant)
    assert t.loc["pay_as_produced", "cfar_eur"] == pytest.approx(0.0, abs=1e-6)  # fixed volumes
    assert t.loc["merchant", "cfar_eur"] > t.loc["baseload", "cfar_eur"]
    assert (p < 0).any() and t.loc["merchant_floor", "floor_value_eur_mwh"] > 0


def test_the_clause_costs_the_producer_the_output_at_negative_prices():
    p = np.array([[-10.0, 50.0], [20.0, 40.0]])
    q = np.array([[2.0, 2.0], [2.0, 2.0]])
    t = structure_table(p, q, floor=0.0)
    k = (p * q).sum() / q.sum()                        # 25.0
    # Clause at the same strike: nothing for the 2 MWh produced at -10 in scenario 1.
    expected = k * (2 + 4) / 2
    assert t.loc["pay_as_produced_clause", "expected_revenue_eur"] == pytest.approx(expected)
    assert t.loc["pay_as_produced_clause", "fair_price_eur_mwh"] == pytest.approx(k)


def test_tenor_price_with_flat_assumptions_is_the_one_year_price():
    years = tenor_price(fair_price=40.0, forward=85.0, energy_mwh=50_000.0, start_year=2027,
                        years=10, discount_rate=0.06)
    assert years.attrs["price"] == pytest.approx(40.0)
    assert list(years.index) == list(range(2027, 2037))


def test_tenor_price_follows_drift_degradation_and_discounting():
    t = tenor_price(fair_price=40.0, forward=80.0, energy_mwh=100.0, start_year=2027, years=2,
                    discount_rate=0.10, capture_rate_drift=-0.05, degradation=0.5)
    # capture rate 0.5 -> 0.45: prices 40 and 36; energy 100 and 50
    assert t["fair_price_eur_mwh"].tolist() == pytest.approx([40.0, 36.0])
    assert t["energy_mwh"].tolist() == pytest.approx([100.0, 50.0])
    d = 1.1 ** -np.array([0.5, 1.5])                    # discount at mid-year
    expected = (d * np.array([100.0, 50.0]) * np.array([40.0, 36.0])).sum() / (
        d * np.array([100.0, 50.0])).sum()
    assert t.attrs["price"] == pytest.approx(expected)


def test_tenor_price_can_follow_a_forward_curve():
    t = tenor_price(fair_price=40.0, forward=80.0, energy_mwh=100.0, start_year=2027, years=2,
                    discount_rate=0.0, forward_curve={2028: 100.0})
    assert t["forward_eur_mwh"].tolist() == [80.0, 100.0]
    assert t["fair_price_eur_mwh"].tolist() == pytest.approx([40.0, 50.0])  # same capture rate
    assert isinstance(t, pd.DataFrame)


def test_tenor_price_holds_the_last_quoted_year_flat():
    t = tenor_price(fair_price=40.0, forward=140.0, energy_mwh=100.0, start_year=2027, years=5,
                    discount_rate=0.0, forward_curve={2029: 90.0, 2028: 105.0})
    assert t["forward_eur_mwh"].tolist() == [140.0, 105.0, 90.0, 90.0, 90.0]
