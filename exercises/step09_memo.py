"""Step 9 exercises: telling the result. Fill in the two functions, then run:

    .venv/bin/pytest exercises -q                # automatic checks
    .venv/bin/python exercises/step09_memo.py    # print your answers

Rules of the game
- Exercise 1 uses reports/results.json (committed; written by `make memo`).
- Exercise 2 uses data/processed/scenarios_2027.parquet (written by `make scenarios`).
- Do not import ppa_lab.dashboard or ppa_lab.analysis: write the formulas yourself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def load_results() -> dict:
    """Given: the Step 7 results the dashboard and the memo use."""
    return json.loads((ROOT / "reports" / "results.json").read_text())


def load_scenarios() -> pd.DataFrame:
    """Given: the Step 6 per-scenario results."""
    return pd.read_parquet(PROCESSED / "scenarios_2027.parquet")


# --------------------------------------------------------------------------- #
# Exercise 1: the dashboard's first number, by hand
# --------------------------------------------------------------------------- #
def indicative_price(results: dict, park: str, balancing: float, credit: float) -> float:
    """First-year indicative pay-as-produced price for your own cost assumptions.

    Take results["parks"][park]["stack_eur_mwh"] and compute
        fair_price - risk_premium - balancing - credit     (EUR/MWh).
    """
    raise NotImplementedError("Exercise 1")


# --------------------------------------------------------------------------- #
# Exercise 2: how often does the PPA beat merchant sales?
# --------------------------------------------------------------------------- #
def ppa_beats_merchant(table: pd.DataFrame, park: str = "solar_park") -> float:
    """Share of the linked scenarios in which the PPA earns more than selling at spot.

    Use rows with prices == "linked". Fair strike K = sum(revenue) / sum(MWh) over them;
    the PPA earns K * MWh per scenario, merchant earns <park>_revenue_eur.
    Return the share of scenarios with PPA revenue > merchant revenue (0 to 1).
    """
    raise NotImplementedError("Exercise 2")


# --------------------------------------------------------------------------- #
# Exercise 3 (written, no code): the three-sentence summary
# --------------------------------------------------------------------------- #
# Write the summary you would send to a managing director who has 30 seconds: what price,
# what it buys us, what could change it. No jargon (no "capture rate", no "CFaR"). Then the
# first sentence once more in German.
#
# Your answer:
#
#


if __name__ == "__main__":
    results = load_results()
    print("Ex 1  solar, base costs:", round(indicative_price(results, "solar_park", 1.5, 1.0), 2),
          "EUR/MWh; wind with 3.0 and 2.0:",
          round(indicative_price(results, "wind_park", 3.0, 2.0), 2), "EUR/MWh")
    table = load_scenarios()
    for park in ("solar_park", "wind_park"):
        print(f"Ex 2  {park}: the PPA beats merchant in {ppa_beats_merchant(table, park):.0%} "
              "of the scenarios")
