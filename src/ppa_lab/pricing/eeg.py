"""The EEG market premium as an option (roadmap item 5): what the subsidy is worth against a PPA.

Under the EEG market premium model a park sells its output at spot (through a direct marketer)
and the grid operator adds, per MWh, the market premium of the month

    MP_m = max(AW - MW_m, 0)

with AW the park's award value ("anzulegender Wert") and MW_m the month's market value of its
technology: the capture price of all German onshore wind in that month, published by the TSOs.
So the park holds a strip of monthly puts on the onshore market value, struck at AW. Under some
EEG versions MW is the annual value (one put per year), which is worth less: shown as a
sensitivity. No premium is paid at negative prices (§51 EEG); the park curtails then.

The scenarios simulate the park, not all German wind. The month's market value is proxied by
the park's own capture price that month times the historical ratio of the official value to
the park's capture price (`basis_ratio`: 0.968 in 2023-2026, the site earns a little more than
the national average).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_lab.pricing.risk import curtail


def month_codes(index: pd.DatetimeIndex, tz: str) -> np.ndarray:
    """Local calendar month (1-12) of every hour."""
    return np.asarray(index.tz_convert(tz).month)


def market_premium(prices: np.ndarray, volumes: np.ndarray, months: np.ndarray, award: float,
                   basis: float = 1.0, reference: str = "month",
                   curtail_below: float | None = 0.0) -> np.ndarray:
    """Market premium per scenario (EUR): sum over the reference periods of
    max(award - basis x the park's capture price, 0) x the output delivered (curtailed below
    `curtail_below`). `prices`, `volumes`: scenarios x hours; `months`: month of each hour;
    `reference`: "month" or "year"."""
    if reference not in ("month", "year"):
        raise ValueError(f"reference must be 'month' or 'year', not {reference!r}")
    sold = curtail(prices, volumes, curtail_below)
    periods = [months == m for m in np.unique(months)] if reference == "month" else [
        np.ones(prices.shape[1], dtype=bool)]
    premium = np.zeros(prices.shape[0])
    for hours in periods:
        q = volumes[:, hours]
        value = basis * (prices[:, hours] * q).sum(axis=1) / np.maximum(q.sum(axis=1), 1e-9)
        premium += np.maximum(award - value, 0.0) * sold[:, hours].sum(axis=1)
    return premium


def eeg_revenue(prices: np.ndarray, volumes: np.ndarray, months: np.ndarray, award: float,
                basis: float = 1.0, reference: str = "month",
                curtail_below: float | None = 0.0) -> np.ndarray:
    """Annual revenue per scenario under the EEG (EUR): spot sale of the delivered output plus
    the market premium (before the direct marketer's fee)."""
    sold = curtail(prices, volumes, curtail_below)
    return (prices * sold).sum(axis=1) + market_premium(prices, volumes, months, award, basis,
                                                        reference, curtail_below)


def basis_ratio(official: pd.Series, prices: pd.Series, generation: pd.Series, tz: str,
                start: str | None = None) -> dict:
    """Ratio of the official monthly market value (EUR/MWh, PeriodIndex of months) to the
    park's own capture price in the same month (hourly `prices` and `generation`, UTC), from
    `start` (e.g. "2023-01") on: mean, standard deviation, months, and the monthly table."""
    q = generation.reindex(prices.index)
    ok = q.notna().to_numpy()
    p, q = prices[ok], q[ok]
    month = pd.PeriodIndex(p.index.tz_convert(tz).tz_localize(None), freq="M")
    park = (p * q).groupby(month).sum() / q.groupby(month).sum()
    table = pd.DataFrame({"official": official, "park": park}).dropna()
    if start is not None:
        table = table[table.index >= pd.Period(start, "M")]
    table["ratio"] = table["official"] / table["park"]
    return {"mean": float(table["ratio"].mean()), "sd": float(table["ratio"].std()),
            "months": len(table), "table": table}


def official_market_values(path, column: str) -> pd.Series:
    """Official monthly market values from the reference CSV (ct/kWh) in EUR/MWh."""
    frame = pd.read_csv(path, comment="#")
    return pd.Series(frame[column].to_numpy() * 10.0,
                     index=pd.PeriodIndex(frame["month"], freq="M"), name=column)
