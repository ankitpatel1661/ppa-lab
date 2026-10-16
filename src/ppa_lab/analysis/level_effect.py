"""Does a technology's capture rate move with the price level? (PPA-8d)

The price model (Step 5) shifts all hours together in arcsinh units, so when the level rises,
hours near zero are lifted and solar's capture rate rises with it. The usual shape-factor
view scales every hour with the level instead, so the capture rate would not move. History
decides, on a monthly panel with the build-out held fixed:

    capture_rate_m = a_month + b ln(base_m) + c share_m + e_m

with month-of-year effects a_month (season), the technology's share of load (build-out) and
heteroscedasticity-robust (HC1) standard errors. b > 0: the capture rate rises with the
level; b = 0: the shape-factor view.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

Z_95 = 1.959964


def monthly_panel(prices: pd.Series, power: pd.DataFrame, tz: str,
                  columns: dict[str, str]) -> pd.DataFrame:
    """Per local month: time-weighted base price, and per technology the capture rate and
    the share of load. `prices` and `power` are hourly (UTC); `columns` maps a technology
    name to its generation column, e.g. {"solar": "solar_mw"}. Months with any missing hour
    of price, load or generation are dropped."""
    index = prices.index
    frame = pd.DataFrame({"price": prices.to_numpy()}, index=index)
    frame["load"] = power["load_mw"].reindex(index).to_numpy()
    for tech, column in columns.items():
        frame[tech] = power[column].reindex(index).to_numpy()
    frame = frame.dropna()
    month = frame.index.tz_convert(tz).tz_localize(None).to_period("M")
    groups = frame.groupby(month)
    panel = pd.DataFrame({"base": groups["price"].mean()})
    for tech in columns:
        weighted = (frame["price"] * frame[tech]).groupby(month).sum()
        panel[f"capture_rate_{tech}"] = weighted / groups[tech].sum() / panel["base"]
        panel[f"share_{tech}"] = groups[tech].sum() / groups["load"].sum()
    return panel.rename_axis("month")


def level_regression(panel: pd.DataFrame, tech: str, start_year: int | None = None,
                     log: bool = False) -> dict | None:
    """OLS of the capture rate (its logarithm with `log`) on ln(base price) and the share of
    load, with month effects.

    Returns coef, se, t, ci_low, ci_high (95%) of ln(base), share_coef and share_se, r2, n;
    None when the data cannot separate the effects (too few months, or a share or level that
    never moves).
    """
    data = panel if start_year is None else panel[panel.index.year >= start_year]
    months = pd.get_dummies(data.index.month, prefix="m").astype(float).to_numpy()
    x = np.column_stack([months, np.log(data["base"].to_numpy()),
                         data[f"share_{tech}"].to_numpy()])
    y = data[f"capture_rate_{tech}"].to_numpy()
    if log:
        y = np.log(y)
    if len(y) <= x.shape[1] or np.linalg.matrix_rank(x) < x.shape[1]:
        return None
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    resid = y - x @ beta
    n, k = x.shape
    xtx_inv = np.linalg.inv(x.T @ x)
    meat = (x * resid[:, None]).T @ (x * resid[:, None])
    cov = xtx_inv @ meat @ xtx_inv * n / (n - k)                  # HC1
    i = months.shape[1]                                           # ln(base) column
    coef, se = float(beta[i]), float(np.sqrt(cov[i, i]))
    return {"coef": coef, "se": se, "t": coef / se,
            "ci_low": coef - Z_95 * se, "ci_high": coef + Z_95 * se,
            "share_coef": float(beta[i + 1]), "share_se": float(np.sqrt(cov[i + 1, i + 1])),
            "r2": float(1 - resid @ resid / ((y - y.mean()) @ (y - y.mean()))), "n": int(n)}


def share_pace(power: pd.DataFrame, tz: str, column: str, first_year: int) -> dict | None:
    """How fast a technology's share of load grew: per year from the end of `first_year` - 1
    to the last complete local calendar year. None without two complete years."""
    frame = power[[column, "load_mw"]].dropna()
    year = frame.index.tz_convert(tz).year
    sums = frame.groupby(year).sum()
    share = (sums[column] / sums["load_mw"])[frame.groupby(year).size() >= 8700]
    base = first_year - 1
    if base not in share.index or share.index.max() <= base:
        return None
    last = int(share.index.max())
    return {"from": base, "to": last,
            "per_year": float((share[last] - share[base]) / (last - base))}

