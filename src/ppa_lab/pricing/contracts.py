"""Cash flows of PPA structures, seen from the producer, interval by interval.

Conventions (see METHODOLOGY.md for the maths):
- prices P_t in EUR/MWh, energy q_t in MWh per interval, cash flows in EUR;
- positive = money to the producer (Encavis' side of the deal);
- every function returns one cash flow per interval, in the shape of its inputs, so the
  caller decides how to aggregate (by month, year or scenario);
- inputs are either pandas Series on one time grid (one history) or NumPy arrays of shape
  (scenarios, intervals) for Monte Carlo; scalars such as the strike broadcast.

The producer is assumed to sell its physical output on the spot market unless the
contract says otherwise, so a structure is "spot revenue + financial settlement".
"""

from __future__ import annotations

from typing import TypeVar

import numpy as np
import pandas as pd

Values = TypeVar("Values", np.ndarray, pd.Series)


def _check_same_grid(*series: object) -> None:
    """pandas would align different indexes silently and return NaNs; refuse instead."""
    indexes = [s.index for s in series if isinstance(s, pd.Series)]
    if any(not idx.equals(indexes[0]) for idx in indexes[1:]):
        raise ValueError("prices and volumes must be on the same time grid (same index)")


def merchant(prices: Values, volumes: Values) -> Values:
    """No contract: all energy sold at the spot price. Cash flow P_t * q_t."""
    _check_same_grid(prices, volumes)
    return prices * volumes


def pay_as_produced(
    prices: Values, volumes: Values, strike: float, pay_at_negative_prices: bool = True
) -> Values:
    """Physical pay-as-produced PPA: the buyer takes every MWh at the fixed strike K.

    Cash flow K * q_t. With pay_at_negative_prices=False (a common negative-price
    clause) the buyer pays nothing in intervals with P_t < 0; the producer is assumed
    to curtail then, so it earns nothing for that energy.
    """
    _check_same_grid(prices, volumes)
    if pay_at_negative_prices:
        return strike * volumes
    return strike * volumes * (prices >= 0)


def cfd(prices: Values, volumes: Values, strike: float) -> Values:
    """Virtual PPA (two-sided contract for difference) on the produced volume.

    The producer sells on spot (P_t q_t) and settles (K - P_t) q_t with the buyer, so it
    receives K q_t whatever the price: the same cash flow as a physical PaP PPA.
    """
    _check_same_grid(prices, volumes)
    return prices * volumes + (strike - prices) * volumes


def collar(
    prices: Values, volumes: Values, floor: float | None = None, cap: float | None = None
) -> Values:
    """Spot sale plus a floor (bought put strip) and/or a cap (sold call strip).

    The producer receives max(P_t, F) with a floor, min(P_t, C) with a cap and
    clip(P_t, F, C) with both, per MWh and per interval. Option premiums are not
    included: they are what the floor or cap is worth (priced later by Monte Carlo).
    """
    _check_same_grid(prices, volumes)
    if floor is not None and cap is not None and floor > cap:
        raise ValueError(f"floor ({floor}) must not be above the cap ({cap})")
    effective = prices
    if floor is not None:
        effective = np.maximum(effective, floor)
    if cap is not None:
        effective = np.minimum(effective, cap)
    return effective * volumes


def baseload(prices: Values, volumes: Values, strike: float, band_mwh: float) -> Values:
    """Baseload (band) PPA: the producer delivers a constant band B every interval.

    It is paid K B and settles the residual (q_t - B) on the spot market: surplus is
    sold, shortfall bought. Cash flow K B + (q_t - B) P_t = merchant + B (K - P_t),
    i.e. a baseload PPA is merchant revenue plus a baseload swap: it fixes the price
    level but leaves the profile (shape) risk with the producer.
    """
    _check_same_grid(prices, volumes)
    return strike * band_mwh + (volumes - band_mwh) * prices


def fair_pay_as_produced_price(
    prices: np.ndarray | pd.Series,
    volumes: np.ndarray | pd.Series,
    discount: np.ndarray | pd.Series | float = 1.0,
) -> float:
    """Break-even pay-as-produced strike K* = E[sum D q P] / E[sum D q].

    Over all scenarios and intervals at once: a ratio of expectations, not the average
    of each scenario's capture price. With D = 1 and one history this is the capture price.
    """
    _check_same_grid(prices, volumes)
    weights = np.asarray(discount * volumes, dtype="float64")
    return float((weights * np.asarray(prices)).sum() / weights.sum())


def fair_baseload_price(
    prices: np.ndarray | pd.Series, discount: np.ndarray | pd.Series | float = 1.0
) -> float:
    """Break-even baseload strike K_B* = E[sum D P] / E[sum D]: the (discounted) base price."""
    weights = np.broadcast_to(np.asarray(discount, dtype="float64"), np.shape(prices))
    return float((weights * np.asarray(prices)).sum() / weights.sum())


def discount_factors(
    times: pd.DatetimeIndex, valuation: pd.Timestamp, rate: float
) -> np.ndarray:
    """Annually compounded discount factors D_t = (1 + r) ** -tau, tau in years (365.25 days)."""
    tau = (times - valuation) / pd.Timedelta(days=365.25)
    return (1.0 + rate) ** -np.asarray(tau, dtype="float64")
