"""Day 4 exercises: from site generation to volume risk. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q                     # automatic checks
    .venv/bin/python exercises/day04_generation.py    # print your answers

Rules of the game
- Work in LOCAL time (Europe/Berlin): a "year" is a local calendar year.
- Use the processed files written by `make weather`:
  generation_solar_park.parquet / generation_wind_park.parquet (column `mw`, hourly:
  mean MW over the hour = MWh produced in that hour) and prices_hourly.parquet.
- Do not import ppa_lab.weather or ppa_lab.analysis: write the formulas yourself.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TZ = "Europe/Berlin"
SOLAR_MWP, WIND_MW = 50.0, 30.0  # park capacities from config/project.toml


def load_generation(park: str) -> pd.DataFrame:
    """Hourly park output for 'solar_park' or 'wind_park' (column 'mw'), index in UTC."""
    return pd.read_parquet(PROCESSED / f"generation_{park}.parquet")


def load_hourly_prices() -> pd.DataFrame:
    """Hourly day-ahead prices, index in UTC (column 'price_eur_mwh')."""
    return pd.read_parquet(PROCESSED / "prices_hourly.parquet")


def annual_mwh(generation: pd.DataFrame) -> pd.Series:
    """Given: MWh per complete local year (years with at least 8,759 hours)."""
    mw = generation["mw"].tz_convert(TZ)
    by_year = mw.groupby(mw.index.year)
    return by_year.sum()[by_year.size() >= 8759]


# --------------------------------------------------------------------------- #
# Exercise 1: specific yield / full-load hours
# --------------------------------------------------------------------------- #
def specific_yield(generation: pd.DataFrame, capacity_mw: float, year: int) -> float:
    """Energy of one local year divided by the capacity: MWh per MW.

    For solar this is kWh per kWp ("specific yield"); for wind it is the number of
    "full-load hours" (how many hours at full power would give the same energy).

    Hints: tz_convert(TZ), .loc[str(year)], sum the hourly MW values, divide.
    """
    raise NotImplementedError("Exercise 1")


# --------------------------------------------------------------------------- #
# Exercise 2: P50 and P90 from the weather years
# --------------------------------------------------------------------------- #
def p50_p90(annual: pd.Series) -> dict[str, float]:
    """P50 and one-year P90 of annual energy over the weather years.

    P50 = the median year. P90 (normal approximation) = mean - 1.2816 * std, with the
    SAMPLE standard deviation (ddof=1). Return {"p50": ..., "p90": ...} in MWh.

    Use only the full weather years 1995-2025: annual_mwh(...).loc[1995:2025].
    """
    raise NotImplementedError("Exercise 2")


# --------------------------------------------------------------------------- #
# Exercise 3: a solar + wind portfolio
# --------------------------------------------------------------------------- #
def portfolio_capture_rate(
    prices: pd.DataFrame, solar: pd.DataFrame, wind: pd.DataFrame, year: int
) -> float:
    """Capture rate of the two parks sold together (one combined profile) in one local year.

    combined_h = solar_h + wind_h (MWh per hour)
    capture    = sum(P_h * combined_h) / sum(combined_h)
    rate       = capture / mean(P_h over the same hours)

    Hint: align the three Series on their common hours (index.intersection) first.
    """
    raise NotImplementedError("Exercise 3")


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): one year vs ten years
# --------------------------------------------------------------------------- #
# In the Day 4 report the solar park's one-year P90 is 6.4% below the mean, but the P90
# of a 10-year AVERAGE is only 2.0% below it. Explain in 3-5 sentences why, which number
# a lender would use to size debt for a 10-year PPA, and which assumption behind the
# 10-year figure may be too optimistic (think about trends and years that are not
# independent).
#
# Your answer:
#
#


if __name__ == "__main__":
    solar, wind = load_generation("solar_park"), load_generation("wind_park")
    print("Ex 1  solar 2024:", round(specific_yield(solar, SOLAR_MWP, 2024), 1), "kWh/kWp;",
          "wind 2024:", round(specific_yield(wind, WIND_MW, 2024), 1), "full-load hours")
    for name, gen in (("solar", solar), ("wind", wind)):
        stats = p50_p90(annual_mwh(gen).loc[1995:2025])
        print(f"Ex 2  {name}: P50 {stats['p50'] / 1e3:.1f} GWh, P90 {stats['p90'] / 1e3:.1f} GWh")
    prices = load_hourly_prices()
    for year in (2024, 2025):
        print(f"Ex 3  portfolio capture rate {year}:",
              round(portfolio_capture_rate(prices, solar, wind, year), 4))
