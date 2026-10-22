"""Step 7 exercises: pricing and risk. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q                  # automatic checks
    .venv/bin/python exercises/step07_pricing.py   # print your answers

Rules of the game
- Exercise 1 uses scenarios_2027.parquet (written by `make scenarios`): one row per scenario,
  rows with prices == "linked" are the weather-linked scenarios.
- Exercises 2 and 3 need no data (Exercise 3 uses the toy market below).
- Do not import ppa_lab.pricing or ppa_lab.analysis: write the formulas yourself.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def load_scenarios() -> pd.DataFrame:
    """Given: the Step 6 per-scenario results."""
    return pd.read_parquet(PROCESSED / "scenarios_2027.parquet")


def toy_market() -> tuple[np.ndarray, np.ndarray]:
    """Given: 300 scenarios x one week of hours. Prices = a level that differs between
    scenarios minus a midday dip that is deeper on sunny scenarios; volumes = a 114 MW solar
    park (Borrentin's size) whose output follows the same sunshine. Returns (prices, volumes), both
    (scenarios, hours), in EUR/MWh and MWh."""
    rng = np.random.default_rng(7)
    hours = np.arange(24 * 7)
    solar = np.clip(np.sin(2 * np.pi * (hours % 24 - 6) / 24), 0, None)
    level = 85 + 15 * rng.standard_normal((300, 1))
    sun = 1 + 0.25 * rng.standard_normal((300, 1))
    return level - 30 * sun * solar[None, :], 114 * sun * solar[None, :]


# --------------------------------------------------------------------------- #
# Exercise 1: how much risk does a PPA take away?
# --------------------------------------------------------------------------- #
def cash_flow_at_risk(table: pd.DataFrame, park: str = "solar_park") -> dict[str, float]:
    """The producer's 95% cash flow at risk (EUR) with and without a pay-as-produced PPA.

    Use the linked scenarios only. Per scenario:
      merchant revenue = <park>_revenue_eur
      PPA revenue      = K * <park>_mwh, with K = sum(revenue) / sum(MWh) (the fair price)
    CFaR95 = mean - 5% quantile (np.quantile(x, 0.05)).
    Return {"merchant": ..., "pay_as_produced": ...}.
    """
    raise NotImplementedError("Exercise 1")


# --------------------------------------------------------------------------- #
# Exercise 2: one price for ten years
# --------------------------------------------------------------------------- #
def tenor_price(fair_price: float, forward: float, energy_mwh: float, start_year: int,
                years: int, rate: float, drift: float = 0.0, degradation: float = 0.0) -> float:
    """Discounted, energy-weighted fair price of a multi-year pay-as-produced PPA.

    Year i = 0 .. years-1:
      capture rate c_i = fair_price / forward + drift * i
      fair price   K_i = forward * c_i
      energy       E_i = energy_mwh * (1 - degradation) ** i
      discount     D_i = (1 + rate) ** -(i + 0.5)       (cash at mid-year)
    Tenor price = sum(D_i E_i K_i) / sum(D_i E_i).
    """
    raise NotImplementedError("Exercise 2")


# --------------------------------------------------------------------------- #
# Exercise 3: the buyer's premium, with and without a hedge
# --------------------------------------------------------------------------- #
def buyer_premium(prices: np.ndarray, volumes: np.ndarray, hedge: bool) -> float:
    """The buyer's risk premium per expected MWh for a pay-as-produced PPA at the fair price.

    K = sum(prices * volumes) / sum(volumes) over all scenarios and hours.
    Buyer's value per scenario: V = sum over hours of volumes * (prices - K).
    With hedge=True the buyer has also sold a baseload band at F = mean of all prices, of
    B = (mean total volume per scenario) / (number of hours) MW:
      V += B * sum over hours of (F - prices).
    Premium = (mean(V) - 5% quantile of V) / mean total volume per scenario.
    """
    raise NotImplementedError("Exercise 3")


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): the price negotiation
# --------------------------------------------------------------------------- #
# The buyer offers 45 EUR/MWh for ten years of the solar park's output. Your CFO says the
# fair price is 55 and asks why you would ever accept less. In 3-5 sentences: what are the
# 10.8 EUR/MWh between the two numbers, why is the premium AFTER the baseload hedge the right
# one to concede (and not the 28.9 EUR/MWh without it), and which assumption in the Step 7
# sensitivity table would you challenge first before signing?
#
# Your answer:
#
#


if __name__ == "__main__":
    table = load_scenarios()
    for park in ("solar_park", "wind_park"):
        r = cash_flow_at_risk(table, park)
        print(f"Ex 1  {park}: CFaR95 merchant EUR {r['merchant'] / 1e6:.2f} m, "
              f"pay-as-produced EUR {r['pay_as_produced'] / 1e6:.2f} m")
    print("Ex 2  10-year price, capture rate -1 pp per year:",
          round(tenor_price(41.08, 85.42, 55_000, 2027, 10, 0.06, -0.01, 0.005), 2), "EUR/MWh")
    p, q = toy_market()
    print(f"Ex 3  premium without hedge {buyer_premium(p, q, False):.2f}, "
          f"with baseload hedge {buyer_premium(p, q, True):.2f} EUR/MWh")
