"""Hourly day-ahead price model: seasonality + a daily factor + intraday patterns.

    y_t = arcsinh(P_t / s)                       transform: linear near 0, log-like for spikes
    y_t = L_{month} + S_{season, daytype, hour} + D_{day(t)} + u_t

- L: one level per calendar month of the calibration window (removes slow moves such as
  gas prices). For a future year, L = annual level + average monthly shape.
- S: the average daily shape by season and day type (working day, Saturday, Sunday or
  holiday), including the midday solar dip.
- D: a DAILY factor, the day's own level (windy, calm, sunny, cold...). It reverts to zero
  slowly, as an AR(1) = discrete Ornstein-Uhlenbeck process across days:
      D_d = phi * D_{d-1} + sigma_season * z_d,      half-life = ln 2 / -ln(phi) days.
  Weather regimes last days, so prices remember for days, not hours.
- u: the INTRADAY pattern around the day's level. Simulated days take the pattern of a
  whole historical day from the same season, together with that day's standardised
  shock z_d: a deep midday solar dip stays with the low daily level it came with.

The annual level is set so that the average simulated price matches a forward price
(`calibrate_level`); `level_volatility` adds uncertainty about that level per path.

Version note: a first, single-factor version (hourly AR(1)) reverted within about ten
hours; validation showed far too little day-to-day memory (autocorrelation at 24 h of
0.48 vs 0.70 in history) and too few negative hours. See learning track Step 5, section 4.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ppa_lab.prices.calendar import SEASONS, calendar_features

PROFILE_KEYS = ["season", "daytype", "hour"]
ONE_HOUR, ONE_DAY = pd.Timedelta(hours=1), pd.Timedelta(days=1)


def transform(prices: np.ndarray, scale: float) -> np.ndarray:
    """y = arcsinh(P / s)."""
    return np.arcsinh(np.asarray(prices, dtype="float64") / scale)


def inverse(y: np.ndarray, scale: float) -> np.ndarray:
    """P = s * sinh(y)."""
    return scale * np.sinh(y)


def half_life(phi: float) -> float:
    """Steps until a shock has decayed by half: ln 2 / kappa with kappa = -ln(phi).

    phi <= 0: no persistence (0 steps); phi >= 1: no mean reversion (infinite).
    """
    if phi <= 0:
        return 0.0
    if phi >= 1:
        return math.inf
    return math.log(2) / -math.log(phi)


def fit_ar1(x: pd.Series, step: pd.Timedelta = ONE_HOUR) -> tuple[float, pd.Series]:
    """Least-squares AR(1) coefficient (no intercept) on neighbours exactly `step` apart.

    Returns (phi, innovations eps_t = x_t - phi * x_{t-1}); pairs across gaps are skipped.
    """
    prev = x.shift(1)
    consecutive = x.index.to_series().diff() == step
    valid = consecutive.to_numpy() & prev.notna().to_numpy() & x.notna().to_numpy()
    xt, xp = x[valid], prev[valid]
    phi = float((xt * xp).sum() / (xp * xp).sum())
    return phi, (xt - phi * xp).rename("innovation")


@dataclass
class PriceModel:
    scale: float
    phi: float                # daily AR(1) coefficient of the day factor D
    sigma: pd.Series          # daily shock standard deviation by season
    profile: pd.Series        # y-deviation by (season, daytype, hour)
    month_shape: pd.Series    # monthly level minus the annual level, by month 1-12
    levels: pd.Series         # fitted level per calendar month "YYYY-MM" (calibration window)
    pool_season: np.ndarray   # season of each historical day in the resampling pool
    pool_z: np.ndarray        # its standardised daily shock
    pool_u: np.ndarray        # its intraday pattern, shape (days, 24 local hours)
    calibration_start: str
    calibration_end: str

    @property
    def half_life_days(self) -> float:
        return half_life(self.phi)

    def save(self, path: Path) -> None:
        data = {
            "scale": self.scale, "phi": self.phi,
            "calibration": [self.calibration_start, self.calibration_end],
            "sigma": {s: v for s, v in self.sigma.items()},
            "profile": [[s, d, int(h), v] for (s, d, h), v in self.profile.items()],
            "month_shape": {int(m): v for m, v in self.month_shape.items()},
            "levels": {str(k): v for k, v in self.levels.items()},
            "pool_season": [str(s) for s in self.pool_season],
            "pool_z": [round(float(z), 6) for z in self.pool_z],
            "pool_u": [[round(float(v), 6) for v in row] for row in self.pool_u],
        }
        Path(path).write_text(json.dumps(data))

    @classmethod
    def load(cls, path: Path) -> PriceModel:
        d = json.loads(Path(path).read_text())
        profile = pd.Series({(s, dt, int(h)): v for s, dt, h, v in d["profile"]})
        profile.index = profile.index.set_names(PROFILE_KEYS)
        return cls(
            scale=d["scale"], phi=d["phi"],
            sigma=pd.Series(d["sigma"]).rename_axis("season"),
            profile=profile,
            month_shape=pd.Series({int(m): v for m, v in d["month_shape"].items()},
                                  name="month_shape").rename_axis("month"),
            levels=pd.Series(d["levels"], name="level"),
            pool_season=np.asarray(d["pool_season"]),
            pool_z=np.asarray(d["pool_z"], dtype="float64"),
            pool_u=np.asarray(d["pool_u"], dtype="float64"),
            calibration_start=d["calibration"][0], calibration_end=d["calibration"][1],
        )


def _keys(features: pd.DataFrame) -> pd.MultiIndex:
    return pd.MultiIndex.from_arrays([features[n].to_numpy() for n in PROFILE_KEYS],
                                     names=PROFILE_KEYS)


def fit(prices: pd.Series, tz: str, scale: float) -> PriceModel:
    """Calibrate the model on hourly prices (UTC index, interval beginning)."""
    prices = prices.dropna()
    y = pd.Series(transform(prices.to_numpy(), scale), index=prices.index)
    f = calendar_features(prices.index, tz)
    local = prices.index.tz_convert(tz)
    month = pd.PeriodIndex(local.tz_localize(None), freq="M")
    day = pd.DatetimeIndex(local.normalize().tz_localize(None), name="day")

    # 1. Seasonality: monthly levels and the daily shape, back-fitted in turn.
    profile_t = pd.Series(0.0, index=y.index)
    for _ in range(3):
        levels = (y - profile_t).groupby(month).mean()
        level_t = pd.Series(levels.reindex(month).to_numpy(), index=y.index)
        profile = (y - level_t).groupby([f[n].to_numpy() for n in PROFILE_KEYS]).mean()
        profile.index = profile.index.set_names(PROFILE_KEYS)
        profile_t = pd.Series(profile.reindex(_keys(f)).to_numpy(), index=y.index)
    x = y - level_t - profile_t

    # 2. Daily factor D (mean of the day) and its AR(1) across days.
    x_by_day = pd.Series(x.to_numpy(), index=day)
    daily = x_by_day.groupby(level=0).mean()
    phi, eps = fit_ar1(daily, step=ONE_DAY)
    day_season = pd.Series(eps.index.month.map(SEASONS), index=eps.index)
    sigma = eps.groupby(day_season).std().rename_axis("season")
    z = eps / sigma.reindex(day_season.to_numpy()).to_numpy()

    # 3. Intraday patterns u (deviation from the day's mean), complete 24-hour days only.
    u = x_by_day - daily.reindex(day).to_numpy()
    table = pd.DataFrame({"u": u.to_numpy(), "hour": f["hour"].to_numpy()}, index=day)
    table = table.groupby([table.index, "hour"])["u"].mean().unstack("hour")
    hours_per_day = x_by_day.groupby(level=0).size()
    full = hours_per_day[hours_per_day == 24].index.intersection(z.index)
    pool = table.loc[full, list(range(24))].dropna()

    by_year = levels.groupby(levels.index.year).transform("mean")
    month_shape = (levels - by_year).groupby(levels.index.month).mean()
    month_shape = month_shape.reindex(range(1, 13), fill_value=0.0).rename_axis("month")
    return PriceModel(
        scale=scale, phi=phi, sigma=sigma, profile=profile,
        month_shape=month_shape.rename("month_shape"),
        levels=pd.Series(levels.to_numpy(), index=levels.index.astype(str), name="level"),
        pool_season=np.asarray(pool.index.month.map(SEASONS)),
        pool_z=z.reindex(pool.index).to_numpy(),
        pool_u=pool.to_numpy(),
        calibration_start=str(local.min().date()), calibration_end=str(local.max().date()),
    )


def seasonal_mean(model: PriceModel, index: pd.DatetimeIndex, tz: str,
                  annual_level: float | None = None) -> np.ndarray:
    """Deterministic part of y for each timestamp.

    With `annual_level` (a future year): annual level + monthly shape + daily shape.
    Without it (in-sample): the fitted level of each calendar month + daily shape.
    """
    f = calendar_features(index, tz)
    shape = model.profile.reindex(_keys(f)).fillna(0.0).to_numpy()
    if annual_level is None:
        month = pd.PeriodIndex(index.tz_convert(tz).tz_localize(None), freq="M").astype(str)
        level = model.levels.reindex(month).to_numpy()
        if np.isnan(level).any():
            raise ValueError("months outside the calibration window need an annual_level")
    else:
        level = annual_level + model.month_shape.reindex(f["month"].to_numpy()).to_numpy()
    return level + shape


def _days(index: pd.DatetimeIndex, tz: str) -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    """Day code per timestamp, the local days, and the local hour per timestamp."""
    local = index.tz_convert(tz)
    codes, days = pd.factorize(local.normalize())
    return codes, days, local.hour.to_numpy()


def _draw_pool_days(model: PriceModel, days: pd.DatetimeIndex, n_paths: int,
                    rng: np.random.Generator) -> np.ndarray:
    """For every path and day, the index of a historical day from the same season."""
    seasons = np.asarray(days.month.map(SEASONS))
    picks = np.empty((n_paths, len(days)), dtype=np.int64)
    for season in np.unique(seasons):
        candidates = np.flatnonzero(model.pool_season == season)
        mask = seasons == season
        picks[:, mask] = rng.choice(candidates, size=(n_paths, int(mask.sum())))
    return picks


def _daily_factor(model: PriceModel, days: pd.DatetimeIndex, picks: np.ndarray,
                  rng: np.random.Generator, bootstrap: bool) -> np.ndarray:
    seasons = days.month.map(SEASONS)
    sig = model.sigma.reindex(seasons).fillna(float(model.sigma.mean())).to_numpy()
    z = model.pool_z[picks] if bootstrap else rng.standard_normal(picks.shape)
    d = np.empty(picks.shape)
    d[:, 0] = z[:, 0] * sig[0] / math.sqrt(1.0 - model.phi**2)  # start in the stationary state
    for k in range(1, picks.shape[1]):
        d[:, k] = model.phi * d[:, k - 1] + sig[k] * z[:, k]
    return d


def random_streams(seed: int) -> tuple[np.random.Generator, np.random.Generator]:
    """Independent random streams for residuals and level shocks (reproducible)."""
    residual, level = np.random.SeedSequence(seed).spawn(2)
    return np.random.default_rng(residual), np.random.default_rng(level)


def simulate_daily_factor(model: PriceModel, index: pd.DatetimeIndex, tz: str, n_paths: int,
                          seed: int = 0, bootstrap: bool = True) -> np.ndarray:
    """The daily factor D only, shape (paths, days)."""
    rng = random_streams(seed)[0]
    _, days, _ = _days(index, tz)
    picks = _draw_pool_days(model, days, n_paths, rng)
    return _daily_factor(model, days, picks, rng, bootstrap)


def simulate_residuals(model: PriceModel, index: pd.DatetimeIndex, tz: str, n_paths: int,
                       seed: int = 0, bootstrap: bool = True) -> np.ndarray:
    """Random part D + u of y, shape (paths, hours)."""
    return _residuals(model, index, tz, n_paths, random_streams(seed)[0], bootstrap)


def _residuals(model: PriceModel, index: pd.DatetimeIndex, tz: str, n_paths: int,
               rng: np.random.Generator, bootstrap: bool) -> np.ndarray:
    codes, days, hours = _days(index, tz)
    picks = _draw_pool_days(model, days, n_paths, rng)
    d = _daily_factor(model, days, picks, rng, bootstrap)
    u = model.pool_u[picks[:, codes], hours[None, :]]
    return d[:, codes] + u


def simulate(model: PriceModel, index: pd.DatetimeIndex, tz: str, n_paths: int,
             annual_level: float | None = None, seed: int = 0, level_volatility: float = 0.0,
             bootstrap: bool = True) -> np.ndarray:
    """Simulated hourly prices in EUR/MWh, shape (paths, hours)."""
    residual_rng, level_rng = random_streams(seed)
    mu = seasonal_mean(model, index, tz, annual_level)
    x = _residuals(model, index, tz, n_paths, residual_rng, bootstrap)
    shift = level_volatility * level_rng.standard_normal((n_paths, 1)) if level_volatility else 0.0
    return inverse(mu[None, :] + x + shift, model.scale)


def calibrate_level(model: PriceModel, index: pd.DatetimeIndex, tz: str, target_price: float,
                    n_paths: int = 200, seed: int = 0, bootstrap: bool = True) -> float:
    """Annual level (in y) at which the average simulated price equals `target_price`.

    Uses the same random numbers as `simulate(..., seed=seed)`, so that call reproduces
    the target exactly. Bisection: the average price rises monotonically with the level.
    """
    mu0 = seasonal_mean(model, index, tz, annual_level=0.0)
    x = simulate_residuals(model, index, tz, n_paths, seed, bootstrap)
    return solve_level(mu0, x, model.scale, target_price)


def solve_level(mu0: np.ndarray, x: np.ndarray, scale: float, target_price: float) -> float:
    """Level L with mean(inverse(mu0 + L + x)) = target_price, by bisection.

    mu0: deterministic part without the level (hours); x: random part (paths x hours).
    The average price rises monotonically with L, so halving [-10, 10] converges.
    """
    low, high = -10.0, 10.0
    for _ in range(100):
        mid = 0.5 * (low + high)
        if inverse(mu0[None, :] + mid + x, scale).mean() < target_price:
            low = mid
        else:
            high = mid
        if high - low < 1e-10:
            break
    return 0.5 * (low + high)
