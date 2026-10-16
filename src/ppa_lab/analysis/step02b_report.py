"""Step 2b report: the TSOs' own data (roadmap item 6).

Output:
    reports/step02b_tso_data.md
    reports/figures/step02b_imbalance_cost.png
    data/processed/balancing.json    measured imbalance costs (input for the cost assumptions)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.balancing import (
    TECHNOLOGIES,
    capture_prices,
    energy_mwh,
    hourly_mean,
    imbalance_cost,
    imbalance_frame,
    load_tso_data,
    market_value_check,
    quarter_hour_prices,
    window_cost,
)
from ppa_lab.analysis.plotting import BLUE, ORANGE, YELLOW, save, style
from ppa_lab.analysis.step02_report import MARKET_VALUES_FILE
from ppa_lab.analysis.step05_report import hourly_prices
from ppa_lab.config import Settings
from ppa_lab.pricing.eeg import official_market_values

log = logging.getLogger(__name__)

LABELS = {"wind_onshore": "Wind onshore", "wind_offshore": "Wind offshore", "solar": "Solar"}
COLOURS = {"wind_onshore": BLUE, "wind_offshore": YELLOW, "solar": ORANGE}


def fig_imbalance(costs: dict[str, pd.DataFrame], path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.6))
    years = sorted({y for t in costs.values() for y in t.index})
    width = 0.8 / len(costs)
    for i, (tech, table) in enumerate(costs.items()):
        x = np.arange(len(years)) + (i - (len(costs) - 1) / 2) * width
        ax.bar(x, table.reindex(years)["cost_eur_mwh"], width=width, color=COLOURS[tech],
               label=LABELS[tech])
    ax.set_xticks(range(len(years)), [str(y) for y in years])
    ax.legend(frameon=False, fontsize=8.5)
    style(ax, "Imbalance cost of the national portfolio, day-ahead forecast errors at reBAP",
          "EUR per MWh produced")
    return save(fig, path)


def _annual_check(prices: pd.Series, online: dict[str, pd.Series], settings: Settings,
                  tz: str) -> pd.DataFrame:
    rows = []
    for ref in settings.references:
        tech = ref.metric.replace("capture_price_", "").replace("_ct_kwh", "")
        if tech not in online:
            continue
        ours = capture_prices(prices, hourly_mean(online[tech]), tz, "Y")
        if ref.year in ours.index:
            rows.append({"technology": tech, "year": ref.year,
                         "official_eur_mwh": ref.value * 10.0,
                         "online_eur_mwh": float(ours.loc[ref.year])})
    table = pd.DataFrame(rows)
    table["difference"] = table["online_eur_mwh"] - table["official_eur_mwh"]
    return table


def write_step02b_report(settings: Settings) -> dict[str, Path | None]:
    tz = settings.timezone
    path = settings.reports_dir / "step02b_tso_data.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = f"{datetime.now(UTC):%Y-%m-%d %H:%M}"
    header = (f"# Step 2b report: the TSOs' own data\n\nGenerated {stamp} UTC by "
              "`ppa-lab balancing`.\n\n")
    tso = load_tso_data(settings.raw_dir)
    if tso is None:
        path.write_text(header + "No TSO data found: run `ppa-lab tso` (netztransparenz.de, "
                        "needs a free API client) and `ppa-lab forecasts` (ENTSO-E) first.\n")
        return {"report": path, "results": None, "figure": None}

    prices = hourly_prices(settings)
    measured = pd.read_parquet(settings.processed_dir / "power_15min.parquet")
    native = pd.read_parquet(settings.processed_dir / "prices_native.parquet")["price_eur_mwh"]
    official = {tech: official_market_values(settings.reference_dir / MARKET_VALUES_FILE, col)
                for tech, (_, _, col) in TECHNOLOGIES.items()}

    # 1. Market values: measured feed-in against the TSOs' online extrapolation.
    monthly = market_value_check(prices, measured.pipe(lambda m: m.resample("1h").mean()),
                                 tso["online"], official, tz)
    monthly["measured_gap"] = monthly["measured"] - monthly["official"]
    monthly["online_gap"] = monthly["online"] - monthly["official"]
    year = monthly.index.year
    gaps = monthly.groupby(["technology", year])[["measured_gap", "online_gap"]].mean()
    outliers = monthly[monthly["online_gap"].abs() > 1.0]
    annual = _annual_check(prices, tso["online"], settings, tz)
    energy = pd.DataFrame({
        f"{tech} measured": energy_mwh(measured[col], tz) / 1e6
        for tech, (col, _, _) in TECHNOLOGIES.items()} | {
        f"{tech} online": energy_mwh(tso["online"][tech], tz) / 1e6 for tech in TECHNOLOGIES})

    # 2. Balancing: day-ahead forecast errors at the imbalance price.
    grid = measured.index
    price_qh = quarter_hour_prices(native, grid)
    short, long = tso["rebap"]["reBAP unterdeckt"], tso["rebap"]["reBAP ueberdeckt"]
    pool_start = str(settings.ppa.analog_pool_start) if settings.ppa else "2025-10-01"
    end = str(settings.end)
    previous = (pd.Timestamp(pool_start) - pd.DateOffset(years=1)).date()
    before_end = (pd.Timestamp(pool_start) - pd.Timedelta(days=1)).date()
    costs, recent, prior = {}, {}, {}
    for tech, (col, _, _) in TECHNOLOGIES.items():
        frame = imbalance_frame(measured[col], tso["forecast"][col], price_qh, short, long, tz)
        costs[tech] = imbalance_cost(frame, tz)
        recent[tech] = window_cost(frame, pool_start, end, tz)
        prior[tech] = window_cost(frame, str(previous), str(before_end), tz)

    fig = fig_imbalance(costs, settings.reports_dir / "figures" / "step02b_imbalance_cost.png")
    out_json = settings.processed_dir / "balancing.json"
    out_json.write_text(json.dumps({
        "generated_utc": f"{datetime.now(UTC):%Y-%m-%d %H:%M}",
        "window": [pool_start, end], "previous_window": [str(previous), str(before_end)],
        "imbalance_cost_eur_mwh": recent, "previous_imbalance_cost_eur_mwh": prior,
        "by_year": {tech: {str(y): r for y, r in t.to_dict(orient="index").items()}
                    for tech, t in costs.items()},
        "market_value_gap_eur_mwh": {f"{tech} {y}": g for (tech, y), g in
                                     gaps.to_dict(orient="index").items()},
    }, indent=1, default=float))

    def fmt(x: float) -> str:
        return f"{x:+.2f}".replace("-", "−")

    gap_rows = ["| Technology | Year | Measured feed-in − official | Online extrapolation − "
                "official |", "|---|---|---|---|"]
    for (tech, y), g in gaps.iterrows():
        gap_rows.append(f"| {LABELS[tech]} | {y} | {fmt(g['measured_gap'])} | "
                        f"{fmt(g['online_gap'])} |")
    annual_rows = ["| Technology | Year | Official (EUR/MWh) | With the online extrapolation | "
                   "Difference |", "|---|---|---|---|---|"]
    for _, r in annual.iterrows():
        annual_rows.append(f"| {LABELS[r['technology']]} | {r['year']} | "
                           f"{r['official_eur_mwh']:.2f} | {r['online_eur_mwh']:.2f} | "
                           f"{fmt(r['difference'])} |")
    outlier_text = ", ".join(f"{LABELS[r['technology']].lower()} {m} ({fmt(r['online_gap'])})"
                             for m, r in outliers.iterrows()) or "none"
    cost_rows = ["| Year | " + " | ".join(f"{LABELS[t]}: cost (EUR/MWh); forecast error"
                                          for t in costs) + " | Mean distance of reBAP from the "
                 "day-ahead price (EUR/MWh) |", "|---|" + "---|" * (len(costs) + 1)]
    for y in sorted({y for t in costs.values() for y in t.index}):
        cells = [f"{costs[t].loc[y, 'cost_eur_mwh']:.2f}; {costs[t].loc[y, 'relative_error']:.1%}"
                 if y in costs[t].index else "–" for t in costs]
        spread = next(iter(costs.values())).loc[y, "spread_eur_mwh"]
        cost_rows.append(f"| {y} | " + " | ".join(cells) + f" | {spread:.1f} |")
    report = header + f"""Data: netztransparenz.de (reBAP, the TSOs' online extrapolation of
wind and solar output), ENTSO-E (day-ahead wind and solar forecasts for DE-LU), Energy-Charts
(measured output, day-ahead prices).

