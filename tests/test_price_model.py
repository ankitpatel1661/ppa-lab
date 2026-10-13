"""Stochastic price model: transform, mean reversion, seasonality, simulation, level.

The model has two random parts on top of the seasonal shape (see prices/model.py):
a DAILY factor that reverts slowly (weather regimes last days) and INTRADAY patterns
resampled as whole historical days from the same season. Parameter-recovery tests use
synthetic data with KNOWN parameters: if the estimator cannot find them again, it cannot
be trusted on real prices.
"""

import math

import numpy as np
import pandas as pd
import pytest

from ppa_lab.prices.model import (
    PriceModel,
    calibrate_level,
    fit,
    fit_ar1,
    half_life,
    inverse,
    seasonal_mean,
    simulate,
    simulate_daily_factor,
    simulate_residuals,
    transform,
)
from ppa_lab.prices.validation import autocorrelation, price_statistics

TZ = "Europe/Berlin"


def hourly(first_local: str, last_local_exclusive: str) -> pd.DatetimeIndex:
    idx = pd.date_range(first_local, last_local_exclusive, freq="h", tz=TZ, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


def ar1(phi: float, sigma: float, n: int, seed: int = 11) -> np.ndarray:
    """Synthetic AR(1) path; each call has its own seed, so results never depend on test order."""
    x = np.zeros(n)
    eps = np.random.default_rng(seed).normal(0, sigma, n)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + eps[t]
    return x


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #
def test_arcsinh_transform_round_trip_and_negative_prices():
    p = np.array([-500.0, -20.0, 0.0, 35.0, 90.0, 2000.0])
    np.testing.assert_allclose(inverse(transform(p, 50.0), 50.0), p)
    # Near zero it is almost linear (P/s); for spikes it grows like a logarithm.
    assert transform(np.array([1.0]), 50.0)[0] == pytest.approx(0.02, rel=1e-3)
    neg, pos = transform(np.array([-100.0, 100.0]), 50.0)
    assert neg == pytest.approx(-pos)  # symmetric: negative prices are no special case


def test_half_life_from_the_ar1_coefficient():
    # phi = 0.5 per step -> kappa = ln 2 -> half-life exactly 1 step
    assert half_life(0.5) == pytest.approx(1.0)
    assert half_life(0.7) == pytest.approx(math.log(2) / -math.log(0.7))


def test_half_life_edge_cases():
    # No persistence (phi <= 0) reverts within one step; phi >= 1 never reverts.
    assert half_life(0.0) == 0.0 and half_life(-0.1) == 0.0
    assert half_life(1.0) == math.inf


def test_fit_ar1_recovers_a_known_coefficient():
    idx = pd.date_range("2024-01-01", periods=30_000, freq="h", tz="UTC")
    phi, eps = fit_ar1(pd.Series(ar1(0.9, 1.0, len(idx)), index=idx))
    assert phi == pytest.approx(0.9, abs=0.01)
    assert eps.std() == pytest.approx(1.0, abs=0.03)


def test_fit_ar1_ignores_pairs_across_gaps():
    idx = pd.date_range("2024-01-01", periods=30_000, freq="h", tz="UTC")
    x = pd.Series(ar1(0.9, 1.0, len(idx)), index=idx)
    # Every 3rd hour missing: half of all neighbouring pairs would span two hours. Using
    # them would mix phi (0.9) with phi^2 (0.81) and give about 0.855.
    phi, _ = fit_ar1(x.drop(x.index[::3]))
    assert phi == pytest.approx(0.9, abs=0.01)


# --------------------------------------------------------------------------- #
# Calibration on synthetic prices with known structure
# --------------------------------------------------------------------------- #
PHI_DAY, SIGMA_DAY, SIGMA_HOUR = 0.7, 0.2, 0.1


@pytest.fixture(scope="module")
def synthetic():
    """Three years: daily shape 0.5*sin, a daily AR(1) factor (0.7, 0.2), hourly noise 0.1."""
    idx = hourly("2023-01-01", "2026-01-01")
    local = idx.tz_convert(TZ)
    day_codes, days = pd.factorize(local.normalize())
    daily = ar1(PHI_DAY, SIGMA_DAY, len(days), seed=21)
    noise = np.random.default_rng(22).normal(0, SIGMA_HOUR, len(idx))
    y = 1.5 + 0.5 * np.sin(2 * np.pi * local.hour.to_numpy() / 24) + daily[day_codes] + noise
    prices = pd.Series(inverse(y, 50.0), index=idx, name="price_eur_mwh")
    return prices, fit(prices, TZ, scale=50.0)


def test_fit_recovers_the_daily_shape(synthetic):
    _, model = synthetic
    # True shape at 06:00 local = 0.5 * sin(pi/2) = +0.5; at 18:00 = -0.5 (around the level).
    assert model.profile.loc[("summer", "weekday", 6)] == pytest.approx(0.5, abs=0.06)
    assert model.profile.loc[("winter", "weekday", 18)] == pytest.approx(-0.5, abs=0.06)


def test_fit_recovers_the_daily_mean_reversion(synthetic):
    _, model = synthetic
    # The monthly levels demean the daily factor in blocks of ~30 days, which biases an AR(1)
    # estimate down by about (1 + 3 phi) / T = 3.1 / 30.4 = 0.10 (Kendall's bias): expect ~0.60.
    assert model.phi == pytest.approx(PHI_DAY - (1 + 3 * PHI_DAY) / 30.4, abs=0.06)
    assert float(model.sigma.mean()) == pytest.approx(SIGMA_DAY, abs=0.02)
    assert model.half_life_days == pytest.approx(half_life(model.phi))


def test_model_round_trips_through_json(synthetic, tmp_path):
    _, model = synthetic
    path = tmp_path / "model.json"
    model.save(path)
    again = PriceModel.load(path)
    assert again.phi == model.phi and again.scale == model.scale
    pd.testing.assert_series_equal(again.profile, model.profile)
    np.testing.assert_allclose(again.pool_u, model.pool_u, atol=1e-5)
    assert list(again.pool_season) == list(model.pool_season)


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def test_simulation_is_reproducible_and_has_one_row_per_path(synthetic):
    _, model = synthetic
    idx = hourly("2027-01-01", "2027-02-01")
    a = simulate(model, idx, TZ, n_paths=20, annual_level=1.5, seed=3)
    b = simulate(model, idx, TZ, n_paths=20, annual_level=1.5, seed=3)
    assert a.shape == (20, len(idx))
    np.testing.assert_array_equal(a, b)


def test_daily_factor_has_the_stationary_variance(synthetic):
    # An AR(1) with coefficient phi and shock sd sigma has variance sigma^2 / (1 - phi^2).
    _, model = synthetic
    idx = hourly("2027-01-01", "2032-01-01")
    d = simulate_daily_factor(model, idx, TZ, n_paths=300, seed=5, bootstrap=False)
    sigma = float(model.sigma.mean())
    assert d.var() == pytest.approx(sigma**2 / (1 - model.phi**2), rel=0.1)


def test_simulation_starts_in_the_stationary_state(synthetic):
    # Already on the first day the spread across paths must be the long-run spread,
    # otherwise the start of every simulated year would be artificially calm.
    _, model = synthetic
    idx = hourly("2027-07-01", "2027-07-03")
    d = simulate_daily_factor(model, idx, TZ, n_paths=4000, seed=13, bootstrap=False)
    sigma = float(model.sigma.mean())
    assert d[:, 0].var() == pytest.approx(sigma**2 / (1 - model.phi**2), rel=0.15)


def test_each_simulated_day_reuses_one_whole_historical_day(synthetic):
    # Intraday patterns are resampled as whole days from the same season, so a deep
    # midday dip stays together with the rest of its day.
    _, model = synthetic
    idx = hourly("2027-07-05", "2027-07-08")          # three summer days, no DST change
    x = simulate_residuals(model, idx, TZ, n_paths=1, seed=17)[0].reshape(3, 24)
    summer = model.pool_u[model.pool_season == "summer"]
    for day in x:
        pattern = day - day.mean()
        distance = np.abs(summer - summer.mean(axis=1, keepdims=True) - pattern).max(axis=1)
        assert distance.min() < 1e-9


def test_level_is_calibrated_to_a_target_average_price(synthetic):
    _, model = synthetic
    idx = hourly("2027-01-01", "2028-01-01")
    level = calibrate_level(model, idx, TZ, target_price=85.0, n_paths=100, seed=7)
    paths = simulate(model, idx, TZ, n_paths=100, annual_level=level, seed=7)
    assert paths.mean() == pytest.approx(85.0, abs=0.1)


def test_level_volatility_spreads_the_annual_averages(synthetic):
    _, model = synthetic
    idx = hourly("2027-01-01", "2027-04-01")
    calm = simulate(model, idx, TZ, n_paths=300, annual_level=1.5, seed=9).mean(axis=1)
    wild = simulate(model, idx, TZ, n_paths=300, annual_level=1.5, seed=9,
                    level_volatility=0.2).mean(axis=1)
    assert wild.std() > 3 * calm.std()


def test_in_sample_seasonal_mean_uses_the_fitted_monthly_levels(synthetic):
    prices, model = synthetic
    mu = seasonal_mean(model, prices.index, TZ)          # no annual level -> fitted levels
    # Shape variance 0.125; daily factor 0.2^2 / (1 - 0.49) = 0.078; hourly noise 0.01:
    # correlation of the deterministic part with y = sqrt(0.125 / 0.213) = 0.77.
    corr = np.corrcoef(mu, transform(prices.to_numpy(), 50.0))[0, 1]
    assert corr == pytest.approx(0.77, abs=0.05)


# --------------------------------------------------------------------------- #
# Validation statistics
# --------------------------------------------------------------------------- #
def test_price_statistics_by_hand():
    stats = price_statistics(np.array([-10.0, 0.0, 10.0, 20.0, 30.0]))
    assert stats["mean"] == pytest.approx(10.0)
    assert stats["negative_share"] == pytest.approx(0.2)
    assert stats["p50"] == pytest.approx(10.0)


def test_autocorrelation_of_an_ar1_is_phi_to_the_lag():
    x = ar1(0.9, 1.0, 50_000)
    acf = autocorrelation(x[None, :], lags=(1, 2))
    assert acf[1] == pytest.approx(0.9, abs=0.02)
    assert acf[2] == pytest.approx(0.81, abs=0.03)
