"""Day 1 report: data quality, annual statistics, reconciliation and four charts.

Output:
    reports/day01_market_data.md
    reports/data_quality.md
    reports/figures/day01_*.png
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files, no window needed (also works on CI servers)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ppa_lab.analysis.reconcile import (  # noqa: E402
    annual_price_stats,
    hourly_profile,
    monthly_mean_price,
    reconcile,
)
from ppa_lab.config import Settings  # noqa: E402
from ppa_lab.data.quality import QualityReport, run_all  # noqa: E402

log = logging.getLogger(__name__)

# Validated categorical palette (slots 1-3) and neutral inks.
BLUE, ORANGE, GREEN = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#e2e2de"


def _style(ax: plt.Axes, title: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=INK)
    ax.set_ylabel(ylabel, color=INK_2, fontsize=9)
    ax.tick_params(colors=INK_2, labelsize=8.5, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def _save(fig: plt.Figure, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def fig_monthly_price(monthly: pd.Series, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 3.6))
    x = monthly.index.to_timestamp()
    ax.plot(x, monthly.to_numpy(), color=BLUE, linewidth=2)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    # Points in the last six months get a left-hand label so they stay inside the plot.
    late = monthly.index[max(0, len(monthly) - 6)]
    for idx in (monthly.idxmax(), monthly.idxmin()):
        right_edge = idx >= late
        ax.annotate(
            f"{idx.strftime('%b %Y')}: {monthly[idx]:.0f}",
            (idx.to_timestamp(), monthly[idx]),
            textcoords="offset points", xytext=(-8, 4) if right_edge else (6, 6),
            ha="right" if right_edge else "left", fontsize=8.5, color=INK,
        )
        ax.plot(idx.to_timestamp(), monthly[idx], "o", color=BLUE, markersize=5)
    _style(ax, "German day-ahead price, monthly time-weighted mean (DE-LU)", "EUR/MWh")
    return _save(fig, path)


def fig_negative_hours(stats: pd.DataFrame, recon: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 3.6))
    years = stats.index.to_list()
    labels = [
        f"{y}\n(to {stats.loc[y, 'last_day']:%d %b})" if stats.loc[y, "hours"] < 8700 else str(y)
        for y in years
    ]
    bars = ax.bar(range(len(years)), stats["negative_hours"], color=BLUE, width=0.6,
                  label="This pipeline (hourly average < 0)")
    ax.bar_label(bars, fmt="%d", fontsize=9, color="white", padding=-16, fontweight="bold")
    pub = recon[recon["metric"] == "negative_hours"].set_index("year")["published"]
    xs = [years.index(y) for y in pub.index if y in years]
    ax.plot(xs, [pub[y] for y in pub.index if y in years], "D", color=ORANGE, markersize=7,
            label="Published (DGS evaluation)", linestyle="none")
    ax.set_xticks(range(len(years)), labels)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    _style(ax, "Hours with negative day-ahead prices, Germany", "hours")
    return _save(fig, path)


def fig_resolution_switch(prices: pd.DataFrame, tz: str, path: Path) -> Path | None:
    local = prices.tz_convert(tz)
    window = local.loc["2025-09-30":"2025-10-01", "price_eur_mwh"]
    if window.empty:  # configured range does not include the switch
        return None
    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.step(window.index, window.to_numpy(), where="post", color=BLUE, linewidth=1.6)
    switch = pd.Timestamp("2025-10-01 00:00", tz=tz)
    ax.axvline(switch, color=ORANGE, linestyle="--", linewidth=1.2)
    ax.text(switch, ax.get_ylim()[1], "  1 Oct 2025: 15-minute products go live",
            color=INK, fontsize=8.5, va="top")
    ax.set_xlim(window.index.min(), window.index.max())
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b %H:%M", tz=tz))
    _style(ax, "Day-ahead price: hourly on 30 Sep 2025, quarter-hourly from 1 Oct 2025",
           "EUR/MWh")
    return _save(fig, path)


def fig_hourly_profile(profile: pd.DataFrame, path: Path) -> Path | None:
    if profile.empty:  # no complete calendar year in range
        return None
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for year, colour in zip(profile.columns, (BLUE, ORANGE, GREEN), strict=False):
        ax.plot(profile.index, profile[year], color=colour, linewidth=2, label=str(year))
    # End-of-line labels, nudged apart so they never overlap.
    ends = sorted((float(profile[y].iloc[-1]), str(y)) for y in profile.columns)
    span = float(profile.max().max() - profile.min().min()) or 1.0
    placed: list[float] = []
    for value, label in ends:
        y = max(value, placed[-1] + 0.06 * span) if placed else value
        placed.append(y)
        ax.text(23.3, y, label, color=INK, fontsize=8.5, va="center")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlim(0, 24.5)
    ax.set_xlabel("Hour of day (local time, interval start)", color=INK_2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", ncols=3)
    _style(ax, "Average day-ahead price by hour of day: the midday 'solar dip'", "EUR/MWh")
    return _save(fig, path)


def _fmt_stats(stats: pd.DataFrame) -> str:
    cols = {
        "first_day": "First day",
        "last_day": "Last day",
        "mean_price_eur_mwh": "Mean price (EUR/MWh)",
        "min_price_eur_mwh": "Min",
        "max_price_eur_mwh": "Max",
        "negative_hours": "Negative hours",
        "hours_with_any_negative_interval": "Hours with any negative interval",
        "negative_time_hours": "Negative time (h)",
        "longest_negative_streak_h": "Longest negative streak (h)",
    }
    table = stats[list(cols)].rename(columns=cols).reset_index().rename(columns={"year": "Year"})
    return table.to_markdown(index=False, floatfmt=".2f")


def write_day01_report(settings: Settings) -> dict[str, Path | None]:
    proc = settings.processed_dir
    prices = pd.read_parquet(proc / "prices_native.parquet")
    prices_hourly = pd.read_parquet(proc / "prices_hourly.parquet")
    power = pd.read_parquet(proc / "power_15min.parquet")

    quality: QualityReport = run_all(prices, power, settings)
    stats = annual_price_stats(prices, settings.timezone)
    recon = reconcile(stats, settings.references)
    monthly = monthly_mean_price(prices, settings.timezone)
    full_years = [int(y) for y in stats.index if stats.loc[y, "hours"] >= 8700][-3:]
    profile = hourly_profile(prices_hourly, settings.timezone, full_years)

    fig_dir = settings.reports_dir / "figures"
    figs = {
        "monthly": fig_monthly_price(monthly, fig_dir / "day01_monthly_price.png"),
        "negative": fig_negative_hours(stats, recon, fig_dir / "day01_negative_hours.png"),
        "switch": fig_resolution_switch(prices, settings.timezone,
                                        fig_dir / "day01_resolution_switch.png"),
        "profile": fig_hourly_profile(profile, fig_dir / "day01_hourly_profile.png"),
    }

    dq_path = settings.reports_dir / "data_quality.md"
    counts = quality.counts()
    dq_path.write_text(
        "# Data-quality report\n\n"
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab check`. "
        f"Result: **{counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail**.\n\n"
        + quality.to_markdown() + "\n"
    )

    captions = {
        "monthly": "Monthly price",
        "negative": "Negative hours",
        "switch": "Resolution switch",
        "profile": "Hourly profile",
    }
    charts = "\n\n".join(
        f"![{captions[key]}](figures/{path.name})" for key, path in figs.items() if path
    )

    recon_view = recon.copy()
    recon_view["ours"] = recon_view["ours"].map(lambda v: f"{v:.2f}")
    recon_view["difference"] = recon_view["difference"].map(lambda v: f"{v:+.2f}")
    report = f"""# Day 1 report: German day-ahead market data

Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab report`.
Data: {settings.energy_charts.license}. Bidding zone {settings.bidding_zone},
delivery days {settings.start} to {settings.end} (local time, {settings.timezone}).

## 1. Data quality

**{counts['pass']} pass, {counts['warn']} warn, {counts['fail']} fail.**
Full details: [data_quality.md](data_quality.md).

## 2. Reconciliation with published figures

{recon_view[["metric", "year", "ours", "published", "difference", "tolerance", "status"]]
 .to_markdown(index=False)}

Sources: {"; ".join(f"{r.year} {r.metric}: {r.source}" for r in settings.references)}.

## 3. Annual statistics

{_fmt_stats(stats)}

## 4. Charts

{charts}
"""
    report_path = settings.reports_dir / "day01_market_data.md"
    report_path.write_text(report)
    log.info("wrote %s and %s", report_path, dq_path)
    return {"report": report_path, "quality": dq_path, **figs}
