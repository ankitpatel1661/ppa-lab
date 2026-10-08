"""Price statistics and reconciliation ("tie-out") against published figures.

A new data pipeline is not trusted until it reproduces numbers that someone else
has published. If our 2025 average price or negative-hour count disagrees with
the official values, either our data or our definition is wrong, and we must
find out which before building anything on top.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ppa_lab.config import Reference
from ppa_lab.timeutils import interval_minutes, to_hourly


def longest_run(flags: pd.Series) -> int:
    """Length of the longest run of consecutive True values."""
    best = current = 0
    for flag in flags.to_numpy():
        current = current + 1 if flag else 0
        best = max(best, current)
    return best


def annual_price_stats(prices: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Yearly statistics by local delivery year.

    Several definitions of "negative hours" are reported on purpose, because
    publishers differ and the 15-minute switch (Oct 2025) made the question
    ambiguous:
      negative_hours                    hourly average price < 0
      hours_with_any_negative_interval  at least one interval in the hour < 0
      negative_time_hours               total duration of negative intervals, in hours
    """
    price = prices["price_eur_mwh"]
    minutes = prices["interval_min"] if "interval_min" in prices else interval_minutes(prices.index)
    weight_h = minutes / 60.0
    year_native = prices.index.tz_convert(tz).year

    hourly = to_hourly(price).dropna()
    year_hourly = hourly.index.tz_convert(tz).year

    rows = []
    for year in sorted(set(year_native)):
        mask = year_native == year
        p, w = price[mask], weight_h[mask]
        h = hourly[year_hourly == year]
        any_negative = (p < 0).groupby(p.index.floor("h")).any()
        local = p.index.tz_convert(tz)
        rows.append(
            {
                "year": year,
                "first_day": local.min().date(),
                "last_day": local.max().date(),
                "hours": float(w.sum()),
                "mean_price_eur_mwh": float((p * w).sum() / w.sum()),
                "mean_of_hourly_prices": float(h.mean()),
                "min_price_eur_mwh": float(p.min()),
                "max_price_eur_mwh": float(p.max()),
                "negative_hours": int((h < 0).sum()),
                "hours_with_any_negative_interval": int(any_negative.sum()),
                "negative_time_hours": float(w[p < 0].sum()),
                "zero_or_negative_hours": int((h <= 0).sum()),
                "longest_negative_streak_h": longest_run(h < 0),
            }
        )
    return pd.DataFrame(rows).set_index("year")


def monthly_mean_price(prices: pd.DataFrame, tz: str) -> pd.Series:
    """Time-weighted mean price per local calendar month."""
    minutes = prices["interval_min"] if "interval_min" in prices else interval_minutes(prices.index)
    local = prices.index.tz_convert(tz)
    month = pd.PeriodIndex(local.tz_localize(None), freq="M")
    weighted = (prices["price_eur_mwh"] * minutes).groupby(month).sum()
    return (weighted / minutes.groupby(month).sum()).rename("mean_price_eur_mwh")


def hourly_profile(prices_hourly: pd.DataFrame, tz: str, years: list[int]) -> pd.DataFrame:
    """Average price for each local hour of the day (rows) and year (columns)."""
    s = prices_hourly["price_eur_mwh"].dropna()
    local = s.index.tz_convert(tz)
    frame = pd.DataFrame({"price": s.to_numpy(), "hour": local.hour, "year": local.year})
    frame = frame[frame["year"].isin(years)]
    return frame.pivot_table(index="hour", columns="year", values="price", aggfunc="mean")


def reconcile(stats: pd.DataFrame, references: tuple[Reference, ...]) -> pd.DataFrame:
    """Compare our statistics with published reference values."""
    rows = []
    for ref in references:
        ours = (
            float(stats.loc[ref.year, ref.metric])
            if ref.year in stats.index and ref.metric in stats.columns
            else math.nan
        )
        diff = ours - ref.value
        if not np.isfinite(ours):
            status = "not available"  # year not in our data range
        elif abs(diff) <= ref.tolerance:
            status = "within tolerance"
        elif ref.note:
            status = "explained difference"  # cause found and documented in the note
        else:
            status = "OUTSIDE tolerance"
        rows.append(
            {
                "metric": ref.metric,
                "year": ref.year,
                "ours": ours,
                "published": ref.value,
                "difference": diff,
                "tolerance": ref.tolerance,
                "status": status,
                "source": ref.source,
                "note": ref.note,
            }
        )
    return pd.DataFrame(rows)
