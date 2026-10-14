"""Step 8 exercises: hedging with futures. Fill in the three functions, then run:

    .venv/bin/pytest exercises -q                  # automatic checks
    .venv/bin/python exercises/step08_hedging.py   # print your answers

Rules of the game
- Exercise 1 uses prices_hourly.parquet (`price_eur_mwh`, index in UTC); work in local time.
- Exercises 2 and 3 use the toy market below (no data needed).
- Do not import ppa_lab.hedging or ppa_lab.analysis: write the formulas yourself.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TZ = "Europe/Berlin"


def load_hourly_prices() -> pd.DataFrame:
    """Hourly day-ahead prices, index in UTC (column 'price_eur_mwh')."""
    return pd.read_parquet(PROCESSED / "prices_hourly.parquet")


def toy_merchant() -> tuple[np.ndarray, np.ndarray, float]:
    """Given: 500 scenarios of one week for a solar park selling at spot.

    Returns (cash, payoff, average_mw):
      cash[s]    = merchant revenue of scenario s (EUR)
      payoff[s]  = payoff of SELLING 1 MW baseload for the week at the average price F,
                   i.e. sum over the hours of (F - P) (EUR per MW)
      average_mw = the park's average output (MW)
    """
    rng = np.random.default_rng(8)
    hours = np.arange(24 * 7)
    solar = np.clip(np.sin(2 * np.pi * (hours % 24 - 6) / 24), 0, None)
    level = 85 + 15 * rng.standard_normal((500, 1))
    sun = 1 + 0.2 * rng.standard_normal((500, 1))
    prices = level - 30 * sun * solar[None, :]
    volumes = 50 * sun * solar[None, :]
    cash = (prices * volumes).sum(axis=1)
    payoff = (prices.mean() - prices).sum(axis=1)
    return cash, payoff, float(volumes.sum(axis=1).mean() / len(hours))


# --------------------------------------------------------------------------- #
# Exercise 1: what did a hedge earn in a real year?
# --------------------------------------------------------------------------- #
def hedge_pnl(prices: pd.DataFrame, year: int, mw: float) -> float:
    """P&L (EUR) of selling `mw` MW of baseload for the local calendar `year` at a forward
    equal to the average hourly price of the PREVIOUS local year (a naive forward):
        mw * sum over the hours of `year` of (forward - P_h)
    """
    raise NotImplementedError("Exercise 1")


# --------------------------------------------------------------------------- #
# Exercise 2: the minimum-variance hedge
# --------------------------------------------------------------------------- #
def min_variance_mw(cash: np.ndarray, payoff: np.ndarray) -> float:
    """MW of baseload to sell so that cash + MW * payoff has the smallest variance:
        MW = - Cov(cash, payoff) / Var(payoff)
    (np.cov(cash, payoff) gives the 2 x 2 covariance matrix.)
    """
    raise NotImplementedError("Exercise 2")


# --------------------------------------------------------------------------- #
# Exercise 3: how good is a hedge?
# --------------------------------------------------------------------------- #
def effectiveness(cash: np.ndarray, payoff: np.ndarray, mw: float) -> float:
    """Share of the revenue variance a hedge of `mw` MW removes:
        1 - Var(cash + mw * payoff) / Var(cash)        (np.var, population variance)
    """
    raise NotImplementedError("Exercise 3")


# --------------------------------------------------------------------------- #
# Exercise 4 (written, no code): "just hedge 100%"
# --------------------------------------------------------------------------- #
# Your CFO says: "Sell 100% of the expected output forward, it is the simplest." In 3-5
# sentences: why is the minimum-variance amount for solar below 100% (89% in the Step 8
# report), what does selling 100% do in a sunny, cheap year, what does the 2024-2025
# back-test teach about judging a hedge by one year's P&L, and what changes if the market
# forward (about 113 EUR/MWh) is far above our expected price (85)?
#
# Your answer:
#
#


if __name__ == "__main__":
    prices = load_hourly_prices()
    for year in (2024, 2025):
        print(f"Ex 1  5 MW baseload sold for {year} at {year - 1}'s average: "
              f"EUR {hedge_pnl(prices, year, 5.0) / 1e6:+.2f} m")
    cash, payoff, average_mw = toy_merchant()
    h = min_variance_mw(cash, payoff)
    print(f"Ex 2  minimum-variance hedge {h:.2f} MW = {h / average_mw:.0%} of the average output")
    for mw in (0.5 * average_mw, average_mw, h):
        print(f"Ex 3  {mw:5.2f} MW removes {effectiveness(cash, payoff, mw):.1%} of the variance")
