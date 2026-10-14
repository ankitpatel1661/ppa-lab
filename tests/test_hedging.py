"""Hedging with power futures: products, forwards, minimum-variance hedges, back-test."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.hedging.hedge import (
    backtest_hedge,
    buyer_hedge,
    hedge_payoffs,
    hedge_strategies,
    min_variance_hedge,
    model_forwards,
)
from ppa_lab.hedging.products import product_masks

TZ = "Europe/Berlin"


def year_index(year: int) -> pd.DatetimeIndex:
    idx = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", tz=TZ, inclusive="left")
    return idx.tz_convert("UTC")


def test_products_cover_the_delivery_hours():
    m = product_masks(year_index(2027), TZ)
    assert m["cal_base"].sum() == 8760
    # EEX peak: Monday to Friday 08:00-20:00 local, holidays included. 2027 has 261 weekdays.
    assert m["cal_peak"].sum() == 261 * 12
    assert sum(m[f"Q{q}"].sum() for q in range(1, 5)) == 8760
    assert sum(m[f"M{k:02d}"].sum() for k in range(1, 13)) == 8760
    assert m["M03"].sum() == 31 * 24 - 1                 # the spring DST day has 23 hours
    local = year_index(2027).tz_convert(TZ)
    peak_hours = set(local[m["cal_peak"] & (local.date == pd.Timestamp("2027-06-02").date())].hour)
    assert peak_hours == set(range(8, 20))              # Wednesday: 08:00 in, 20:00 out
    assert not m["cal_peak"][local.date == pd.Timestamp("2027-06-05").date()].any()  # Saturday


def test_model_forwards_are_average_prices_over_product_hours():
    idx = year_index(2027)
    m = product_masks(idx, TZ)
    prices = np.vstack([np.full(len(idx), 80.0), np.full(len(idx), 100.0)])
    prices[:, m["cal_peak"]] += 10.0
    f = model_forwards(prices, m)
    assert f["cal_peak"] == pytest.approx(100.0)
    assert f["cal_base"] == pytest.approx(90.0 + 10.0 * m["cal_peak"].mean())


def level_scenarios(n=400, hours=48, seed=3):
    rng = np.random.default_rng(seed)
    level = 85 + 15 * rng.standard_normal((n, 1))
    shape = 10 * np.sin(2 * np.pi * np.arange(hours) / 24)[None, :]
    return level + shape + rng.normal(0, 3, (n, hours))


def test_min_variance_hedge_recovers_a_known_exposure():
    prices = level_scenarios()
    masks = {"cal_base": np.ones(48, bool)}
    forwards = model_forwards(prices, masks)
    exposure_mw = 7.0
    cash = exposure_mw * prices.sum(axis=1)               # long 7 MW of baseload
    payoff = hedge_payoffs(prices, masks, forwards, ["cal_base"])
    h = min_variance_hedge(cash, payoff)
    assert h[0] == pytest.approx(exposure_mw, rel=1e-6)
    hedged = cash + payoff @ h
    assert hedged.std() == pytest.approx(0.0, abs=1e-6)


def test_strategies_rank_the_hedges():
    prices = level_scenarios()
    masks = {"cal_base": np.ones(48, bool)}
    for k in range(1, 5):                                  # four "quarters" of 12 hours
        masks[f"Q{k}"] = np.zeros(48, bool)
        masks[f"Q{k}"][(k - 1) * 12:k * 12] = True
    solar = np.clip(np.sin(2 * np.pi * (np.arange(48) - 6) / 24), 0, None)
    volumes = np.tile(5 * solar, (400, 1))
    cash = (prices * volumes).sum(axis=1)
    t = hedge_strategies(cash, prices, masks, model_forwards(prices, masks),
                         average_mw=volumes.sum(axis=1).mean() / 48)
    assert t.loc["none", "effectiveness"] == pytest.approx(0.0)
    assert t.loc["cal_base_min_variance", "effectiveness"] >= t.loc["cal_base_100", "effectiveness"]
    assert t.loc["quarters_min_variance", "effectiveness"] >= t.loc["cal_base_min_variance",
                                                                    "effectiveness"] - 1e-9
    assert t.loc["cal_base_100", "hedge_ratio"] == pytest.approx(1.0)
    assert (t["cfar_eur"] <= t.loc["none", "cfar_eur"] + 1e-6).all()


def test_the_buyer_needs_less_than_a_full_band_when_output_is_peaky():
    prices = level_scenarios()
    solar = np.clip(np.sin(2 * np.pi * (np.arange(48) - 6) / 24), 0, None)
    rng = np.random.default_rng(4)
    volumes = (1 + 0.1 * rng.standard_normal((400, 1))) * 5 * solar[None, :]
    r = buyer_hedge(prices, volumes)
    assert r["premium_min_variance"] <= r["premium_full_band"] + 1e-9
    assert r["band_mw"] == pytest.approx(volumes.sum(axis=1).mean() / 48)


def test_backtest_sells_at_the_previous_years_average():
    idx = pd.date_range("2024-01-01", "2026-01-01", freq="h", tz=TZ, inclusive="left")
    idx = idx.tz_convert("UTC")
    year = idx.tz_convert(TZ).year
    prices = pd.Series(np.where(year == 2024, 100.0, 80.0), index=idx)
    mw = pd.Series(10.0, index=idx)
    t = backtest_hedge(prices, mw, TZ, years=[2025], hedge_mw=5.0)
    row = t.loc[2025]
    assert row["forward_proxy"] == pytest.approx(100.0)   # 2024's average
    assert row["realised_base"] == pytest.approx(80.0)
    hours = (year == 2025).sum()
    assert row["hedge_pnl_eur"] == pytest.approx(5.0 * hours * (100.0 - 80.0))
    assert row["hedged_revenue_eur"] == pytest.approx(row["merchant_revenue_eur"]
                                                      + row["hedge_pnl_eur"])
