"""Hedging with futures: forwards, payoffs, minimum-variance hedges, strategies, back-test.

Selling h MW of a product at forward F pays, per scenario, h * sum over the product's
hours of (F - P_t): the seller gains when spot ends below the forward. A hedge is the vector
h over products that is added to a position's cash flow (METHODOLOGY section 11).

The minimum-variance hedge minimises Var(cash + payoffs @ h): a least-squares regression of
the cash flow on the product payoffs, the classic hedge ratio Cov / Var generalised to
several products.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_lab.hedging.products import MONTHS, QUARTERS
from ppa_lab.pricing.risk import QUANTILE, buyer_value, cash_flow_at_risk, premium

# The rows of hedge_strategies, with readable names for reports and the dashboard.
STRATEGIES = {
    "none": "No hedge (merchant)",
    "cal_base_50": "Cal base, 50% of average output",
    "cal_base_100": "Cal base, 100% of average output",
    "cal_base_min_variance": "Cal base, minimum-variance",
    "quarters_min_variance": "Quarters, minimum-variance",
    "months_min_variance": "Months, minimum-variance",
}


def model_forwards(prices: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, float]:
    """Expected average price of each product over the scenarios (the model's forward)."""
    return {name: float(prices[:, mask].mean()) for name, mask in masks.items()}


def hedge_payoffs(prices: np.ndarray, masks: dict[str, np.ndarray], forwards: dict[str, float],
                  products: list[str]) -> np.ndarray:
    """Payoff of selling 1 MW of each product, per scenario: (scenarios, products), EUR."""
    return np.column_stack([(forwards[p] - prices[:, masks[p]]).sum(axis=1) for p in products])


def min_variance_hedge(cash: np.ndarray, payoffs: np.ndarray) -> np.ndarray:
    """MW per product that minimise the variance of cash + payoffs @ h."""
    x = payoffs - payoffs.mean(axis=0)
    y = cash - cash.mean()
    h, *_ = np.linalg.lstsq(x, -y, rcond=None)
    return h


def _row(cash: np.ndarray, hedged: np.ndarray, hedge_mw: float, average_mw: float,
         quantile: float) -> dict:
    return {
        "hedge_mw": hedge_mw, "hedge_ratio": hedge_mw / average_mw,
        "expected_eur": float(hedged.mean()), "cfar_eur": cash_flow_at_risk(hedged, quantile),
        "cfar_reduction": 1.0 - cash_flow_at_risk(hedged, quantile)
        / cash_flow_at_risk(cash, quantile),
        "effectiveness": 1.0 - hedged.var() / cash.var(),
    }


def hedge_strategies(cash: np.ndarray, prices: np.ndarray, masks: dict[str, np.ndarray],
                     forwards: dict[str, float], average_mw: float,
                     quantile: float = QUANTILE) -> pd.DataFrame:
    """No hedge, 50% and 100% of the average output as Cal base, and minimum-variance hedges
    with Cal base, quarters and months (whichever products are in `masks`).

    hedge_mw is the average MW sold over the year; hedge_ratio = hedge_mw / average_mw.
    """
    rows = {"none": _row(cash, cash, 0.0, average_mw, quantile)}
    base = hedge_payoffs(prices, masks, forwards, ["cal_base"])[:, 0]
    for share in (0.5, 1.0):
        rows[f"cal_base_{share * 100:.0f}"] = _row(cash, cash + share * average_mw * base,
                                                   share * average_mw, average_mw, quantile)
    families = {"cal_base_min_variance": ["cal_base"],
                "quarters_min_variance": [q for q in QUARTERS if q in masks],
                "months_min_variance": [m for m in MONTHS if m in masks]}
    for name, products in families.items():
        if not products:
            continue
        payoff = hedge_payoffs(prices, masks, forwards, products)
        h = min_variance_hedge(cash, payoff)
        hours = np.array([masks[p].sum() for p in products], dtype="float64")
        mean_mw = float((h * hours).sum() / masks["cal_base"].sum())   # MW averaged over the year
        rows[name] = _row(cash, cash + payoff @ h, mean_mw, average_mw, quantile)
        rows[name]["products_mw"] = dict(zip(products, h.round(3).tolist(), strict=True))
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("strategy")


def buyer_hedge(prices: np.ndarray, volumes: np.ndarray,
                quantile: float = QUANTILE) -> dict[str, float]:
    """The PPA buyer's premium with a full baseload band (Step 7) and with the
    minimum-variance band, both sold at the average price."""
    energy = volumes.sum(axis=1)
    hours = prices.shape[1]
    k = float((prices * volumes).sum() / volumes.sum())
    forward = float(prices.mean())
    band = float(energy.mean()) / hours
    unhedged = buyer_value(prices, volumes, k)
    payoff = (forward - prices).sum(axis=1)
    h = float(min_variance_hedge(unhedged, payoff[:, None])[0])
    return {
        "band_mw": band, "min_variance_mw": h, "min_variance_ratio": h / band,
        "premium_full_band": premium(unhedged + band * payoff, energy, quantile),
        "premium_min_variance": premium(unhedged + h * payoff, energy, quantile),
    }


def backtest_hedge(prices: pd.Series, mw: pd.Series, tz: str, years: list[int],
                   hedge_mw: float) -> pd.DataFrame:
    """History: sell `hedge_mw` of Cal base for year Y at Y-1's average price (a naive
    forward proxy: real forward quotes are not in the public data used here)."""
    local_year = prices.index.tz_convert(tz).year
    rows = {}
    for y in years:
        prev, this = prices[local_year == y - 1], prices[local_year == y]
        q = mw.reindex(this.index)
        forward = float(prev.mean())
        pnl = hedge_mw * float((forward - this).sum())
        merchant = float((this * q).sum())
        rows[y] = {"forward_proxy": forward, "realised_base": float(this.mean()),
                   "merchant_revenue_eur": merchant, "hedge_pnl_eur": pnl,
                   "hedged_revenue_eur": merchant + pnl}
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("year")
