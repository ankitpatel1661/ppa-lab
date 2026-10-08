"""Day 2 exercises: capture prices by hand. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q                 # automatic checks
    .venv/bin/python exercises/day02_capture.py   # print your answers

Rules of the game
- Work in LOCAL time (Europe/Berlin): a "month" or "year" is a local calendar period.
- Use the HOURLY processed files (prices_hourly, power_hourly); do not import from
  ppa_lab.analysis.capture. The point is to write the formula yourself.
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


def load_hourly_power() -> pd.DataFrame:
    """Hourly generation in MW (columns such as 'solar_mw'), index in UTC.

    Mean MW over one hour = MWh produced in that hour, so these values are energies.
    """
    return pd.read_parquet(PROCESSED / "power_hourly.parquet")


# --------------------------------------------------------------------------- #
# Exercise 1: one capture price by hand
# --------------------------------------------------------------------------- #
def capture_price_month(
    prices: pd.DataFrame, power: pd.DataFrame, column: str, year: int, month: int
) -> float:
    """Volume-weighted price (EUR/MWh) earned by one technology in one local month.

        capture price = sum(price_h * energy_h) / sum(energy_h)

    Example call: capture_price_month(prices, power, "solar_mw", 2024, 7)

    Hints:
      1. Convert both frames to local time with .tz_convert(TZ).
      2. Select the month with .loc[f"{year}-{month:02d}"].
      3. Multiply the two Series (pandas aligns them on the index), sum, divide.
    """
    prices_local = prices.tz_convert(TZ)
    power_local = power.tz_convert(TZ)

    month_str = f"{year}-{month:02d}"
    p = prices_local.loc[month_str,"price_eur_mwh"]
    e = power_local.loc[month_str,column]
    return float((p * e).sum() / e.sum())


# --------------------------------------------------------------------------- #
# Exercise 2: how much energy is produced at negative prices?
# --------------------------------------------------------------------------- #
def negative_price_energy_share(
    prices: pd.DataFrame, power: pd.DataFrame, column: str, year: int
) -> float:
    """Share (0 to 1) of a technology's energy in one local year produced in hours
    whose hourly price is below zero.

    Why it matters: since 2025, new EEG plants get no market premium in negative
    periods, and a pay-as-produced PPA buyer pays the fixed price for these MWh
    although they are worth less than nothing on the spot market.

    Hints:
      1. Same selection as in exercise 1, but for a whole year: .loc[str(year)].
      2. Boolean mask: price < 0. Energy in those hours / total energy.
    """
    prices_local = prices.tz_convert(TZ).loc[str(year)]
    power_local = power.tz_convert(TZ).loc[str(year)]

    p = prices_local["price_eur_mwh"]
    e = power_local[column]
    negative = p<0
    return float(e[negative].sum()/e.sum())


# --------------------------------------------------------------------------- #
# Exercise 3: the profile cost in euros
# --------------------------------------------------------------------------- #
def profile_cost_eur_bn(prices: pd.DataFrame, power: pd.DataFrame, column: str, year: int) -> float:
    """How much less (in billion EUR) all German plants of one technology earned in one
    local year than if their energy had been sold at the baseload price:

        profile cost = (base price - capture price) * energy

    Base price = simple mean of the hourly prices of that year (time-weighted).
    Units: EUR/MWh * MWh = EUR; divide by 1e9 for EUR bn.

    Hints:
      1. Reuse your logic from exercise 1 for the capture price of the year.
      2. Energy in MWh = sum of the hourly MW values.
    """
    prices_local = prices.tz_convert(TZ).loc[str(year)]
    power_local = power.tz_convert(TZ).loc[str(year)]

    p = prices_local["price_eur_mwh"]
    e = power_local[column]

    capture = (p*e).sum() / e.sum()
    base = p.mean()
    energy = e.sum()
    return float((base-capture)*energy / 1e9)


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): hourly vs quarter-hourly
# --------------------------------------------------------------------------- #
# With the hourly files, the 2025 solar capture price comes out at about 46.07 EUR/MWh.
# The Day 2 report (quarter-hourly) says 45.95 EUR/MWh. For 2024 both methods give
# exactly the same number. Explain in 3-5 sentences why, and which one the TSOs use.

# Your answer:
# Until 30 Sep 2025 the day-ahead price was hourly, so all four quarter-hours of an hour have
# the same price; then sum(price x quarter-hour energy) = price x hourly energy, and the hourly
# and quarter-hourly methods are mathematically identical (2024: 35.82 both ways in July).
# From 1 Oct 2025 each quarter-hour has its own price. Averaging prices and energy to hours
# first ignores how output and price move together inside the hour: solar ramps up while
# quarter-hour prices fall (and down while they rise), a negative within-hour covariance, so
# the hourly method overstates the solar capture price (Oct-Dec 2025: +0.7 to +1.4 EUR/MWh).
# For the whole of 2025 the gap is only 0.12 EUR/MWh because just Oct-Dec are affected and
# they carry 7 of 70 TWh of solar. The TSOs use quarter-hours, as EEG 2023 Anlage 1 requires
# ("fuer jede Viertelstunde"), and so does our report.
#Why it matters for PPA pricing
#Since quarter-hour prices started, pricing solar with hourly data overvalues it by about 1 EUR/MWh
#in every month of 2026. In April 2026 it was 20.25 against the true 19.07, about 6% too high. 
#On a 100 GWh-per-year PPA that's roughly EUR 0.1 million per year of value that doesn't exist. 
#Since October 2025 you must price renewable profiles at 15-minute resolution; hourly data overstates
#solar capture prices because of the within-hour covariance between output and price.

if __name__ == "__main__":
    prices, power = load_hourly_prices(), load_hourly_power()
    print("Ex 1  solar capture price July 2024:",
          round(capture_price_month(prices, power, "solar_mw", 2024, 7), 2), "EUR/MWh")
    print("      official MW Solar July 2024 :  35.54 EUR/MWh (3.554 ct/kWh)")
    for year in (2023, 2024, 2025):
        share = negative_price_energy_share(prices, power, "solar_mw", year)
        print(f"Ex 2  solar energy at negative prices {year}: {share:.1%}")
    for year in (2023, 2024, 2025):
        cost = profile_cost_eur_bn(prices, power, "solar_mw", year)
        print(f"Ex 3  solar profile cost {year}: {cost:.2f} bn EUR")
