"""Day 4 report: site generation from ERA5 weather, P50/P90 and checks against national data.

Output:
    reports/day04_generation.md
    reports/figures/day04_*.png
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from ppa_lab.analysis.capture import TECHNOLOGIES
from ppa_lab.analysis.generation import monthly_shares, site_vs_national, yield_trend
from ppa_lab.analysis.plotting import BLUE, INK, INK_2, ORANGE, save, style
from ppa_lab.config import Park, Settings
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import sited_parks, weather_dataset
from ppa_lab.timeutils import to_hourly
from ppa_lab.weather.yields import annual_energy, p_values

log = logging.getLogger(__name__)

COLOURS = {"solar": ORANGE, "wind_onshore": BLUE}
UNIT = {"solar": ("kWh/kWp", "specific yield"),
        "wind_onshore": ("full-load hours", "full-load hours")}


def _title(park: Park) -> str:
    return park.name.replace("_", " ").title()


def _overlap_years(settings: Settings, annual: pd.Series) -> list[int]:
    """Complete calendar years inside the market-data range that are also weather years."""
    return [y for y in range(settings.start.year, settings.end.year + 1)
            if date(y, 1, 1) >= settings.start and date(y, 12, 31) <= settings.end
            and y in annual.index]


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_annual(annuals: dict[str, pd.Series], parks: list[Park], path: Path) -> Path:
    fig, axes = plt.subplots(len(parks), 1, figsize=(9, 3.2 * len(parks)), squeeze=False)
    for ax, park in zip(axes[:, 0], parks, strict=True):
        per_mw = annuals[park.name] / park.capacity_mw  # MWh/MW = kWh/kW = full-load hours
        stats = p_values(per_mw)
        colour = COLOURS.get(park.technology, BLUE)
        ax.bar(per_mw.index, per_mw.to_numpy(), color=colour, width=0.7)
        lines = ((stats["p50"], "P50", "-"), (stats["p90_1y"], "P90 (1 year)", "--"))
        first, last = per_mw.index.min(), per_mw.index.max()
        for value, label, dash in lines:
            # Line over the bars only; its label sits in the free space to the right.
            ax.hlines(value, first - 0.5, last + 0.5, color=INK, linewidth=1.1, linestyles=dash)
            ax.text(last + 0.9, value, f"{label}: {value:,.0f}", fontsize=8.5, color=INK,
                    va="center")
        ax.set_ylim(per_mw.min() * 0.85, per_mw.max() * 1.05)
        ax.set_xlim(first - 0.8, last + 6.5)
        ax.set_xticks(range(first - first % 5 + 5, last + 1, 5))
        unit, what = UNIT.get(park.technology, ("MWh/MW", "energy per MW"))
        style(ax, f"{_title(park)}: {what} per weather year ({park.site})", unit)
    return save(fig, path)


def fig_monthly(shares: dict[str, tuple[pd.Series, pd.Series]], parks: list[Park],
                path: Path) -> Path:
    fig, axes = plt.subplots(1, len(parks), figsize=(4.6 * len(parks), 3.4), squeeze=False)
    months = list(range(1, 13))
    for ax, park in zip(axes[0], parks, strict=True):
        site, national = shares[park.name]
        colour = COLOURS.get(park.technology, BLUE)
        ax.plot(months, 100 * national.reindex(months).to_numpy(), color=INK_2, linewidth=1.6,
                linestyle="--", marker="o", markersize=3, label="Germany (national fleet)")
        ax.plot(months, 100 * site.reindex(months).to_numpy(), color=colour, linewidth=2.2,
                marker="o", markersize=4, label="Site model")
        ax.set_xticks(months, ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
        ax.legend(frameon=False, fontsize=8.5, loc="best")
        style(ax, f"{_title(park)}: share of annual energy by month", "% of annual energy")
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
def _yield_table(park: Park, annual: pd.Series) -> str:
    st = p_values(annual)
    trend = yield_trend(annual)
    per_mw = 1.0 / park.capacity_mw
    unit = UNIT.get(park.technology, ("MWh/MW", ""))[0]
    rows = [
        ("Weather years", f"{annual.index.min()}-{annual.index.max()} ({st['years']})"),
        ("P50 (median year)", f"{st['p50'] / 1e3:,.1f} GWh = {st['p50'] * per_mw:,.0f} {unit}"),
        ("Mean", f"{st['mean'] / 1e3:,.1f} GWh"),
        ("Year-to-year variability (std, CoV)", f"{st['std'] / 1e3:,.1f} GWh ({st['cov']:.1%})"),
        ("P90, one year",
         f"{st['p90_1y'] / 1e3:,.1f} GWh ({st['p90_1y'] / st['mean'] - 1:+.1%} vs mean)"),
        ("P90, 10-year average",
         f"{st['p90_10y'] / 1e3:,.1f} GWh ({st['p90_10y'] / st['mean'] - 1:+.1%})"),
        ("Worst / best year", f"{st['min_year']}: {st['min'] / 1e3:,.1f} GWh "
                              f"({st['min'] / st['mean'] - 1:+.1%}) / {st['max_year']}: "
                              f"{st['max'] / 1e3:,.1f} GWh ({st['max'] / st['mean'] - 1:+.1%})"),
        ("Linear trend", f"{trend['per_decade_pct']:+.1f}% per decade"),
    ]
    return pd.DataFrame(rows, columns=["", _title(park)]).to_markdown(index=False)


def _validation_table(tables: dict[str, pd.DataFrame], parks: list[Park]) -> str:
    rows = []
    for park in parks:
        for year, r in tables[park.name].iterrows():
            rows.append({
                "Park": _title(park), "Year": year,
                "Hourly correlation with national": f"{r['correlation']:.2f}",
                "Capture rate, site": f"{r['site_capture_rate']:.3f}",
                "Capture rate, national": f"{r['national_capture_rate']:.3f}",
                "Site capture price (EUR/MWh)": f"{r['site_capture_eur_mwh']:.2f}",
            })
    return pd.DataFrame(rows).to_markdown(index=False)


def write_day04_report(settings: Settings) -> dict[str, Path | None]:
    tz = settings.timezone
    proc = settings.processed_dir
    parks = sited_parks(settings)
    store = RawStore(settings.raw_dir, source="open_meteo")
    prices = to_hourly(pd.read_parquet(proc / "prices_native.parquet")[["price_eur_mwh"]])
    national = to_hourly(pd.read_parquet(proc / "power_15min.parquet"))

    mw, annuals, shares, checks, sites = {}, {}, {}, {}, []
    for park in parks:
        mw[park.name] = pd.read_parquet(proc / f"generation_{park.name}.parquet")["mw"]
        annuals[park.name] = annual_energy(mw[park.name], tz)
        dataset = weather_dataset(park)
        grid = store.read_meta(dataset, store.months(dataset)[-1])["grid"]
        sites.append({
            "Park": _title(park), "Site": park.site,
            "Requested": f"{park.latitude:.2f} N, {park.longitude:.2f} E",
            "ERA5 grid point": f"{grid['latitude']:.2f} N, {grid['longitude']:.2f} E, "
                               f"{grid['elevation_m']:.0f} m",
            "Capacity": f"{park.capacity_mw:g} MW"
                        + ("p (DC)" if park.technology == "solar" else ""),
            "Model": ", ".join(f"{k}={v}" for k, v in park.model.items()),
        })

    complete = all(len(a) >= 2 for a in annuals.values())
    fig_dir = settings.reports_dir / "figures"
    figs: dict[str, Path | None] = {"annual": None, "monthly": None}
    yields_text, checks_text, findings = (
        "No complete weather year in range (at least two are needed).",
        "No complete year with both site and national data.", [])
    if complete:
        figs["annual"] = fig_annual(annuals, parks, fig_dir / "day04_annual_yield.png")
        yields_text = "\n\n".join(_yield_table(p, annuals[p.name]) for p in parks)
        years = _overlap_years(settings, annuals[parks[0].name])
        if years:
            for park in parks:
                nat = national[TECHNOLOGIES[park.technology]]
                checks[park.name] = site_vs_national(
                    mw[park.name], nat, prices["price_eur_mwh"], tz, years)
                shares[park.name] = (monthly_shares(mw[park.name], tz, years),
                                     monthly_shares(nat, tz, years))
            figs["monthly"] = fig_monthly(shares, parks, fig_dir / "day04_monthly_shares.png")
            checks_text = _validation_table(checks, parks)
        for park in parks:
            st, trend = p_values(annuals[park.name]), yield_trend(annuals[park.name])
            unit = UNIT.get(park.technology, ("MWh/MW", ""))[0]
            line = (f"- **{_title(park)}:** P50 {st['p50'] / park.capacity_mw:,.0f} {unit}; "
                    f"one year in ten falls below {st['p90_1y'] / st['mean'] - 1:+.1%} of the "
                    f"mean, the worst year ({st['min_year']}) was "
                    f"{st['min'] / st['mean'] - 1:+.1%}; trend "
                    f"{trend['per_decade_pct']:+.1f}% per decade.")
            if park.name in checks:
                c = checks[park.name]
                line += (f" Hourly correlation with the national fleet "
                         f"{c['correlation'].min():.2f}-{c['correlation'].max():.2f}; "
                         f"capture rate site "
                         f"{c['site_capture_rate'].mean():.3f} vs national "
                         f"{c['national_capture_rate'].mean():.3f} (average of the check years).")
            findings.append(line)

    charts = "\n\n".join(f"![{k}](figures/{p.name})" for k, p in figs.items() if p)
    report = f"""# Day 4 report: weather to power

Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab weather`.
Weather: {settings.weather_license}. Hourly ERA5 reanalysis per site; radiation converted from
end-of-hour to interval-beginning labels (checked against the sun's position).

## 1. The parks

{pd.DataFrame(sites).to_markdown(index=False)}

## 2. Annual energy over the weather years (volume risk)

P50 = median weather year. P90 = energy exceeded in 90% of years (normal approximation,
mean − 1.2816 σ); for a 10-year average σ shrinks by √10.

{yields_text}

## 3. Checks against national data

The site models are compared with national generation of the same technology (Day 1)
and priced with the same hourly day-ahead prices (capture rate as on Day 2).

{checks_text}

## 4. What the numbers say

{chr(10).join(findings) if findings else "-"}

## 5. Charts

{charts}
"""
    path = settings.reports_dir / "day04_generation.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report)
    log.info("wrote %s", path)
    return {"report": path, **figs}
