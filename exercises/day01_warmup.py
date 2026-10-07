"""Day 1 warm-up exercises. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q          # automatic checks
    .venv/bin/python exercises/day01_warmup.py   # print your answers

Rules of the game
- Work in LOCAL time (Europe/Berlin): markets define peak hours and delivery days locally.
- Use the processed hourly/15-minute files; do not re-download anything.
- Read the hints, try first, and only then ask for help.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TZ = "Europe/Berlin"


def load_hourly_prices() -> pd.DataFrame:
    """Hourly day-ahead prices, index in UTC (column 'price_eur_mwh')."""
    return pd.read_parquet(PROCESSED / "prices_hourly.parquet")


def load_power_15min() -> pd.DataFrame:
    """15-minute generation in MW (columns such as 'solar_mw'), index in UTC."""
    return pd.read_parquet(PROCESSED / "power_15min.parquet")


# --------------------------------------------------------------------------- #
# Exercise 1: peak vs base
# --------------------------------------------------------------------------- #
def peak_base(hourly: pd.DataFrame, year: int) -> dict[str, float]:
    """Average base, peak and off-peak price for one calendar year.

    EEX definition: Peak = Monday-Friday, 08:00-20:00 local time
    (hours starting 08:00 up to and including the hour starting 19:00).
    Off-peak = every other hour. Base = all hours.

    Return {"base": ..., "peak": ..., "offpeak": ...} in EUR/MWh.

    Hints:
      1. Convert the index to local time first: hourly.tz_convert(TZ)
      2. Select the year with .loc[str(year)]
      3. DatetimeIndex has .dayofweek (Monday = 0) and .hour
      4. Build a boolean mask for peak, then use mask and ~mask
    """
    local = hourly.tz_convert(TZ).loc[str(year)]
    idx = local.index
    peak = (
        (idx.dayofweek  < 5)
        & (idx.hour >= 8)
        & (idx.hour < 20)
    )

    prices = local["price_eur_mwh"]

    return {
        "base": prices.mean(),
        "peak": prices[peak].mean(),
        "offpeak": prices[~peak].mean()
    }

# --------------------------------------------------------------------------- #
# Exercise 2: the extreme hours
# --------------------------------------------------------------------------- #
def extreme_hours(hourly: pd.DataFrame, year: int) -> dict[str, object]:
    """Lowest and highest hourly price of a year, with their local start times.

    Return {"min_time": Timestamp, "min_price": float,
            "max_time": Timestamp, "max_price": float}
    where the times are tz-aware in Europe/Berlin.

    Hints: .idxmin() / .idxmax() return the index label of the extreme value.
    Afterwards, look up solar, wind and load at those hours in
    power_hourly.parquet and explain the prices with the merit order
    (write your explanation in the docstring of `main` below).
    """
    local = hourly.tz_convert(TZ).loc[str(year)]
    prices = local["price_eur_mwh"]
    min_time = prices.idxmin()
    max_time = prices.idxmax()
    return {
        "min_time": min_time,
        "min_price": float(prices.loc[min_time]),
        "max_time": max_time,
        "max_price": float(prices.loc[max_time]),
    }





# --------------------------------------------------------------------------- #
# Exercise 3: units drill
# --------------------------------------------------------------------------- #
def solar_twh(power_15min: pd.DataFrame, year: int) -> float:
    """Total German public net solar generation in one year, in TWh.

    The data is average POWER (MW) per 15-minute interval.
    Energy per interval = MW x 0.25 h = MWh.  1 TWh = 1,000,000 MWh.

    Pitfall to avoid: summing MW values directly gives a number 4x too large
    (and with the wrong unit).
    """
    local = power_15min.tz_convert(TZ).loc[str(year)]
    solar_mw = local["solar_mw"]
    return solar_mw.sum() * 0.25 / 1_000_000


def main() -> None:
    """Print your answers.

    My merit-order explanation of the two extreme hours (Exercise 2):
    - Lowest hour: On a sunny Sunday, solar generation (42 GW) exceeded total
      demand (40 GW). The surplus pushed the price below zero because subsidised
      and inflexible plants kept producing and there was too little storage,
      export or flexible demand.
    - Highest hour: On a winter weekday evening there was no sun and little wind
      (4.5 GW) against 71 GW of demand, so the market had to use the most
      expensive plants (gas peakers, oil, imports); the marginal plant set the
      price for everyone.
    """
    hourly = load_hourly_prices()
    print("Exercise 1:", {k: round(v, 2) for k, v in peak_base(hourly, 2025).items()})
    print("Exercise 2:", extreme_hours(hourly, 2025))
    print("Exercise 3:", round(solar_twh(load_power_15min(), 2025), 1), "TWh")


if __name__ == "__main__":
    main()
