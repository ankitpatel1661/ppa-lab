"""Day 2 report: capture prices and capture rates, tied out to the official market values.

Output:
    reports/day02_capture_prices.md
    reports/figures/day02_*.png
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.capture import (
    TECHNOLOGIES,
    capture_table,
    compare_monthly,
    load_market_values,
    reconciliation_metrics,
)
from ppa_lab.analysis.plotting import BLUE, BLUE_RAMP, GREEN, GRID, INK, INK_2, ORANGE, save, style
from ppa_lab.analysis.reconcile import reconcile
from ppa_lab.config import Settings

log = logging.getLogger(__name__)

MARKET_VALUES_FILE = "netztransparenz_market_values_monthly.csv"
# Colour follows the technology in every chart (never its rank).
COLOURS = {"wind_onshore": BLUE, "solar": ORANGE, "wind_offshore": GREEN}
LABELS = {"solar": "Solar", "wind_onshore": "Wind onshore", "wind_offshore": "Wind offshore"}
SERIES_LABELS = {"spot": "Spot (base)", **LABELS}
# Tolerance used for the monthly comparison, same as for the annual references.
MONTHLY_TOLERANCE_CT = 0.10


def complete_months(start: date, end: date) -> list[pd.Period]:
    """Calendar months that lie entirely inside the inclusive range start..end."""
    first = pd.Period(start, freq="M")
    if start.day != 1:
        first += 1
    last = pd.Period(end, freq="M")
    if end != last.end_time.date():
        last -= 1
    return list(pd.period_range(first, last, freq="M")) if first <= last else []


def complete_years(start: date, end: date) -> list[int]:
    """Calendar years that lie entirely inside the inclusive range start..end."""
    first = start.year if (start.month, start.day) == (1, 1) else start.year + 1
    last = end.year if (end.month, end.day) == (12, 31) else end.year - 1
    return list(range(first, last + 1))


def negative_hours_by_month(prices: pd.DataFrame, tz: str) -> pd.Series:
    """Duration of negative prices per local month, in hours (any resolution)."""
    hours = prices["interval_min"] / 60.0
    month = pd.PeriodIndex(prices.index.tz_convert(tz).tz_localize(None), freq="M")
    return hours.where(prices["price_eur_mwh"] < 0, 0.0).groupby(month).sum()


def solar_share_of_load(power: pd.DataFrame, tz: str) -> pd.Series:
    """Solar generation as a share of load per local month (both energies, in %)."""
    month = pd.PeriodIndex(power.index.tz_convert(tz).tz_localize(None), freq="M")
    sums = power[["solar_mw", "load_mw"]].groupby(month).sum()
    return 100.0 * sums["solar_mw"] / sums["load_mw"]


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_capture_rate_monthly(monthly: pd.DataFrame, path: Path) -> Path:
    rate = monthly["capture_rate"].unstack("technology")
    x = rate.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(9, 3.9))
    ax.hlines(1.0, x[0], x[-1], color=INK_2, linewidth=0.9, linestyle="--")
    ax.text(x[-1] + pd.Timedelta(days=12), 1.01, "Baseload = 1.0", color=INK_2, fontsize=8,
            va="bottom")
    for tech in ("wind_offshore", "wind_onshore", "solar"):
        if tech in rate:
            ax.plot(x, rate[tech].to_numpy(), color=COLOURS[tech], linewidth=2, label=LABELS[tech])
    # Direct labels at the line ends (text in ink, the line carries the colour).
    ends = sorted((float(rate[t].iloc[-1]), LABELS[t]) for t in rate.columns)
    placed: list[float] = []
    for value, label in ends:
        y = max(value, placed[-1] + 0.06) if placed else value
        placed.append(y)
        ax.text(x[-1] + pd.Timedelta(days=12), y, label, color=INK, fontsize=8.5, va="center")
    ax.set_xlim(x[0], x[-1] + pd.Timedelta(days=150))
    ax.set_ylim(0, max(1.15, float(np.nanmax(rate.to_numpy())) + 0.05))
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", ncols=3)
    style(ax, "Capture rate by month: what share of the baseload price each technology earns",
          "capture price / base price")
    return save(fig, path)


def fig_official_gap(
    comparison: pd.DataFrame, negative_hours: pd.Series, path: Path
) -> Path | None:
    if comparison.empty:
        return None
    diff = comparison.pivot(index="month", columns="series", values="difference_ct_kwh")
    x = diff.index.to_timestamp()
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(9, 5.4), sharex=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    top.axhspan(-MONTHLY_TOLERANCE_CT, MONTHLY_TOLERANCE_CT, color=GRID, alpha=0.6, linewidth=0)
    top.axhline(0, color=INK_2, linewidth=0.8)
    for tech in ("wind_offshore", "wind_onshore", "solar"):
        if tech in diff:
            top.plot(x, diff[tech].to_numpy(), color=COLOURS[tech], linewidth=2,
                     marker="o", markersize=3, label=LABELS[tech])
    top.text(x[0], -MONTHLY_TOLERANCE_CT, "grey band: ±0.10 ct/kWh tolerance", color=INK_2,
             fontsize=8, va="top")
    top.legend(frameon=False, fontsize=8.5, loc="upper left", ncols=3)
    style(top, "Our capture price minus the official market value, by month", "ct/kWh")

    neg = negative_hours.reindex(diff.index).fillna(0.0)
    bottom.bar(x, neg.to_numpy(), width=20, color=INK_2)
    style(bottom, "Hours with negative day-ahead prices in the month", "hours")
    return save(fig, path)


def fig_solar_cannibalisation(monthly: pd.DataFrame, share: pd.Series, path: Path) -> Path | None:
    if monthly.empty:
        return None
    solar = monthly.xs("solar", level="technology")["capture_rate"]
    data = pd.DataFrame({"share": share, "rate": solar}).dropna()
    if len(data) < 6:  # too few months for a meaningful picture
        return None
    years = sorted({p.year for p in data.index})
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for year, colour in zip(years, BLUE_RAMP[-len(years):], strict=False):
        pts = data[[p.year == year for p in data.index]]
        ax.scatter(pts["share"], pts["rate"], s=40, color=colour, edgecolor="white",
                   linewidth=1, label=str(year), zorder=3)
    slope, intercept = np.polyfit(data["share"], data["rate"], 1)
    xs = np.linspace(data["share"].min(), data["share"].max(), 50)
    ax.plot(xs, intercept + slope * xs, color=INK_2, linewidth=1.2, linestyle="--",
            label=f"linear fit: {10 * slope:+.2f} per +10 points of share")
    lowest = data["rate"].idxmin()
    ax.annotate(f"{lowest.strftime('%b %Y')}: {data.loc[lowest, 'rate']:.2f}",
                (data.loc[lowest, "share"], data.loc[lowest, "rate"]),
                textcoords="offset points", xytext=(-8, -2), ha="right", fontsize=8.5, color=INK)
    ax.set_xlabel("Solar generation as % of load in the month", color=INK_2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    style(ax, "Solar cannibalisation: the more solar, the less each MWh earns",
          "solar capture rate")
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Tables and text
# --------------------------------------------------------------------------- #
def _annual_table(annual: pd.DataFrame, full_years: list[int], end: date) -> str:
    view = annual.reset_index()
    view["order"] = view["technology"].map({t: i for i, t in enumerate(TECHNOLOGIES)})
    view = view.sort_values(["period", "order"]).reset_index(drop=True)
    view["Year"] = [
        str(p.year) if p.year in full_years else f"{p.year} (to {end:%d %b})"
        if p.year == end.year else f"{p.year} (partial)"
        for p in view["period"]
    ]
    view["Technology"] = view["technology"].map(LABELS)
    out = pd.DataFrame(
        {
            "Year": view["Year"],
            "Technology": view["Technology"],
            "Base price (EUR/MWh)": view["base_price_eur_mwh"].map("{:.2f}".format),
            "Capture price (EUR/MWh)": view["capture_price_eur_mwh"].map("{:.2f}".format),
            "Capture rate": view["capture_rate"].map("{:.3f}".format),
            "Energy (TWh)": view["energy_twh"].map("{:.1f}".format),
            "Energy at negative prices": view["negative_price_share"].map("{:.1%}".format),
        }
    )
    return out.to_markdown(index=False)


def _monthly_summary(comparison: pd.DataFrame) -> str:
    rows = []
    for series, grp in comparison.groupby("series", sort=False):
        worst = grp.loc[grp["difference_ct_kwh"].abs().idxmax()]
        rows.append(
            {
                "Series": SERIES_LABELS.get(series, series),
                "Months": len(grp),
                "Mean difference (ct/kWh)": f"{grp['difference_ct_kwh'].mean():+.3f}",
                "Mean absolute difference": f"{grp['difference_ct_kwh'].abs().mean():.3f}",
                "Months within ±0.10": int(
                    (grp["difference_ct_kwh"].abs() <= MONTHLY_TOLERANCE_CT + 1e-9).sum()
                ),
                "Largest difference": f"{worst['difference_ct_kwh']:+.3f} "
                f"({worst['month'].strftime('%b %Y')})",
            }
        )
    return pd.DataFrame(rows).to_markdown(index=False)


def _open_differences(recon: pd.DataFrame) -> str:
    n_open = int((recon["status"] == "OUTSIDE tolerance").sum())
    if not n_open:
        return "Every reference is within tolerance or has a documented cause."
    return (
        f"**{n_open} differences are outside tolerance without a proven cause.** They are "
        "open investigations (see `docs/BACKLOG.md`), not accepted errors."
    )


def monthly_comparison_text(comparison: pd.DataFrame) -> str:
    """Report section 3: how many months were compared and the summary per series."""
    if comparison.empty:
        return "No complete month in the data range has an official value to compare with."
    months = comparison["month"]
    return (
        f"{months.nunique()} complete months compared "
        # pandas Periods do not accept f-string date formats; use strftime.
        f"({months.min().strftime('%b %Y')} to {months.max().strftime('%b %Y')}).\n\n"
        + _monthly_summary(comparison)
    )


def _findings(annual: pd.DataFrame, full_years: list[int]) -> str:
    if not full_years:
        return "No complete calendar year in the data range."
    first, last = full_years[0], full_years[-1]
    lines = []
    for tech in ("solar", "wind_onshore", "wind_offshore"):
        a = annual.loc[(pd.Period(str(first), "Y"), tech)]
        b = annual.loc[(pd.Period(str(last), "Y"), tech)]
        lines.append(
            f"- **{LABELS[tech]}:** capture rate {a['capture_rate']:.2f} in {first} and "
            f"{b['capture_rate']:.2f} in {last}; in {last} it earned "
            f"{b['base_price_eur_mwh'] - b['capture_price_eur_mwh']:.2f} EUR/MWh less than "
            f"baseload, and {b['negative_price_share']:.1%} of its energy was produced at "
            "negative prices."
        )
    return "\n".join(lines)


def write_day02_report(settings: Settings) -> dict[str, Path | None]:
    tz = settings.timezone
    proc = settings.processed_dir
    prices = pd.read_parquet(proc / "prices_native.parquet")
    power = pd.read_parquet(proc / "power_15min.parquet")

    monthly = capture_table(prices, power, tz, freq="M")
    annual = capture_table(prices, power, tz, freq="Y")
    full_years = complete_years(settings.start, settings.end)
    full_months = complete_months(settings.start, settings.end)

    in_full_years = [p.year in full_years for p in annual.index.get_level_values("period")]
    metrics = reconciliation_metrics(annual[in_full_years])
    references = tuple(
        r for r in settings.references
        if r.metric.startswith(("capture_price_", "nonnegative_share_"))
    )
    recon = reconcile(metrics, references)

    official_path = settings.reference_dir / MARKET_VALUES_FILE
    official = load_market_values(official_path)
    in_full_months = monthly.index.get_level_values("period").isin(full_months)
    comparison = compare_monthly(monthly[in_full_months], official)

    fig_dir = settings.reports_dir / "figures"
    share = solar_share_of_load(power, tz)
    figs = {
        "capture_rate": fig_capture_rate_monthly(
            monthly, fig_dir / "day02_capture_rate_monthly.png"
        ),
        "official_gap": fig_official_gap(
            comparison, negative_hours_by_month(prices, tz), fig_dir / "day02_official_gap.png"
        ),
        "cannibalisation": fig_solar_cannibalisation(
            monthly[in_full_months], share, fig_dir / "day02_solar_cannibalisation.png"
        ),
    }
    captions = {
        "capture_rate": "Capture rate by month",
        "official_gap": "Difference to the official market values",
        "cannibalisation": "Solar cannibalisation",
    }
    charts = "\n\n".join(
        f"![{captions[key]}](figures/{path.name})" for key, path in figs.items() if path
    )

    recon_view = recon.copy()
    recon_view["ours"] = recon_view["ours"].map(lambda v: f"{v:.3f}")
    recon_view["difference"] = recon_view["difference"].map(lambda v: f"{v:+.3f}")

    report = f"""# Day 2 report: capture prices of German solar and wind

Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab capture`.
Data: {settings.energy_charts.license}. Bidding zone {settings.bidding_zone},
delivery days {settings.start} to {settings.end} (local time, {tz}).
Official market values: netztransparenz.de (file `{official_path.name}`).

Capture price = sum(price x energy) / sum(energy) over the quarter-hours of the period;
capture rate = capture price / time-weighted base price. Technologies:
{", ".join(LABELS[t] for t in TECHNOLOGIES)}.

## 1. Capture prices and capture rates by year

{_annual_table(annual, full_years, settings.end)}

## 2. Reconciliation with the official annual market values

{recon_view[["metric", "year", "ours", "published", "difference", "tolerance", "status"]]
 .to_markdown(index=False)}

{_open_differences(recon)}

Sources: {"; ".join(f"{r.year} {r.metric}: {r.source}" for r in references)}.

## 3. Monthly comparison with the official market values

{monthly_comparison_text(comparison)}

## 4. What the numbers say

{_findings(annual, full_years)}

## 5. Charts

{charts}
"""
    report_path = settings.reports_dir / "day02_capture_prices.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    log.info("wrote %s", report_path)
    return {"report": report_path, **figs}
