"""Analysis of site generation: long-term trend and checks against national data.

A site model cannot be reconciled with an official number the way prices were on Day 1
and Day 2, because nobody publishes this park's output. Instead we check that it
behaves like the real fleet: the hour-by-hour pattern correlates with national
generation of the same technology, the seasonal shape matches, and the capture rate is
in the same range.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def yield_trend(annual: pd.Series) -> dict[str, float]:
    """Linear trend of annual energy over the weather years, per decade (absolute and %)."""
    slope, _ = np.polyfit(np.asarray(annual.index, dtype="float64"), annual.to_numpy(), 1)
    return {"per_decade": 10.0 * slope, "per_decade_pct": 100.0 * 10.0 * slope / annual.mean()}


def monthly_shares(mw: pd.Series, tz: str, years: list[int]) -> pd.Series:
    """Average share of annual energy produced in each calendar month (1-12) over `years`."""
    local = mw.index.tz_convert(tz)
    frame = pd.DataFrame({"mw": mw.to_numpy(), "year": local.year, "month": local.month})
    frame = frame[frame["year"].isin(years)]
    by_month = frame.groupby(["year", "month"])["mw"].sum().unstack("month")
    shares = by_month.div(by_month.sum(axis=1), axis=0).mean()
    shares.index.name = "month"
    return shares.rename("share")


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation; NaN (without a warning) if either series is constant."""
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def site_vs_national(site_mw: pd.Series, national_mw: pd.Series, prices: pd.Series, tz: str,
                     years: list[int]) -> pd.DataFrame:
    """Per year: hourly correlation, and capture price / rate of the site vs the nation.

    All three series are hourly with a UTC index; only common hours are used.
    """
    common = site_mw.index.intersection(national_mw.index).intersection(prices.index)
    site, nat, price = site_mw[common], national_mw[common], prices[common]
    year = common.tz_convert(tz).year
    rows = {}
    for y in years:
        mask = year == y
        s, n, p = site[mask], nat[mask], price[mask]
        base = float(p.mean())
        site_cap = float((s * p).sum() / s.sum())
        nat_cap = float((n * p).sum() / n.sum())
        rows[y] = {
            "correlation": _correlation(s.to_numpy(), n.to_numpy()),
            "base_eur_mwh": base,
            "site_capture_eur_mwh": site_cap,
            "national_capture_eur_mwh": nat_cap,
            "site_capture_rate": site_cap / base,
            "national_capture_rate": nat_cap / base,
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("year")
