"""Capture prices and capture rates: what a generation profile really earns.

A solar park does not earn the average (baseload) price. It sells its output when
the sun shines, and those are exactly the hours in which all other solar parks
produce too, so prices are low. The volume-weighted price it actually receives is
its CAPTURE PRICE:

    capture price = sum_t(price_t * energy_t) / sum_t(energy_t)
    capture rate  = capture price / baseload price        (also called value factor)

This is the same formula the German TSOs use for the official market values
("Marktwerte", EEG 2023 Anlage 1 Nr. 3.3 and 4.3): every quarter-hour's spot price
times the energy produced in that quarter-hour, summed, divided by total energy.
So the official numbers are a free, independent check of this module.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ppa_lab.timeutils import interval_minutes

# Technology name -> generation column in the processed power datasets.
TECHNOLOGIES: dict[str, str] = {
    "solar": "solar_mw",
    "wind_onshore": "wind_onshore_mw",
    "wind_offshore": "wind_offshore_mw",
}


def capture_price(prices: pd.Series, generation: pd.Series) -> float:
    """Volume-weighted average price in EUR/MWh.

    Both series must share one regular time grid (e.g. 15 minutes), so that
    generation in MW is proportional to energy per interval. Intervals where
    either value is missing are ignored.
    """
    if not prices.index.equals(generation.index):
        raise ValueError(
            "prices and generation must be on the same time grid; "
            "map prices onto the generation grid with prices_on_grid() first"
        )
    valid = prices.notna() & generation.notna()
    energy = generation[valid]
    if energy.sum() <= 0:
        raise ValueError("no generation in the period: the capture price is undefined")
    return float((prices[valid] * energy).sum() / energy.sum())


def capture_rate(prices: pd.Series, generation: pd.Series) -> float:
    """Capture price divided by the time-weighted (baseload) price of the same period."""
    return capture_price(prices, generation) / float(prices.mean())


def prices_on_grid(prices: pd.DataFrame, grid: pd.DatetimeIndex) -> pd.Series:
    """Price in force at each timestamp of a finer grid.

    Day-ahead prices were hourly until 30 Sep 2025 and are quarter-hourly since,
    while generation is quarter-hourly throughout. Each grid timestamp gets the
    price of the delivery interval that contains it, so an hourly price is
    repeated for its four quarters. Timestamps not covered by any published
    interval stay NaN (no forward-filling across gaps).
    """
    minutes = prices["interval_min"] if "interval_min" in prices else interval_minutes(prices.index)
    pos = prices.index.searchsorted(grid, side="right") - 1
    safe = pos.clip(min=0)
    starts = prices.index[safe]
    ends = starts + pd.to_timedelta(minutes.to_numpy()[safe], unit="min")
    covered = (pos >= 0) & (grid < ends)
    values = np.where(covered, prices["price_eur_mwh"].to_numpy()[safe], np.nan)
    return pd.Series(values, index=grid, name="price_eur_mwh")


def capture_table(
    prices: pd.DataFrame,
    power: pd.DataFrame,
    tz: str,
    freq: str = "M",
    technologies: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Capture prices per local calendar period and technology.

    Index: (period, technology). Columns:
      base_price_eur_mwh     time-weighted mean price of the period
      capture_price_eur_mwh  volume-weighted price of the technology
      capture_rate           capture price / base price
      energy_twh             energy produced in the period
      negative_price_share   share of that energy produced at a negative price
    """
    technologies = technologies or TECHNOLOGIES
    price = prices_on_grid(prices, power.index)
    hours = interval_minutes(power.index) / 60.0
    local = power.index.tz_convert(tz).tz_localize(None)
    period = pd.PeriodIndex(local, freq=freq, name="period")

    priced = price.notna()
    base = (price * hours)[priced].groupby(period[priced]).sum() / hours[priced].groupby(
        period[priced]
    ).sum()

    frames = []
    for tech, column in technologies.items():
        energy_mwh = (power[column] * hours).where(priced)
        total = energy_mwh.groupby(period).sum()
        revenue = (price * energy_mwh).groupby(period).sum()
        negative = energy_mwh.where(price < 0, 0.0).groupby(period).sum()
        capture = (revenue / total).where(total > 0)
        frames.append(
            pd.DataFrame(
                {
                    "technology": tech,
                    "base_price_eur_mwh": base,
                    "capture_price_eur_mwh": capture,
                    "capture_rate": capture / base,
                    "energy_twh": total / 1e6,
                    "negative_price_share": (negative / total).where(total > 0),
                }
            )
        )
    table = pd.concat(frames).set_index("technology", append=True).sort_index()
    return table


def reconciliation_metrics(annual: pd.DataFrame) -> pd.DataFrame:
    """Annual capture metrics in the units of the official publications.

    Returns one row per year (int) with columns such as
    capture_price_solar_ct_kwh (1 ct/kWh = 10 EUR/MWh) and
    nonnegative_share_solar_pct (share of energy sold at a price >= 0, in %),
    ready for ppa_lab.analysis.reconcile.reconcile().
    """
    rows: dict[int, dict[str, float]] = {}
    for (period, tech), row in annual.iterrows():
        metrics = rows.setdefault(int(period.year), {})
        metrics[f"capture_price_{tech}_ct_kwh"] = row["capture_price_eur_mwh"] / 10.0
        metrics[f"nonnegative_share_{tech}_pct"] = 100.0 * (1.0 - row["negative_price_share"])
    out = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    out.index.name = "year"
    return out


def load_market_values(path: Path) -> pd.DataFrame:
    """Official monthly market values (ct/kWh), indexed by calendar month."""
    frame = pd.read_csv(path, comment="#")
    frame.index = pd.PeriodIndex(frame.pop("month"), freq="M", name="month")
    return frame


def compare_monthly(monthly: pd.DataFrame, official: pd.DataFrame) -> pd.DataFrame:
    """Our monthly base and capture prices against the official market values.

    Returns long format: month, series ("spot" or a technology), ours_ct_kwh,
    official_ct_kwh, difference_ct_kwh (ours - official). Months without an
    official value (not published yet) are left out.
    """
    rows = []
    for (period, tech), row in monthly.iterrows():
        if period not in official.index:
            continue
        ref = official.loc[period]
        pairs = [("spot", row["base_price_eur_mwh"]), (tech, row["capture_price_eur_mwh"])]
        for name, ours_eur_mwh in pairs:
            column = f"{name}_ct_kwh"
            if column not in ref.index:
                continue
            ours = ours_eur_mwh / 10.0
            rows.append(
                {
                    "month": period,
                    "series": name,
                    "ours_ct_kwh": ours,
                    "official_ct_kwh": float(ref[column]),
                    "difference_ct_kwh": ours - float(ref[column]),
                }
            )
    columns = ["month", "series", "ours_ct_kwh", "official_ct_kwh", "difference_ct_kwh"]
    out = pd.DataFrame(rows, columns=columns)
    # The spot comparison appears once per technology; keep one copy.
    return out.drop_duplicates(subset=["month", "series"]).reset_index(drop=True)
