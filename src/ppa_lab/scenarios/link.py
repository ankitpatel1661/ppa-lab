"""The weather-price link: prices simulated FOR a given weather (Step 6).

Step 5 drew each simulated day at random from its season, so a sunny, windy day was as
likely to get an expensive price day as a cheap one. Here the weather decides:

    y_t = seasonal mean (Step 5) + E_d + r_d + u_(j, hour)

- E_d, the weather effect on the day's level: a regression per season of the Step 5 daily
  factor on the day's weather anomalies (solar and wind capacity factor, temperature):
      E_d = const_season + beta_season . anomaly_d
  In-sample the anomaly is taken within the month (the fitted monthly levels already hold
  each month's average weather); for a future year it is taken against the climatology of
  the weather years, so a windy month is a cheap month.
- r_d, what weather does not explain (fuel, demand, outages, weather elsewhere): an AR(1)
  across days, r_d = phi r_(d-1) + sigma_season xi_j, started in its stationary state.
- u_(j, hour), the intraday pattern of an ANALOG day j: one of the k historical days within
  +-window days of the same date whose weather was closest. A sunny day gets the deep midday
  dip of a sunny day. The analog day also supplies the residual shock xi_j.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ppa_lab.prices.calendar import SEASONS
from ppa_lab.prices.model import (
    ONE_DAY,
    PriceModel,
    fit_ar1,
    half_life,
    inverse,
    random_streams,
    seasonal_mean,
    solve_level,
    transform,
)
from ppa_lab.scenarios.weather import FEATURES


@dataclass
class WeatherLink:
    climatology: pd.DataFrame     # month (1-12) x feature: normal weather of the weather years
    beta: pd.DataFrame            # season x ["const", *FEATURES]: response of the daily level
    r_squared: pd.Series          # season: share of daily-level variance explained by weather
    phi: float                    # AR(1) coefficient of the unexplained daily level, per day
    sigma: pd.Series              # season: its shock standard deviation
    pool_days: pd.DatetimeIndex   # historical days available as analogs
    pool_features: pd.DataFrame   # their weather (raw features)
    pool_xi: np.ndarray           # their standardised residual shock
    pool_u: np.ndarray            # their intraday pattern, days x 24 local hours
    feature_scale: pd.Series      # feature standard deviations used for analog distances
    window_days: int              # analogs within +-window days of the same date
    k: int                        # number of nearest analogs to draw from

    @property
    def half_life_days(self) -> float:
        return half_life(self.phi)


def _seasons(days: pd.DatetimeIndex) -> np.ndarray:
    return np.asarray(days.month.map(SEASONS))


def _anomalies(link_or_clim: pd.DataFrame, weather: pd.DataFrame, in_sample: bool) -> pd.DataFrame:
    w = weather[list(FEATURES)]
    days = pd.DatetimeIndex(w.index)
    if in_sample:
        return w - w.groupby([days.year, days.month]).transform("mean")
    return w - link_or_clim.reindex(days.month)[list(FEATURES)].to_numpy()


def weather_effect(link: WeatherLink, weather: pd.DataFrame, in_sample: bool) -> np.ndarray:
    """E_d for each day (row) of `weather`: const + beta . anomaly, by season."""
    days = pd.DatetimeIndex(weather.index)
    anomaly = _anomalies(link.climatology, weather, in_sample).to_numpy()
    beta = link.beta.reindex(_seasons(days))
    return beta["const"].to_numpy() + (anomaly * beta[list(FEATURES)].to_numpy()).sum(axis=1)


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #
def fit_link(model: PriceModel, prices: pd.Series, features: pd.DataFrame,
             climatology: pd.DataFrame, tz: str, window_days: int = 30,
             k: int = 10) -> WeatherLink:
    """Calibrate the link on the Step 5 calibration history and the weather of those days."""
    prices = prices.dropna()
    x = (transform(prices.to_numpy(), model.scale, model.negative_scale)
         - seasonal_mean(model, prices.index, tz))
    local = prices.index.tz_convert(tz)
    day = pd.DatetimeIndex(local.normalize().tz_localize(None), name="day")
    by_day = pd.Series(x, index=day)
    daily = by_day.groupby(level=0).mean()

    weather = features.reindex(daily.index)[list(FEATURES)]
    if weather.isna().any().any():
        missing = int(weather.isna().any(axis=1).sum())
        raise ValueError(f"weather features missing for {missing} calibration days")
    anomaly = _anomalies(climatology, weather, in_sample=True)

    # 1. Weather effect on the daily level, one regression per season.
    seasons = _seasons(daily.index)
    rows, r2 = {}, {}
    resid = pd.Series(np.nan, index=daily.index)
    for season in np.unique(seasons):
        m = seasons == season
        design = np.column_stack([np.ones(m.sum()), anomaly[m].to_numpy()])
        target = daily[m].to_numpy()
        coef, *_ = np.linalg.lstsq(design, target, rcond=None)
        rows[season] = coef
        fitted = design @ coef
        resid[m] = target - fitted
        r2[season] = 1.0 - ((target - fitted) ** 2).sum() / ((target - target.mean()) ** 2).sum()
    beta = pd.DataFrame(rows, index=["const", *FEATURES]).T.rename_axis("season")

    # 2. What weather does not explain: AR(1) across days, shocks by season.
    phi, eps = fit_ar1(resid, step=ONE_DAY)
    eps_season = _seasons(pd.DatetimeIndex(eps.index))
    sigma = eps.groupby(eps_season).std().rename_axis("season")
    xi = eps / sigma.reindex(eps_season).to_numpy()

    # 3. Analog pool: complete 24-hour days with a residual shock.
    u = by_day - daily.reindex(day).to_numpy()
    table = pd.DataFrame({"u": u.to_numpy(), "hour": local.hour}, index=day)
    table = table.groupby([table.index, "hour"])["u"].mean().unstack("hour")
    hours_per_day = by_day.groupby(level=0).size()
    pool = hours_per_day[hours_per_day == 24].index.intersection(xi.index)
    pool_features = weather.loc[pool]
    return WeatherLink(
        climatology=climatology[list(FEATURES)], beta=beta,
        r_squared=pd.Series(r2).rename_axis("season"), phi=phi, sigma=sigma,
        pool_days=pd.DatetimeIndex(pool, name="day"), pool_features=pool_features,
        pool_xi=xi.reindex(pool).to_numpy(), pool_u=table.loc[pool, list(range(24))].to_numpy(),
        # A feature that never varies (sd 0) must not turn every distance into NaN.
        feature_scale=pool_features.std().replace(0.0, 1.0), window_days=window_days, k=k,
    )


def restrict_pool(link: WeatherLink, start: pd.Timestamp) -> WeatherLink:
    """The same link, with analog days from `start` on only (e.g. the most recent year,
    whose midday dips reflect today's solar capacity). Responses and phi are unchanged."""
    keep = np.asarray(link.pool_days >= start)
    return dataclasses.replace(link, pool_days=link.pool_days[keep],
                               pool_features=link.pool_features[keep],
                               pool_xi=link.pool_xi[keep], pool_u=link.pool_u[keep])


# --------------------------------------------------------------------------- #
# Analog days
# --------------------------------------------------------------------------- #
def analog_days(link: WeatherLink, day: pd.Timestamp, weather_row: pd.Series,
                exclude_days: int | None = None) -> np.ndarray:
    """Pool indices of the (up to) k historical days nearest in weather, nearest first.

    Candidates lie within +-window_days of the same date in any year. `exclude_days` drops
    pool days that close to `day` itself (in-sample validation: no peeking at the answer).
    """
    gap = np.abs(link.pool_days.dayofyear.to_numpy() - day.dayofyear)
    ok = np.minimum(gap, 365 - gap) <= link.window_days
    if exclude_days is not None:
        ok &= np.abs((link.pool_days - day).days.to_numpy()) > exclude_days
    candidates = np.flatnonzero(ok)
    if len(candidates) == 0:
        raise ValueError(f"no analog days for {day:%Y-%m-%d}")
    diff = (link.pool_features.iloc[candidates] - weather_row[list(FEATURES)]) / link.feature_scale
    distance = (diff.to_numpy() ** 2).sum(axis=1)
    return candidates[np.argsort(distance, kind="stable")[: link.k]]


# --------------------------------------------------------------------------- #
# Simulation
# --------------------------------------------------------------------------- #
def _linked_residuals(model: PriceModel, link: WeatherLink, index: pd.DatetimeIndex, tz: str,
                      weather: pd.DataFrame, n_paths: int, rng: np.random.Generator,
                      in_sample: bool, exclude_days: int | None) -> np.ndarray:
    local = index.tz_convert(tz)
    codes, days = pd.factorize(local.normalize().tz_localize(None))
    days = pd.DatetimeIndex(days)
    hours = local.hour.to_numpy()
    w = weather.reindex(days)
    if w[list(FEATURES)].isna().any().any():
        raise ValueError("weather missing for some simulated days")

    effect = weather_effect(link, w, in_sample)
    picks = np.empty((n_paths, len(days)), dtype=np.int64)
    for i, d in enumerate(days):
        near = analog_days(link, d, w.iloc[i], exclude_days)
        picks[:, i] = near[rng.integers(0, len(near), n_paths)]

    sig = link.sigma.reindex(_seasons(days)).fillna(float(link.sigma.mean())).to_numpy()
    z = link.pool_xi[picks]
    r = np.empty(picks.shape)
    r[:, 0] = z[:, 0] * sig[0] / math.sqrt(1.0 - link.phi**2)    # stationary start
    for i in range(1, len(days)):
        r[:, i] = link.phi * r[:, i - 1] + sig[i] * z[:, i]
    level = effect[None, :] + r
    return level[:, codes] + link.pool_u[picks[:, codes], hours[None, :]]


def linked_residuals(model: PriceModel, link: WeatherLink, index: pd.DatetimeIndex, tz: str,
                     weather: pd.DataFrame, n_paths: int, seed: int = 0,
                     in_sample: bool = False, exclude_days: int | None = None) -> np.ndarray:
    """Random part of y given the weather (paths x hours): E + r + u. Same seed, same draws
    as `simulate_linked(..., seed=seed)`."""
    rng = random_streams(seed)[0]
    return _linked_residuals(model, link, index, tz, weather, n_paths, rng, in_sample,
                             exclude_days)


def simulate_linked(model: PriceModel, link: WeatherLink, index: pd.DatetimeIndex, tz: str,
                    weather: pd.DataFrame, n_paths: int, annual_level: float | None = None,
                    seed: int = 0, level_volatility: float = 0.0,
                    exclude_days: int | None = None) -> np.ndarray:
    """Hourly prices (paths x hours, EUR/MWh) for the given daily weather.

    `weather` has one row per local day of `index` with the FEATURES columns. Without
    `annual_level` the calibration window is re-simulated (fitted monthly levels).
    """
    residual_rng, level_rng = random_streams(seed)
    in_sample = annual_level is None
    mu = seasonal_mean(model, index, tz, annual_level)
    x = _linked_residuals(model, link, index, tz, weather, n_paths, residual_rng, in_sample,
                          exclude_days)
    shift = level_volatility * level_rng.standard_normal((n_paths, 1)) if level_volatility else 0.0
    return inverse(mu[None, :] + x + shift, model.scale, model.negative_scale)


def calibrate_linked_level(model: PriceModel, link: WeatherLink, index: pd.DatetimeIndex,
                           tz: str, weather: pd.DataFrame, target_price: float,
                           n_paths: int = 200, seed: int = 0) -> float:
    """Annual level at which `simulate_linked(..., seed=seed)` averages `target_price`."""
    mu0 = seasonal_mean(model, index, tz, annual_level=0.0)
    x = linked_residuals(model, link, index, tz, weather, n_paths, seed)
    return solve_level(mu0, x, model.scale, target_price, model.negative_scale)
