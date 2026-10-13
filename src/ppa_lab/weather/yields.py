"""Annual energy per weather year and the P50 / P90 statistics of volume risk.

P50 is the annual energy exceeded in half of all years; P90 the energy exceeded in 90%
of years. With a normal approximation over the weather years:
    P90 (one year)       = mean - 1.2816 * std
    P90 (10-year mean)   = mean - 1.2816 * std / sqrt(10)   (years assumed independent)
Lenders size debt on P90 or P99; a 10-year average is far less uncertain than one year.
"""

from __future__ import annotations

import math

import pandas as pd

from ppa_lab.timeutils import interval_minutes

Z90 = 1.2815515655446004  # standard normal quantile for 90 %


def annual_energy(mw: pd.Series, tz: str, min_coverage: float = 0.999) -> pd.Series:
    """MWh per local calendar year; years with less than `min_coverage` of their hours
    present are left out (a partial year is not a weather year)."""
    hours = interval_minutes(mw.index) / 60.0
    year = pd.Index(mw.index.tz_convert(tz).year, name="year")
    energy = (mw * hours).groupby(year).sum()
    covered = hours.groupby(year).sum()
    expected = pd.Series(
        {y: (pd.Timestamp(f"{y + 1}-01-01", tz=tz) - pd.Timestamp(f"{y}-01-01", tz=tz))
         / pd.Timedelta(hours=1) for y in covered.index}
    )
    return energy[covered / expected >= min_coverage].rename("energy_mwh")


def p_values(annual: pd.Series) -> dict[str, float]:
    """Mean, median (P50), std, coefficient of variation, P90 for 1 and 10 years."""
    mean, std = float(annual.mean()), float(annual.std(ddof=1))
    return {
        "years": int(annual.count()),
        "mean": mean,
        "p50": float(annual.median()),
        "std": std,
        "cov": std / mean,
        "p90_1y": mean - Z90 * std,
        "p90_10y": mean - Z90 * std / math.sqrt(10),
        "min": float(annual.min()),
        "min_year": int(annual.idxmin()),
        "max": float(annual.max()),
        "max_year": int(annual.idxmax()),
    }
