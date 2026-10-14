"""Step 3 exercises: PPA structures by hand. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q              # automatic checks
    .venv/bin/python exercises/step03_ppa.py    # print your answers

Rules of the game
- Work in LOCAL time (Europe/Berlin) and with the HOURLY processed files.
- Use the national profile of a technology as "the park" (per MWh results do not depend
  on the park size).
- Do not import ppa_lab.pricing: write the cash flows yourself. Cash flows are to the
  PRODUCER (positive = money to the producer).
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
    """Hourly generation in MW = MWh per hour (columns such as 'solar_mw'), index in UTC."""
    return pd.read_parquet(PROCESSED / "power_hourly.parquet")


# --------------------------------------------------------------------------- #
# Exercise 1: a baseload PPA by hand
# --------------------------------------------------------------------------- #
def baseload_revenue_per_mwh(
    prices: pd.DataFrame, power: pd.DataFrame, column: str, year: int, strike: float
) -> float:
    """Producer revenue per MWh produced under a baseload PPA for one local year.

    The band B (MWh per hour) delivers the year's energy flat: B = total energy / hours.
    Each hour the producer is paid strike * B and settles the residual (q_h - B) at the
    spot price P_h (sells a surplus, buys a shortfall):

        cash_h = strike * B + (q_h - B) * P_h
        result = sum(cash_h) / sum(q_h)

    Example: solar, 2025, strike 78.51 (the 2024 base price, as in the Step 3 report).

    Hints:
      1. Same selection as in Step 2: tz_convert(TZ), then .loc[str(year)].
      2. B is one number for the whole year; len(series) gives the number of hours.
    """
    raise NotImplementedError("Exercise 1")


# --------------------------------------------------------------------------- #
# Exercise 2: what is a floor worth?
# --------------------------------------------------------------------------- #
def floor_value_per_mwh(
    prices: pd.DataFrame, power: pd.DataFrame, column: str, year: int, floor: float
) -> float:
    """Average payout per MWh produced of a floor at `floor` EUR/MWh in one local year.

    A floor pays (floor - P_h) for each MWh produced in hours where the price is below
    the floor, and nothing otherwise:

        payout_h = q_h * max(floor - P_h, 0)
        result   = sum(payout_h) / sum(q_h)

    This is the historical "intrinsic" value: what a producer would have paid at most
    for this protection had it known the year in advance.

    Hints:
      1. (floor - p).clip(lower=0) is max(floor - P, 0) for a whole Series.
      2. Try floor = 0 (protection against negative prices) and floor = 20.
    """
    raise NotImplementedError("Exercise 2")


# --------------------------------------------------------------------------- #
# Exercise 3: the break-even strike with a negative-price clause
# --------------------------------------------------------------------------- #
def breakeven_strike_with_clause(
    prices: pd.DataFrame, power: pd.DataFrame, column: str, year: int
) -> float:
    """Pay-as-produced strike that makes the producer exactly as well off as selling at
    spot, when the buyer pays NOTHING for energy produced at negative prices (and the
    producer curtails then).

    Merchant revenue:            sum_h q_h * P_h
    PPA revenue with the clause: K * sum of q_h over hours with P_h >= 0
    Solve "PPA revenue = merchant revenue" for K.

    Compare the result with the plain capture price of the same year (Step 2): by how
    much does the clause raise the fair strike?
    """
    raise NotImplementedError("Exercise 3")


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): same contract, opposite outcomes
# --------------------------------------------------------------------------- #
# In the Step 3 report, both parks signed a baseload PPA for 2025 at 78.51 EUR/MWh (the
# 2024 base price), and both lost 10.81 EUR/MWh against merchant (the 2025 base price
# was 89.32). Yet the surprise against plan was -11.34 EUR/MWh for the solar park and
# +1.92 EUR/MWh for the wind park. Explain in 3-5 sentences why, using "price level"
# and "shape" (capture rate), and say which kind of PPA you would offer a solar park
# that wants protection against falling prices.
#
# Your answer:
#
#


if __name__ == "__main__":
    prices, power = load_hourly_prices(), load_hourly_power()
    for column in ("solar_mw", "wind_onshore_mw"):
        print(f"--- {column}")
        print("Ex 1  baseload PPA 2025 at 78.51:",
              round(baseload_revenue_per_mwh(prices, power, column, 2025, 78.51), 2), "EUR/MWh")
        for floor in (0.0, 20.0):
            print(f"Ex 2  floor at {floor:.0f} in 2025 worth:",
                  round(floor_value_per_mwh(prices, power, column, 2025, floor), 2), "EUR/MWh")
        print("Ex 3  break-even strike with the clause, 2025:",
              round(breakeven_strike_with_clause(prices, power, column, 2025), 2), "EUR/MWh")
