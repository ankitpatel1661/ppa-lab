"""Step 3 report: PPA structures back-tested on 2024-2025 for the illustrative parks.

Output:
    reports/step03_ppa_structures.md
    reports/figures/step03_*.png
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.capture import TECHNOLOGIES, prices_on_grid
from ppa_lab.analysis.plotting import BLUE, GRID, INK, INK_2, YELLOW, save, style
from ppa_lab.config import Park, Settings
from ppa_lab.pricing.backtest import STRUCTURE_LABELS, backtest, park_energy, summarise

log = logging.getLogger(__name__)

# Colour follows the structure in every Step 3 chart; merchant is the grey reference.
STRUCTURE_COLOURS = {"merchant": INK_2, "pay_as_produced": BLUE, "baseload": YELLOW}


def run_park(prices_grid: pd.Series, power: pd.DataFrame, park: Park, settings: Settings):
    """Back-test one park: returns (energy, cash flows, strikes, summary)."""
    years = sorted({y for d in settings.delivery_years for y in (d - 1, d)})
    energy = park_energy(power[TECHNOLOGIES[park.technology]], park.capacity_mw,
                         park.full_load_hours, settings.timezone, years)
    cash, strikes, plan = backtest(prices_grid, energy, settings.timezone,
                                   list(settings.delivery_years), settings.floor_eur_mwh)
    return energy, cash, strikes, summarise(cash, energy, settings.timezone, plan)


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_annual(results: dict[str, tuple], parks: tuple[Park, ...], years: tuple[int, ...],
               path: Path) -> Path:
    order = list(STRUCTURE_LABELS)
    fig, axes = plt.subplots(len(parks), len(years), figsize=(5.2 * len(years), 2.9 * len(parks)),
                             squeeze=False, sharex=True)
    for r, park in enumerate(parks):
        summary = results[park.name][3]
        for c, year in enumerate(years):
            ax = axes[r][c]
            per_mwh = summary.loc[year, "revenue_eur_per_mwh"].reindex(order)
            colours = [INK_2 if s == "merchant" else BLUE for s in order]
            ax.barh(range(len(order)), per_mwh.to_numpy(), color=colours, height=0.62)
            ax.axvline(per_mwh["merchant"], color=INK_2, linewidth=0.9, linestyle="--")
            for i, value in enumerate(per_mwh.to_numpy()):
                ax.text(value + 1, i, f"{value:.1f}", va="center", fontsize=8.5, color=INK)
            ax.set_yticks(range(len(order)), [STRUCTURE_LABELS[s] for s in order] if c == 0
                          else [""] * len(order))
            ax.invert_yaxis()
            style(ax, f"{park.name.replace('_', ' ').title()}, delivery {year}", "")
            ax.grid(axis="x", color=GRID, linewidth=0.8)
            ax.grid(axis="y", visible=False)
    for ax in axes[-1]:
        ax.set_xlabel("EUR per MWh produced (dashed: merchant)", color=INK_2, fontsize=9)
    return save(fig, path)


def fig_monthly(cash: pd.DataFrame, park: Park, tz: str, path: Path) -> Path:
    local = cash.index.tz_convert(tz).tz_localize(None)
    monthly = cash.groupby(pd.PeriodIndex(local, freq="M")).sum() / 1e3
    x = monthly.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.axhline(0, color=INK_2, linewidth=0.8)
    for structure, colour in STRUCTURE_COLOURS.items():
        ax.plot(x, monthly[structure].to_numpy(), color=colour, linewidth=2, marker="o",
                markersize=3, label=STRUCTURE_LABELS[structure])
    # Direct labels at the line ends, nudged apart so they never overlap.
    span = float(np.ptp(monthly[list(STRUCTURE_COLOURS)].to_numpy())) or 1.0
    ends = sorted((float(monthly[st].iloc[-1]), st) for st in STRUCTURE_COLOURS)
    placed: list[float] = []
    for value, structure in ends:
        y = max(value, placed[-1] + 0.07 * span) if placed else value
        placed.append(y)
        ax.text(x[-1] + pd.Timedelta(days=10), y, STRUCTURE_LABELS[structure].split(" (")[0],
                color=INK, fontsize=8.5, va="center")
    ax.set_xlim(x[0] - pd.Timedelta(days=10), x[-1] + pd.Timedelta(days=120))
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncols=1)
    style(ax, f"{park.name.replace('_', ' ').title()} ({park.capacity_mw:.0f} MW): "
              "monthly revenue by structure (seasonality and liquidity)", "EUR thousand")
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
def _park_table(summary: pd.DataFrame) -> str:
    view = summary.reset_index()
    view["Structure"] = view["structure"].map(STRUCTURE_LABELS)
    numeric = view.select_dtypes("number").columns.drop("year")
    view[numeric] = view[numeric].round(2) + 0.0  # + 0.0 turns -0.00 into 0.00
    out = pd.DataFrame(
        {
            "Year": view["year"],
            "Structure": view["Structure"],
            "Revenue (EUR m)": view["revenue_eur_m"].map("{:.2f}".format),
            "EUR/MWh": view["revenue_eur_per_mwh"].map("{:.2f}".format),
            "vs merchant (EUR/MWh)": view["vs_merchant_eur_per_mwh"].map("{:+.2f}".format),
            "Plan (EUR/MWh)": view["plan_eur_per_mwh"].map("{:.2f}".format),
            "Surprise vs plan": view["vs_plan_eur_per_mwh"].map("{:+.2f}".format),
            "Worst month (EUR k)": view["worst_month_eur_k"].map("{:.0f}".format),
        }
    )
    return out.to_markdown(index=False)


def _strikes_table(strikes: pd.DataFrame) -> str:
    view = strikes.reset_index().rename(
        columns={
            "year": "Delivery year",
            "pay_as_produced_strike": "PaP strike (EUR/MWh)",
            "baseload_strike": "Baseload strike (EUR/MWh)",
            "band_mw": "Band (MW)",
        }
    )
    return view.to_markdown(index=False, floatfmt=(".0f", ".2f", ".2f", ".2f"))


def _findings(park: Park, summary: pd.DataFrame, floor: float) -> str:
    year = int(summary.index.get_level_values("year").max())
    s = summary.loc[year]
    merchant = s.loc["merchant", "revenue_eur_per_mwh"]

    def diff(structure: str) -> str:
        return f"{s.loc[structure, 'vs_merchant_eur_per_mwh']:+.2f}"

    clause_cost = (s.loc["pay_as_produced", "revenue_eur_per_mwh"]
                   - s.loc["pap_negative_clause", "revenue_eur_per_mwh"])
    surprise = s["vs_plan_eur_per_mwh"]
    return (
        f"- **{park.name.replace('_', ' ').title()}, {year}:** merchant earned "
        f"{merchant:.2f} EUR/MWh. Against that, the pay-as-produced PPA made "
        f"{diff('pay_as_produced')} EUR/MWh and the baseload PPA {diff('baseload')} EUR/MWh. "
        f"The negative-price clause cost the producer {clause_cost:.2f} EUR/MWh; a floor at "
        f"{floor:.0f} EUR/MWh (or curtailing below it) added {diff('merchant_with_floor')} "
        f"EUR/MWh. Surprise against plan: merchant {surprise['merchant']:+.2f}, "
        f"pay-as-produced {surprise['pay_as_produced']:+.2f}, baseload "
        f"{surprise['baseload']:+.2f} EUR/MWh."
    )


def write_step03_report(settings: Settings) -> dict[str, Path | None]:
    tz = settings.timezone
    proc = settings.processed_dir
    prices = pd.read_parquet(proc / "prices_native.parquet")
    power = pd.read_parquet(proc / "power_15min.parquet")
    prices_grid = prices_on_grid(prices, power.index)

    results = {park.name: run_park(prices_grid, power, park, settings) for park in settings.parks}

    fig_dir = settings.reports_dir / "figures"
    figs: dict[str, Path | None] = {
        "annual": fig_annual(results, settings.parks, settings.delivery_years,
                             fig_dir / "step03_structures_annual.png"),
    }
    first = settings.parks[0]
    figs["monthly"] = fig_monthly(results[first.name][1], first, tz,
                                  fig_dir / "step03_structures_monthly.png")

    sections = []
    for park in settings.parks:
        _, _, strikes, summary = results[park.name]
        sections.append(
            f"### {park.name.replace('_', ' ').title()}: {park.capacity_mw:.0f} MW "
            f"{park.technology.replace('_', ' ')}, {park.full_load_hours:.0f} full-load hours\n\n"
            f"Strikes, fixed at the end of the previous year:\n\n{_strikes_table(strikes)}\n\n"
            f"Results:\n\n{_park_table(summary)}\n"
        )
    findings = "\n".join(
        _findings(park, results[park.name][3], settings.floor_eur_mwh) for park in settings.parks
    )

    report = f"""# Step 3 report: PPA structures back-tested

Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab ppa`.
Data: {settings.energy_charts.license}.
Delivery years: {", ".join(map(str, settings.delivery_years))}.

**Set-up.** Each park uses the national generation profile of its technology, scaled to
capacity x full-load hours in every year. A contract for delivery year Y is signed at the
end of Y-1 at Y-1's fair price: the pay-as-produced strike is Y-1's capture price, the
baseload strike Y-1's base price, and the band delivers the expected annual energy flat.
That is a naive stand-in for forward prices. Cash flows are to the producer, per
quarter-hour, without option premiums, balancing or credit costs. Maths: `METHODOLOGY.md`.

**Plan and surprise.** The plan is what each structure would have earned per MWh had the
delivery year looked like the year before (same terms on last year's prices and profile):
the expectation at signing. Surprise = realised − plan is the risk each structure left with
the producer. The worst month shows liquidity: a baseload seller can have negative months.

## 1. Results per park

{chr(10).join(sections)}
## 2. What the numbers say

{findings}

## 3. Charts

![Revenue per MWh by structure](figures/{figs["annual"].name})

![Monthly revenue by structure](figures/{figs["monthly"].name})
"""
    report_path = settings.reports_dir / "step03_ppa_structures.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    log.info("wrote %s", report_path)
    return {"report": report_path, **figs}
