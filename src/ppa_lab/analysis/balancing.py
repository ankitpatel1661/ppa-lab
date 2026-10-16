"""What the TSOs' own data say (roadmap item 6): the official market values (PPA-2b) and what
balancing a wind or solar portfolio costs.

Market values. The TSOs compute the official monthly market value of a technology from their
online extrapolation of its output ("Online-Hochrechnung"), not from the measured feed-in.
Capture prices recomputed with that extrapolation and our day-ahead prices test whether this
explains the gap of Step 2 (backlog PPA-2b).

Balancing. A direct marketer sells its day-ahead forecast at the day-ahead price and settles
the difference to the actual output at the imbalance price reBAP (long: "reBAP ueberdeckt",
short: "reBAP unterdeckt"). Per MWh produced the imbalance costs

    c = sum_t (a_t - f_t) (P_t - reBAP_t) / sum_t a_t

with a the actual output (Energy-Charts, quarter-hours), f the day-ahead forecast (ENTSO-E,
the same basis) and P the day-ahead price. Each month's forecast is scaled to that month's
actual energy first: a forecaster corrects a systematic bias, so only timing and shape errors
count. The national portfolio smooths errors a single park has, but intraday trading lets a
marketer correct some of them before delivery: the two effects pull in opposite directions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_lab.data.store import RawStore

TECHNOLOGIES = {  # name: (Energy-Charts column, online extrapolation dataset, official column)
    "wind_onshore": ("wind_onshore_mw", "wind_onshore_online", "wind_onshore_ct_kwh"),
    "wind_offshore": ("wind_offshore_mw", "wind_offshore_online", "wind_offshore_ct_kwh"),
    "solar": ("solar_mw", "solar_online", "solar_ct_kwh"),
}


def load_tso_data(raw_dir) -> dict | None:
    """reBAP and the online extrapolations (netztransparenz.de) and the day-ahead forecasts
    (ENTSO-E) from the raw cache; None if any is missing (`ppa-lab tso`, `ppa-lab forecasts`)."""
    nt, en = RawStore(raw_dir, source="netztransparenz"), RawStore(raw_dir, source="entsoe")
    needed = [nt.months(ds) for _, ds, _ in TECHNOLOGIES.values()] + [nt.months("rebap"),
                                                                       en.months("wind_solar_forecast")]
    if not all(needed):
        return None
    return {"rebap": nt.load("rebap"), "forecast": en.load("wind_solar_forecast"),
            "online": {tech: nt.load(ds).sum(axis=1, min_count=1)
                       for tech, (_, ds, _) in TECHNOLOGIES.items()}}


def hourly_mean(series: pd.Series) -> pd.Series:
    """Hourly mean (UTC hours) of a series at any resolution (the online extrapolation moved
    from hours to quarter-hours in 2025)."""
    return series.resample("1h").mean().dropna()


def energy_mwh(series: pd.Series, tz: str) -> pd.Series:
    """Energy per local year (MWh) of an MW series, whatever its resolution."""
    hourly = hourly_mean(series)
    return hourly.groupby(hourly.index.tz_convert(tz).year).sum()


def capture_prices(prices: pd.Series, generation: pd.Series, tz: str, freq: str) -> pd.Series:
    """Volume-weighted price per local month ("M") or year ("Y") of hourly prices (UTC) and
    hourly generation."""
    q = generation.reindex(prices.index)
    ok = q.notna().to_numpy()
    p, q = prices[ok], q[ok]
    local = p.index.tz_convert(tz).tz_localize(None)
    key = pd.PeriodIndex(local, freq="M") if freq == "M" else local.year
    return (p * q).groupby(key).sum() / q.groupby(key).sum()


def market_value_check(prices: pd.Series, measured: pd.DataFrame, online: dict[str, pd.Series],
                       official: dict[str, pd.Series], tz: str) -> pd.DataFrame:
    """Per technology and month: the official market value, and the capture prices with the
    measured feed-in and with the TSOs' online extrapolation (EUR/MWh)."""
    rows = []
    for tech, (column, _, _) in TECHNOLOGIES.items():
        table = pd.DataFrame({
            "official": official[tech],
            "measured": capture_prices(prices, measured[column], tz, "M"),
            "online": capture_prices(prices, hourly_mean(online[tech]), tz, "M"),
        }).dropna()
        rows.append(table.assign(technology=tech))
    return pd.concat(rows).rename_axis("month")


def bias_free(actual: pd.Series, forecast: pd.Series, tz: str) -> pd.Series:
    """The forecast scaled per local month to that month's actual energy."""
    month = pd.PeriodIndex(actual.index.tz_convert(tz).tz_localize(None), freq="M")
    factor = actual.groupby(month).transform("sum") / forecast.groupby(month).transform("sum")
    return forecast * factor.to_numpy()


def imbalance_frame(actual: pd.Series, forecast: pd.Series, price: pd.Series,
                    rebap_short: pd.Series, rebap_long: pd.Series, tz: str,
                    correct_bias: bool = True) -> pd.DataFrame:
    """Quarter-hours with all inputs: actual a, forecast f (bias-free unless told otherwise),
    error a - f, the imbalance price that applies (long or short) and the cost (EUR)."""
    grid = actual.index
    frame = pd.DataFrame({"a": actual, "f": forecast.reindex(grid), "p": price.reindex(grid),
                          "short": rebap_short.reindex(grid),
                          "long": rebap_long.reindex(grid)}).dropna()
    if correct_bias:
        frame["f"] = bias_free(frame["a"], frame["f"], tz)
    step_h = (frame.index[1] - frame.index[0]) / pd.Timedelta(hours=1) if len(frame) > 1 else 0.25
    frame["error"] = frame["a"] - frame["f"]
    frame["rebap"] = np.where(frame["error"] > 0, frame["long"], frame["short"])
    frame["cost_eur"] = frame["error"] * step_h * (frame["p"] - frame["rebap"])
    frame["energy_mwh"] = frame["a"] * step_h
    return frame


def imbalance_cost(frame: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Per local year: imbalance cost per MWh produced, relative forecast error (mean absolute
    error over mean output) and the mean distance of reBAP from the day-ahead price."""
    year = frame.index.tz_convert(tz).year
    grouped = frame.groupby(year)
    return pd.DataFrame({
        "cost_eur_mwh": grouped["cost_eur"].sum() / grouped["energy_mwh"].sum(),
        "relative_error": frame["error"].abs().groupby(year).mean() / grouped["a"].mean(),
        "spread_eur_mwh": (frame["rebap"] - frame["p"]).abs().groupby(year).mean(),
        "energy_twh": grouped["energy_mwh"].sum() / 1e6,
    }).rename_axis("year")


def window_cost(frame: pd.DataFrame, start: str, end: str, tz: str) -> float:
    """Imbalance cost per MWh produced over local days [start, end]."""
    day = frame.index.tz_convert(tz).tz_localize(None).normalize()
    part = frame[(day >= pd.Timestamp(start)) & (day <= pd.Timestamp(end))]
    return float(part["cost_eur"].sum() / part["energy_mwh"].sum())


def quarter_hour_prices(prices_native: pd.Series, grid: pd.DatetimeIndex) -> pd.Series:
    """Day-ahead prices on a quarter-hour grid: hourly prices (until September 2025) hold
    for their four quarter-hours."""
    union = prices_native.index.union(grid)
    return prices_native.reindex(union).sort_index().ffill().reindex(grid)