## 1. The official market values come from the TSOs' extrapolation (backlog PPA-2b)

Our capture prices with the measured feed-in (Energy-Charts) were above the official market
values, most for wind. The TSOs compute those values from their online extrapolation of the
output. With that extrapolation and our day-ahead prices the official monthly values are
reproduced (EUR/MWh, mean over the months of the year):

{chr(10).join(gap_rows)}

Months with the extrapolation more than 1 EUR/MWh off: {outlier_text}. The annual values
(Jahresmarktwerte) the same way:

{chr(10).join(annual_rows)}

The extrapolation counts more energy than the measured feed-in (TWh):

{energy.round(1).rename_axis("Year").to_markdown()}

The measured feed-in lacks output curtailed in congested or negative hours, which are cheap: so
its capture price is higher. The difference of Step 2 is explained, not an error of ours.

## 2. What balancing costs

A direct marketer sells its day-ahead forecast at the day-ahead price and settles the rest at
the imbalance price reBAP. Per MWh produced, with each month's forecast scaled to the month's
actual energy (only timing and shape errors count):

{chr(10).join(cost_rows)}

Forecast error: mean absolute error over mean output. The cost follows the distance of reBAP
from the day-ahead price more than the forecast quality, which hardly changed. Over the last 12
months ({pool_start} to {end}, the analog pool of the 2027 scenarios):
{", ".join(f"{LABELS[t].lower()} {recent[t]:.2f}" for t in recent)} EUR/MWh (the 12 months
before: {", ".join(f"{LABELS[t].lower()} {prior[t]:.2f}" for t in prior)}).

This is the national portfolio. A single park's forecast errors are larger, but a direct
marketer pools many parks and corrects part of its error intraday before delivery: the two
effects pull in opposite directions, so the national cost is a fair estimate for a large
marketer's pool. The cost assumptions of Step 7 (`[ppa.parks.*] balancing_eur_mwh`) are this
measured cost plus a marketing fee.

![Imbalance cost by year](figures/{fig.name})

Results: `data/processed/{out_json.name}`.
"""
    path.write_text(report)
    log.info("wrote %s and %s", path, out_json)
    return {"report": path, "results": out_json, "figure": fig}
