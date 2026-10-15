"""Risk on joint scenarios (Step 7): premia, cash flow at risk, structures, tenor price.

Arrays are (scenarios, hours): prices P in EUR/MWh and volumes q in MWh per hour, all
scenarios equally likely (METHODOLOGY sections 5 and 10).

Two views of the same contract:
- the PRODUCER sells its output; its risk is the spread of its annual revenue (CFaR);
- the BUYER of a pay-as-produced PPA takes every MWh at the strike K and is worth
  sum_t q_t (P_t - K) per scenario. It sells a baseload forward against the expected
  average volume, so the price LEVEL is hedged; what is left is profile and volume risk,
  and the premium it asks for is the 5% shortfall of that value per expected MWh.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_lab.pricing.contracts import (
    baseload,
    collar,
    fair_pay_as_produced_price,
    merchant,
    pay_as_produced,
)

QUANTILE = 0.05


def cash_flow_at_risk(cash: np.ndarray, quantile: float = QUANTILE) -> float:
    """Expected cash flow minus its `quantile` (CFaR95 for 0.05)."""
    cash = np.asarray(cash, dtype="float64")
    return float(cash.mean() - np.quantile(cash, quantile))


def premium(values: np.ndarray, energy: np.ndarray, quantile: float = QUANTILE) -> float:
    """(E[value] - quantile of value) / E[energy]: the shortfall per expected MWh."""
    return cash_flow_at_risk(values, quantile) / float(np.mean(energy))


def buyer_value(prices: np.ndarray, volumes: np.ndarray, strike: float,
                forward: float | None = None, band_mw: float | None = None) -> np.ndarray:
    """Value of a pay-as-produced PPA to its buyer, per scenario: sum_t q (P - K).

    With `forward` and `band_mw` the buyer has also sold a baseload band of `band_mw` MW at
    `forward` EUR/MWh: + band * sum_t (forward - P).
    """
    value = (volumes * (prices - strike)).sum(axis=1)
    if forward is not None and band_mw is not None:
        value = value + band_mw * (forward - prices).sum(axis=1)
    return value


def risk_premia(prices: np.ndarray, volumes: np.ndarray,
                quantile: float = QUANTILE) -> dict[str, float]:
    """Fair pay-as-produced price and the buyer's premia, EUR/MWh.

    - unhedged: the buyer's 5% shortfall without any hedge (includes the price level);
    - joint: after selling a baseload band at the average price (profile + volume risk);
    - profile: the same with the EXPECTED hourly volume in every scenario (shape only);
    - volume: joint - profile, i.e. what varying volumes, and their link to prices, add.
    """
    energy = volumes.sum(axis=1)
    hours = prices.shape[1]
    forward = float(prices.mean())                  # the model's average price (forward)
    band = float(energy.mean()) / hours
    k = fair_pay_as_produced_price(prices, volumes)
    expected_profile = np.broadcast_to(volumes.mean(axis=0), prices.shape)
    k_profile = fair_pay_as_produced_price(prices, expected_profile)
    joint = premium(buyer_value(prices, volumes, k, forward, band), energy, quantile)
    profile = premium(buyer_value(prices, expected_profile, k_profile, forward, band),
                      energy, quantile)
    return {
        "fair_price": k,
        "unhedged": premium(buyer_value(prices, volumes, k), energy, quantile),
        "joint": joint,
        "profile": profile,
        "volume": joint - profile,
    }


def structure_revenues(prices: np.ndarray, volumes: np.ndarray,
                       floor: float = 0.0) -> dict[str, tuple[float | None, np.ndarray]]:
    """The producer's annual revenue per scenario under each structure, with its strike.

    pay_as_produced_clause uses the same strike as pay_as_produced (as in the Step 3
    back-test): the buyer pays nothing for output at negative prices and the producer
    curtails, so the clause costs the producer that output. merchant_floor is spot
    revenue with a bought floor, net of the floor's fair premium.
    """
    energy = volumes.sum(axis=1)
    k = fair_pay_as_produced_price(prices, volumes)
    base = float(prices.mean())
    band = float(energy.mean()) / prices.shape[1]
    floor_cost = float((volumes * np.maximum(floor - prices, 0.0)).sum(axis=1).mean())
    return {
        "merchant": (None, merchant(prices, volumes).sum(axis=1)),
        "pay_as_produced": (k, pay_as_produced(prices, volumes, k).sum(axis=1)),
        "pay_as_produced_clause": (k, pay_as_produced(prices, volumes, k,
                                                      pay_at_negative_prices=False).sum(axis=1)),
        "merchant_floor": (None, collar(prices, volumes, floor=floor).sum(axis=1) - floor_cost),
        "baseload": (base, baseload(prices, volumes, base, band).sum(axis=1)),
    }


def structure_table(prices: np.ndarray, volumes: np.ndarray, floor: float = 0.0,
                    quantile: float = QUANTILE) -> pd.DataFrame:
    """Fair price, expected and P5 revenue and CFaR of each structure (producer view)."""
    energy = volumes.sum(axis=1)
    floor_cost = float((volumes * np.maximum(floor - prices, 0.0)).sum(axis=1).mean())
    rows = {}
    for name, (strike, cash) in structure_revenues(prices, volumes, floor).items():
        expected = float(cash.mean())
        rows[name] = {
            "fair_price_eur_mwh": np.nan if strike is None else strike,
            "expected_revenue_eur": expected,
            "p05_revenue_eur": float(np.quantile(cash, quantile)),
            "cfar_eur": cash_flow_at_risk(cash, quantile),
            "cfar_share": cash_flow_at_risk(cash, quantile) / expected,
            "floor_value_eur_mwh": floor_cost / float(energy.mean()) if name == "merchant_floor"
            else np.nan,
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("structure")


def tenor_price(fair_price: float, forward: float, energy_mwh: float, start_year: int,
                years: int, discount_rate: float, capture_rate_drift: float = 0.0,
                degradation: float = 0.0,
                forward_curve: dict[int, float] | None = None) -> pd.DataFrame:
    """One price for a multi-year pay-as-produced PPA from the first year's fair price.

    Year y: forward F_y = `forward` in the first year, then `forward_curve` where it gives the
    year; a year after the last quoted one keeps that quote (flat). Capture rate
    c_y = c_0 + drift * (y - start) with c_0 = fair_price / forward, fair price F_y c_y,
    energy E_y = energy * (1 - degradation)^(y - start), discount factor (1 + r)^-(y - start
    + 0.5) at mid-year. The tenor price is sum D E K / sum D E. Returned per year, with the
    tenor price in `.attrs["price"]`.
    """
    forward_curve = forward_curve or {}
    c0 = fair_price / forward
    rows = []
    f_y = forward
    for i in range(years):
        y = start_year + i
        f_y = forward_curve.get(y, f_y)
        rows.append({
            "year": y, "forward_eur_mwh": f_y, "capture_rate": c0 + capture_rate_drift * i,
            "energy_mwh": energy_mwh * (1.0 - degradation) ** i,
            "discount_factor": (1.0 + discount_rate) ** -(i + 0.5),
        })
    table = pd.DataFrame(rows).set_index("year")
    table["fair_price_eur_mwh"] = table["forward_eur_mwh"] * table["capture_rate"]
    weights = table["discount_factor"] * table["energy_mwh"]
    table.attrs["price"] = float((weights * table["fair_price_eur_mwh"]).sum() / weights.sum())
    return table
