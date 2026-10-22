"""Step 5 exercises: the building blocks of the price model. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q                  # automatic checks
    .venv/bin/python exercises/step05_prices.py     # print your answers

Rules of the game
- Work in LOCAL time (Europe/Berlin): a "day" is a local calendar day.
- Use prices_hourly.parquet (column `price_eur_mwh`, index in UTC) written by `make build`.
- Do not import ppa_lab.prices or ppa_lab.analysis: write the formulas yourself.
- Use numpy and pandas only (no statsmodels, no scipy).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TZ = "Europe/Berlin"
SCALE = 120.0  # EUR/MWh, the arcsinh scale in config/project.toml [price_model]


def load_hourly_prices() -> pd.DataFrame:
    """Hourly day-ahead prices, index in UTC (column 'price_eur_mwh')."""
    return pd.read_parquet(PROCESSED / "prices_hourly.parquet")


def transform(prices: np.ndarray | pd.Series, scale: float = SCALE):
    """Given: y = arcsinh(P / scale). Linear near zero, logarithmic for spikes, fine for P < 0."""
    return np.arcsinh(prices / scale)


# --------------------------------------------------------------------------- #
# Exercise 1: how fast do price levels revert?
# --------------------------------------------------------------------------- #
def daily_ar1(prices: pd.DataFrame, scale: float, year: int) -> dict[str, float]:
    """AR(1) coefficient and half-life of the DAILY price level in one local year.

    1. y = transform(P, scale) for every hour of the local year.
    2. d = mean of y per local calendar day (365 or 366 values).
    3. Remove the seasonality in two steps:
       a. subtract each month's mean of d   (slow level: gas, CO2, season)
       b. then subtract each weekday's mean (Mon..Sun) of what is left (demand: weekends)
    4. phi = sum(d_t * d_{t-1}) / sum(d_{t-1}^2)   over consecutive days (OLS, no intercept;
       the year is complete, so a plain shift by one day is fine).
    5. half-life = ln 2 / -ln(phi)   in days.

    Return {"phi": ..., "half_life_days": ...}.
    Hints: .tz_convert(TZ).loc[str(year)], groupby(index.date), groupby(...).transform("mean").
    """
    p = prices["price_eur_mwh"].tz_convert(TZ).loc[str(year)]

    # Transform prices and average by local calendar day.
    y = pd.Series(transform(p.to_numpy(), scale), index=p.index)
    d = y.groupby(y.index.date).mean()

    # Remove monthly level effects.
    dates = pd.DatetimeIndex(d.index)
    d.index = dates
    d = d - d.groupby(d.index.month).transform("mean")

    # Remove weekday effects from the monthly-adjusted daily series.
    d = d - d.groupby(d.index.dayofweek).transform("mean")

    # OLS AR(1) coefficient without an intercept.
    previous = d.iloc[:-1].to_numpy()
    current = d.iloc[1:].to_numpy()
    denominator = np.sum(previous ** 2)

    if denominator == 0:
        raise ValueError("Cannot estimate AR(1): previous-day values have zero variance")

    phi = float(np.sum(current * previous) / denominator)

    if not 0 < phi < 1:
        raise ValueError(f"Estimated phi must be between 0 and 1 for this half-life formula; got {phi}")

    half_life = float(np.log(2) / -np.log(phi))

    return {"phi": phi, "half_life_days": half_life}


# --------------------------------------------------------------------------- #
# Exercise 2: simulate the daily factor
# --------------------------------------------------------------------------- #
def simulate_ar1(phi: float, sigma: float, n_days: int, n_paths: int, seed: int) -> np.ndarray:
    """Simulate n_paths AR(1) paths x_t = phi * x_{t-1} + eps_t, eps_t ~ N(0, sigma^2).

    Return an array of shape (n_paths, n_days).
    The FIRST day must already be in the long-run (stationary) state: draw it from
    N(0, sigma^2 / (1 - phi^2)), not 0. Otherwise every simulated year starts too calm.
    Use rng = np.random.default_rng(seed), so the same seed gives the same paths.
    """
    if not -1 < phi < 1:
        raise ValueError("phi must be between -1 and 1 for a stationary AR(1)")
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if n_days < 1 or n_paths < 1:
        raise ValueError("n_days and n_paths must be positive")

    rng = np.random.default_rng(seed)
    x = np.empty((n_paths, n_days), dtype=float)

    # Start in the stationary distribution.
    stationary_sd = sigma / np.sqrt(1 - phi**2)
    x[:, 0] = rng.normal(0, stationary_sd, size=n_paths)

    # Simulate the remaining days.
    if n_days > 1:
        eps = rng.normal(0, sigma, size=(n_paths, n_days - 1))
        for t in range(1, n_days):
            x[:, t] = phi * x[:, t - 1] + eps[:, t - 1]

    return x


# --------------------------------------------------------------------------- #
# Exercise 3: calibrate the level to a forward price
# --------------------------------------------------------------------------- #
def level_for_forward(x: np.ndarray, scale: float, target: float) -> float:
    """The level L such that the average price equals the forward:

        mean( scale * sinh(L + x) ) = target

    x holds everything except the level (shape and noise, in transformed units).
    sinh is not linear, so L is NOT simply arcsinh(target / scale). Find L by bisection:
    start with low = -10, high = 10 and halve the interval until it is shorter than 1e-10.
    (The average price rises with L, so the sign of the error tells you which half to keep.)
    """
    if scale <= 0:
        raise ValueError("scale must be positive")
    if x.size == 0:
        raise ValueError("x must not be empty")

    low, high = -10.0, 10.0

    def average_price(level: float) -> float:
        return float(np.mean(scale * np.sinh(level + x)))

    # Ensure the target is bracketed by the starting interval.
    if not average_price(low) <= target <= average_price(high):
        raise ValueError("Target forward is outside the price range bracketed by [-10, 10]")

    while high - low >= 1e-10:
        mid = (low + high) / 2
        if average_price(mid) < target:
            low = mid
        else:
            high = mid

    return float((low + high) / 2)


def shape_of_year(prices: pd.DataFrame, scale: float, year: int) -> np.ndarray:
    """Given: one local year of transformed prices minus their mean (the 'x' of Exercise 3)."""
    y = transform(prices["price_eur_mwh"].tz_convert(TZ).loc[str(year)].to_numpy(), scale)
    return y - y.mean()


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): what the model gets wrong, and why it matters
# --------------------------------------------------------------------------- #
# The Step 5 model reproduces the mean, the spread and the average daily shape of history,
# but history has more negative hours (6.2% vs 4.9%) and a stronger 24-hour autocorrelation
# (0.70 vs 0.59). Priced with simulated paths, the solar park's capture rate is about 0.61;
# with real 2025 prices it was 0.555. In 3-5 sentences: why does a price model that is
# independent of the weather overstate what solar earns, how are the two validation misses
# linked to it, and what would you change first?
#
# Your answer:
#
#A price model that is independent of weather overstates solar earnings because high solar generation often coincides with lower electricity prices, reducing the price solar plants receive. The model underestimates negative-price hours (4.9% versus 6.2% in history) and 24-hour autocorrelation (0.59 versus 0.70), so it misses some low-price periods and persistent daily price patterns. This helps explain why the simulated solar capture rate of about 0.61 is higher than the 2025 historical value of 0.555. I would first link simulated prices to weather-driven solar and wind generation, then recalibrate and validate negative-price frequency and hourly autocorrelation.


if __name__ == "__main__":
    prices = load_hourly_prices()
    for year in (2024, 2025):
        r = daily_ar1(prices, SCALE, year)
        print(f"Ex 1  {year}: phi {r['phi']:.3f} per day, half-life {r['half_life_days']:.2f} days")
    x = simulate_ar1(0.5, 0.2, n_days=365, n_paths=2000, seed=1)
    print(f"Ex 2  variance {x.var():.4f} (theory {0.2**2 / (1 - 0.5**2):.4f}),",
          f"first-day variance {x[:, 0].var():.4f}")
    shape = shape_of_year(prices, SCALE, 2025)
    level = level_for_forward(shape, SCALE, 85.0)
    naive = float(np.arcsinh(85.0 / SCALE))
    print(f"Ex 3  level {level:.4f} vs naive arcsinh(85/{SCALE:g}) = {naive:.4f};",
          f"the naive level averages {(SCALE * np.sinh(naive + shape)).mean():.2f} EUR/MWh")
