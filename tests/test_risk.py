"""Risk measures on scenarios: premium, CFaR, buyer value, premia split, structures, tenor."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.pricing.risk import (
    buyer_value,
    cash_flow_at_risk,
    curtailment_value,
    level_shift,
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
    p = level_and_shape() + 30.0                       # no negative prices: curtailment idle
    q = np.tile(SOLAR, (400, 1))
    t = structure_table(p, q)
    assert list(t.index) == ["merchant", "merchant_no_curtailment", "pay_as_produced",
                             "pay_as_produced_clause", "pay_as_produced_deemed", "baseload"]
    # Same expected revenue at fair prices, very different risk.
    merchant = t.loc["merchant", "expected_revenue_eur"]
    for name in t.index:
        assert t.loc[name, "expected_revenue_eur"] == pytest.approx(merchant)
    assert t.loc["pay_as_produced", "cfar_eur"] == pytest.approx(0.0, abs=1e-6)  # fixed volumes
    assert t.loc["merchant", "cfar_eur"] > t.loc["baseload", "cfar_eur"]


def test_curtailing_keeps_the_value_a_plain_ppa_destroys():
    p = np.array([[-10.0, 50.0], [20.0, 40.0]])
    q = np.array([[2.0, 2.0], [2.0, 2.0]])
    t = structure_table(p, q)
    k = (p * q).sum() / q.sum()                        # 25.0: the park produces at -10
    assert t.loc["pay_as_produced", "fair_price_eur_mwh"] == pytest.approx(k)
    # stopping at -10 avoids a loss of 2 MWh x 10 EUR in scenario 1: +10 EUR on average
    gain = 10.0
    assert t.loc["merchant", "expected_revenue_eur"] == pytest.approx(
        t.loc["merchant_no_curtailment", "expected_revenue_eur"] + gain)
    # the clause pays only the 6 MWh produced at prices >= 0, at their own fair strike
    assert t.loc["pay_as_produced_clause", "fair_price_eur_mwh"] == pytest.approx(
        (100 + 40 + 80) / 6)
    assert t.loc["pay_as_produced_clause", "energy_share"] == pytest.approx(0.75)
    # deemed: the buyer curtails and pays all 8 MWh, the strike rises by the avoided loss
    assert t.loc["pay_as_produced_deemed", "fair_price_eur_mwh"] == pytest.approx(
        k + gain / 4)
    for name in ("pay_as_produced_clause", "pay_as_produced_deemed", "baseload"):
        assert t.loc[name, "expected_revenue_eur"] == pytest.approx(
            t.loc["merchant", "expected_revenue_eur"])
    # without curtailment the old set: no clause variants, the merchant produces
    old = structure_table(p, q, curtail_below=None)
    assert list(old.index) == ["merchant", "pay_as_produced", "baseload"]
    assert old.loc["merchant", "expected_revenue_eur"] == pytest.approx(
        t.loc["merchant_no_curtailment", "expected_revenue_eur"])


def test_curtailment_value_per_mwh_of_potential_output():
    p = np.array([[-10.0, 50.0], [20.0, 40.0]])
    q = np.array([[2.0, 2.0], [2.0, 2.0]])
    v = curtailment_value(p, q)
    assert v == {"share": 0.25, "mean_price": -10.0, "value": pytest.approx(20 / 8)}


def test_the_tenor_follows_the_delivered_volume():
    shares = {"level": [50.0, 100.0], "share": [0.6, 0.8]}
    t = tenor_price(fair_price=80.0, forward=100.0, energy_mwh=80.0, start_year=2027, years=2,
                    discount_rate=0.0, forward_curve={2028: 50.0}, volume_response=shares)
    assert t["energy_mwh"].tolist() == pytest.approx([80.0, 60.0])      # 80 x 0.6 / 0.8


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


RESPONSE = {"level": [50.0, 100.0, 200.0], "capture_rate": [0.40, 0.50, 0.60]}


def test_level_shift_interpolates_in_log_level_and_is_flat_beyond_the_ends():
    assert level_shift(None, 140.0, 90.0) == 0.0
    assert level_shift(RESPONSE, 100.0, 200.0) == pytest.approx(0.10)
    assert level_shift(RESPONSE, 100.0, 100.0 * 2 ** 0.5) == pytest.approx(0.05)   # half way in ln
    assert level_shift(RESPONSE, 200.0, 400.0) == 0.0
    assert level_shift(RESPONSE, 100.0, 25.0) == pytest.approx(-0.10)


def test_tenor_price_moves_the_capture_rate_with_the_forward_curve():
    t = tenor_price(fair_price=100.0, forward=200.0, energy_mwh=100.0, start_year=2027, years=3,
                    discount_rate=0.0, capture_rate_drift=-0.01,
                    forward_curve={2028: 100.0, 2029: 50.0}, level_response=RESPONSE)
    assert t["capture_rate"].tolist() == pytest.approx([0.50, 0.39, 0.28])
    assert t["fair_price_eur_mwh"].tolist() == pytest.approx([100.0, 39.0, 14.0])


def test_build_out_factors_scale_each_years_capture_rate():
    t = tenor_price(fair_price=50.0, forward=100.0, energy_mwh=100.0, start_year=2027, years=3,
                    discount_rate=0.0, capture_rate_drift=-0.01,
                    capture_rate_factors={2027: 1.0, 2028: 0.9, 2029: 0.8})
    assert t["capture_rate"].tolist() == pytest.approx([0.5, 0.45 - 0.01, 0.40 - 0.02])
