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
SOLAR_MWP, WIND_MW = 114.0, 28.5  # park capacities from config/project.toml


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
       (mean MW / 28.5 MW).
    2. Subtract each month's mean from both (so the season and the gas price drop out).
    3. slope = sum(w * p) / sum(w^2) on these anomalies (EUR/MWh per unit of capacity factor);
       return it per 0.1 capacity factor, and the correlation of the two anomaly series.

    Return {"eur_per_0.1_cf": ..., "correlation": ...}.
    """
     """Slope and correlation of daily prices on wind capacity factor."""
    price = prices["price_eur_mwh"].copy()
    generation = wind["mw"].copy()

    # Convert timestamps to German local time before grouping into days.
    price.index = price.index.tz_convert(TZ)
    generation.index = generation.index.tz_convert(TZ)

    daily_price = price.groupby(price.index.date).mean()
    daily_cf = generation.groupby(generation.index.date).mean() / WIND_MW

    daily = pd.DataFrame({
        "price": daily_price,
        "wind": daily_cf,
    })
    daily.index = pd.to_datetime(daily.index)
    daily = daily.loc[daily.index.year == year].dropna()

    # Remove monthly means to control for seasonality and monthly price levels.
    anomalies = daily - daily.groupby(daily.index.month).transform("mean")
    w = anomalies["wind"]
    p = anomalies["price"]

    denominator = (w ** 2).sum()
    slope = (w * p).sum() / denominator if denominator else float("nan")
    correlation = w.corr(p)

    return {
        "eur_per_0.1_cf": float(slope * 0.1),
        "correlation": float(correlation),
    }


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
     """Return the k nearest weather analog dates."""
    target = pd.Timestamp(target).normalize()
    target_features = features.loc[target]

    # Seasonal distance, wrapping around the end of the year.
    target_doy = target.dayofyear
    candidate_doy = features.index.dayofyear
    gap = abs(candidate_doy - target_doy)
    gap = pd.Series(
        gap,
        index=features.index,
    )
    gap = gap.where(gap <= 365 - gap, 365 - gap)

    day_distance = abs((features.index - target).days)
    mask = (gap <= window) & (day_distance >= exclude)
    candidates = features.loc[mask].copy()

    if candidates.empty:
        return []

    # Standardize each feature using the standard deviation over all rows.
    std = features.std()
    std = std.replace(0, float("nan"))

    distances = (
        (candidates - target_features) / std
    ).pow(2).sum(axis=1)

    # Stable sorting preserves the original order for tied distances.
    order = distances.sort_values(kind="stable").head(k)
    return [pd.Timestamp(d) for d in order.index]


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
     """Calculate scenario-weighted pay-as-produced fair prices."""
    parks = ["solar_park", "wind_park"]
    price_types = ["independent", "linked"]
    result = pd.DataFrame(
        index=parks,
        columns=price_types,
        dtype=float,
    )

    for park in parks:
        mwh_col = f"{park}_mwh"
        revenue_col = f"{park}_revenue_eur"

        for price_type in price_types:
            subset = table.loc[table["prices"] == price_type]
            total_mwh = subset[mwh_col].sum()
            total_revenue = subset[revenue_col].sum()

            result.loc[park, price_type] = (
                total_revenue / total_mwh
                if total_mwh != 0
                else float("nan")
            )

    return result


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): the colleague's wind offer
# --------------------------------------------------------------------------- #
# A colleague prices the 28.5 MW wind park's 2027 pay-as-produced PPA with the Step 5 model
# (prices independent of the weather) and offers 148 EUR/MWh. The Step 6 scenarios say 129.
# In 3-5 sentences: why is 148 too generous, why is the solar error smaller in the Step 6
# report (about 3 EUR/MWh), and why might the true solar error still be larger (look at the
# sensitivity table: which historical days represent 2027?)?
#
# Your answer:
#The 148 EUR/MWh wind offer is too generous because the Step 5 model assumes prices are 
#independent of weather and generation, missing the price impact when wind output is high; 
#the linked scenarios put the fair price at 129 EUR/MWh. The solar error is smaller in the 
#Step 6 report (about 3 EUR/MWh) because the scenario-based calculation captures more of the 
#relationship between solar production and prices. However, the true solar error could be larger 
#if the historical days used to represent 2027 underrepresent high-solar-output days with frequent
#negative prices. The sensitivity table should reveal which historical days drive the 2027 result 
#and whether those days adequately capture solar cannibalization.
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
