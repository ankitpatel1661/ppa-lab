"""Step 6 exercises: weather and prices together. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q                  # automatic checks
    .venv/bin/python exercises/step06_joint.py      # print your answers

Rules of the game
- Work in LOCAL time (Europe/Berlin): a "day" is a local calendar day.
- Use the processed files: prices_hourly.parquet (`price_eur_mwh`), generation_<park>.parquet
  (`mw`, MWh per hour), weather_solar_park.parquet (`temp_air_c`) and, for Exercise 3,
  scenarios_2027.parquet written by `make scenarios`.
- Do not import ppa_lab.scenarios or ppa_lab.analysis: write the formulas yourself.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TZ = "Europe/Berlin"
SOLAR_MWP, WIND_MW = 50.0, 30.0  # park capacities from config/project.toml


def load(name: str) -> pd.DataFrame:
    """A processed file by name, e.g. load('prices_hourly') or load('generation_wind_park')."""
    return pd.read_parquet(PROCESSED / f"{name}.parquet")


def daily_weather(first: str = "2024", last: str = "2025") -> pd.DataFrame:
    """Given: one row per local day: solar and wind capacity factor (mean MW / capacity) and
    mean temperature. Index: dates (DatetimeIndex, no time zone)."""
    solar = load("generation_solar_park")["mw"].tz_convert(TZ)
    wind = load("generation_wind_park")["mw"].tz_convert(TZ)
    temp = load("weather_solar_park")["temp_air_c"].tz_convert(TZ)
    frame = pd.DataFrame({
        "solar": solar.groupby(solar.index.date).mean() / SOLAR_MWP,
        "wind": wind.groupby(wind.index.date).mean() / WIND_MW,
        "temp": temp.groupby(temp.index.date).mean(),
    })
    frame.index = pd.to_datetime(frame.index)
    return frame.loc[first:last]


# --------------------------------------------------------------------------- #
# Exercise 1: how much does wind move the price?
# --------------------------------------------------------------------------- #
def wind_price_response(prices: pd.DataFrame, wind: pd.DataFrame, year: int) -> dict[str, float]:
    """Slope and correlation of the daily price on the wind park's daily capacity factor.

    1. For every local day of `year`: the mean price and the wind park's capacity factor
       (mean MW / 30 MW).
    2. Subtract each month's mean from both (so the season and the gas price drop out).
    3. slope = sum(w * p) / sum(w^2) on these anomalies (EUR/MWh per unit of capacity factor);
       return it per 0.1 capacity factor, and the correlation of the two anomaly series.

    Return {"eur_per_0.1_cf": ..., "correlation": ...}.
    """
    raise NotImplementedError("Exercise 1")


# --------------------------------------------------------------------------- #
# Exercise 2: analog days
# --------------------------------------------------------------------------- #
def analog_days(features: pd.DataFrame, target: pd.Timestamp, k: int = 5, window: int = 30,
                exclude: int = 0) -> list[pd.Timestamp]:
    """The k days of `features` whose weather is closest to the weather of `target`.

    - Candidates: days whose day of the year is within `window` days of the target's, in any
      year: gap = |doy_a - doy_b|, then gap = min(gap, 365 - gap).
    - Drop candidates fewer than `exclude` days away from the target (0 keeps the target).
    - Distance: sum over the columns of ((x - x_target) / std of that column)^2, with the
      standard deviation over ALL rows of `features`.
    - Return the k nearest dates, nearest first (sort with kind="stable").
    """
    raise NotImplementedError("Exercise 2")


# --------------------------------------------------------------------------- #
# Exercise 3: the fair price from scenarios
# --------------------------------------------------------------------------- #
def fair_prices(table: pd.DataFrame) -> pd.DataFrame:
    """Fair pay-as-produced price of each park, with linked and with independent prices.

    `table` is scenarios_2027.parquet: one row per scenario, a column `prices` ("linked" or
    "independent") and per park `<park>_mwh` and `<park>_revenue_eur`.
    Fair price = sum of revenue / sum of MWh over the scenarios (Step 3: E[sum qP] / E[sum q]).
    Return a DataFrame: index solar_park, wind_park; columns independent, linked.
    """
    raise NotImplementedError("Exercise 3")


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): the colleague's wind offer
# --------------------------------------------------------------------------- #
# A colleague prices the 30 MW wind park's 2027 pay-as-produced PPA with the Step 5 model
# (prices independent of the weather) and offers 145 EUR/MWh. The Step 6 scenarios say 131.
# In 3-5 sentences: why is 145 too generous, why is the solar error smaller in the Step 6
# report (about 3.5 EUR/MWh), and why might the true solar error still be larger (look at the
# sensitivity table: which historical days represent 2027?)?
#
# Your answer:
#
#


if __name__ == "__main__":
    prices, wind = load("prices_hourly"), load("generation_wind_park")
    for year in (2024, 2025):
        r = wind_price_response(prices, wind, year)
        print(f"Ex 1  {year}: {r['eur_per_0.1_cf']:+.2f} EUR/MWh per +0.1 wind CF, "
              f"correlation {r['correlation']:+.3f}")
    features = daily_weather()
    target = pd.Timestamp("2025-06-15")
    print("Ex 2  analogs of 15 Jun 2025:", [d.strftime("%Y-%m-%d") for d in
                                            analog_days(features, target, exclude=8)])
    print("Ex 3  fair prices (EUR/MWh):")
    print(fair_prices(load("scenarios_2027")).round(2))
