"""Solar and storage build-out after the delivery year (backlog PPA-8f, roadmap item 7).

The delivery-year scenarios carry solar's build-out up to that year (the intraday trend of
Step 5). For later contract years the capture rate follows explicit build-out scenarios:

1. Solar's share of load grows with the solar capacity added, kappa share points per GW
   (calibrated on history: the share's growth over the years the additions came in).
2. Batteries take midday solar out of the cheap hours: a GWh of storage cycling n times a year,
   a fraction f of it from solar, removes lambda = n f / load of the share. History's storage
   growth is already inside kappa, so only storage beyond history's pace counts.
3. The capture rate falls by the same proportion per share point as on monthly history,
   log CR = month effects + b ln(price) + gamma share (PPA-8d data, log form), amplified by the
   share's seasonality: new solar adds most share in the sunny months, which weigh most.

So per year after the delivery year, the effective share grows by
    ds = kappa x PV additions - lambda x (storage additions - history's storage additions)
and the capture rate is multiplied by exp(gamma x amplification x cumulative ds).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Calibration:
    kappa: float           # share of load per GW of solar added
    lam: float             # share of load absorbed per GWh of storage
    amplification: float   # production-weighted monthly share over the annual share
    gamma: float           # change of ln(capture rate) per unit of monthly share
    gamma_se: float
    load_twh: float
    share_start: float     # solar share of load in the first and last history year
    share_end: float


def annual_share(power: pd.DataFrame, tz: str, column: str = "solar_mw") -> pd.Series:
    """Solar share of load per local year (hourly MW, UTC index)."""
    year = power.index.tz_convert(tz).year
    sums = power.groupby(year)[[column, "load_mw"]].sum()
    return sums[column] / sums["load_mw"]


def seasonal_amplification(power: pd.DataFrame, tz: str, year: int,
                           column: str = "solar_mw") -> float:
    """Sum over months of (the month's share of solar output) x (the month's share of load
    over the year's): how much more a share rise counts where solar produces."""
    local = power.index.tz_convert(tz)
    part = power[local.year == year]
    month = part.groupby(part.index.tz_convert(tz).month)[[column, "load_mw"]].sum()
    year_share = month[column].sum() / month["load_mw"].sum()
    weight = month[column] / month[column].sum()
    return float((weight * (month[column] / month["load_mw"]) / year_share).sum())


def calibrate(power: pd.DataFrame, tz: str, first_year: int, last_year: int,
              additions_gw: list[float], cycles: float, solar_fraction: float,
              gamma: float, gamma_se: float) -> Calibration:
    """kappa from the share's growth from `first_year` to `last_year` over the solar
    capacity added in the years between (`additions_gw`, one per year after `first_year`);
    lambda from the storage assumptions and `last_year`'s load."""
    if len(additions_gw) != last_year - first_year:
        raise ValueError(f"need one addition per year {first_year + 1}-{last_year}")
    share = annual_share(power, tz)
    year = power.index.tz_convert(tz).year
    load_twh = float(power.loc[year == last_year, "load_mw"].sum() / 1e6)
    return Calibration(
        kappa=float((share[last_year] - share[first_year]) / sum(additions_gw)),
        lam=cycles * solar_fraction / (load_twh * 1000.0),
        amplification=seasonal_amplification(power, tz, last_year),
        gamma=gamma, gamma_se=gamma_se, load_twh=load_twh,
        share_start=float(share[first_year]), share_end=float(share[last_year]))


def share_growth(cal: Calibration, pv_gw: float, storage_gwh: float,
                 history_storage_gwh: float) -> float:
    """Growth of the effective solar share per year (share units)."""
    return cal.kappa * pv_gw - cal.lam * (storage_gwh - history_storage_gwh)


def capture_rate_factors(cal: Calibration, growth: float, start: int,
                         years: int) -> dict[int, float]:
    """Factor on the capture rate per contract year: 1 in the delivery year `start`, then
    exp(gamma x amplification x growth x years since `start`)."""
    return {start + i: float(np.exp(cal.gamma * cal.amplification * growth * i))
            for i in range(years)}
