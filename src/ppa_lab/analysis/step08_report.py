"""Step 8 report: hedging the parks' output with power futures.

Output:
    data/processed/hedging.json        key results (the memo and the dashboard read them)
    reports/step08_hedging.md
    reports/figures/step08_*.png
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.plotting import BLUE, INK, INK_2, save, style
from ppa_lab.analysis.step05_report import hourly_prices
from ppa_lab.analysis.step06_report import load_weather_inputs, parks
from ppa_lab.analysis.step07_report import scenario_set, to_strict_json
from ppa_lab.config import Settings
from ppa_lab.dashboard import Assumptions, default_assumptions, offer
from ppa_lab.hedging.hedge import (
    STRATEGIES,
    backtest_hedge,
    buyer_hedge,
    hedge_payoffs,
    hedge_strategies,
    min_variance_hedge,
    model_forwards,
)
from ppa_lab.hedging.products import MONTHS, QUARTERS, product_masks
from ppa_lab.weather.yields import annual_energy, p_values

log = logging.getLogger(__name__)

GREY = "#a9a9a4"


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_cfar(tables: dict[str, pd.DataFrame], names: dict[str, str], path: Path) -> Path:
    fig, axes = plt.subplots(1, len(tables), figsize=(11, 3.6))
    for ax, (park, t) in zip(np.atleast_1d(axes), tables.items(), strict=True):
        values = t["cfar_eur"] / 1e6
        colours = [GREY] + [BLUE] * (len(values) - 1)
        ax.barh(range(len(values)), values, color=colours)
        ax.set_yticks(range(len(values)), [STRATEGIES[k] for k in t.index], fontsize=8)
        ax.invert_yaxis()
        for i, v in enumerate(values):
            ax.text(v, i, f" {v:.2f}", va="center", fontsize=8, color=INK)
        ax.set_xlabel("Cash flow at risk 95% (EUR m)", color=INK_2, fontsize=9)
        ax.grid(axis="x", color="#e2e2de")
        style(ax, f"{names[park]}: merchant risk by hedge", "")
    return save(fig, path)


def fig_months(monthly: dict[str, pd.DataFrame], names: dict[str, str], path: Path) -> Path:
    fig, axes = plt.subplots(1, len(monthly), figsize=(11, 3.4), sharey=False)
    x = np.arange(12)
    for ax, (park, t) in zip(np.atleast_1d(axes), monthly.items(), strict=True):
        ax.bar(x - 0.2, t["expected_mw"], width=0.4, color=GREY, label="expected output")
        ax.bar(x + 0.2, t["hedge_mw"], width=0.4, color=BLUE, label="minimum-variance hedge")
        ax.axhline(0, color=INK_2, linewidth=0.7)
        ax.set_xticks(x, [m[1:] for m in t.index], fontsize=8)
        ax.set_xlabel("Month", color=INK_2, fontsize=9)
        style(ax, f"{names[park]}: monthly hedge vs expected output", "MW")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=8)
    return save(fig, path)


def fig_distribution(cash: np.ndarray, hedged: np.ndarray, label: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.3))
    bins = np.linspace(min(cash.min(), hedged.min()), max(cash.max(), hedged.max()), 50) / 1e6
    ax.hist(cash / 1e6, bins=bins, color=GREY, alpha=0.8, label="merchant")
    ax.hist(hedged / 1e6, bins=bins, color=BLUE, alpha=0.75, label="with Cal base hedge (min-var)")
    for values, colour in ((cash, INK_2), (hedged, BLUE)):
        ax.axvline(np.quantile(values, 0.05) / 1e6, color=colour, linestyle="--", linewidth=1.4)
    ax.set_xlabel("Annual revenue (EUR m); dashed: 5% quantile", color=INK_2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5)
    style(ax, f"{label}: annual revenue with and without the hedge", "Scenarios")
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _strategies_md(tables: dict[str, pd.DataFrame], names: dict[str, str]) -> str:
    rows = []
    for park, t in tables.items():
        for key, r in t.iterrows():
            rows.append({
                "Park": names[park], "Strategy": STRATEGIES[key],
                "Sold (MW, year average)": f"{r['hedge_mw']:.1f}",
                "Hedge ratio": f"{r['hedge_ratio']:.0%}",
                "CFaR95 (EUR m)": f"{r['cfar_eur'] / 1e6:.2f}",
                "CFaR reduction": f"{r['cfar_reduction']:.0%}",
                "Variance removed": f"{r['effectiveness']:.0%}",
            })
    return pd.DataFrame(rows).to_markdown(index=False)


def _market_md(quotes, forwards: dict[str, float], year: int) -> str:
    rows = []
    for q in quotes:
        if q.delivery_year != year:
            continue
        model = forwards.get(q.product)
        rows.append({"Product": q.product, "Market quote (EUR/MWh)": f"{q.price_eur_mwh:.2f}",
                     "Quote date": str(q.date), "Model forward (EUR/MWh)": f"{model:.2f}",
                     "Market − model": f"{q.price_eur_mwh - model:+.2f}",
                     "Source": f"[link]({q.source}) ({q.source.split('/')[2]})"})
    return pd.DataFrame(rows).to_markdown(index=False) if rows else "No market quotes configured."


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def write_step08_report(settings: Settings) -> dict[str, Path | None]:
    hg, ppa, tz = settings.hedging, settings.ppa, settings.timezone
    path = settings.reports_dir / "step08_hedging.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Step 8 report: hedging with power futures\n\n"
              f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab hedging`.\n\n")
    inputs = load_weather_inputs(settings)
    if inputs is None:
        path.write_text(header + "No site weather or generation found: run `ppa-lab weather` "
                        "first (Step 4).\n")
        return {"report": path, "results": None, "cfar": None, "months": None,
                "distribution": None}

    solar, wind = parks(settings)
    names = {solar.name: "Solar park", wind.name: "Wind park"}
    q = ppa.risk_quantile
    scen = scenario_set(settings, inputs, pd.Timestamp(ppa.analog_pool_start))
    prices, hours = scen.prices, scen.prices.shape[1]
    masks = product_masks(scen.index, tz)
    forwards = model_forwards(prices, masks)
    history = hourly_prices(settings)
    pricing_file = settings.processed_dir / "ppa_pricing.json"
    pricing = json.loads(pricing_file.read_text()) if pricing_file.exists() else None

    tables, monthly, results, hedged_lead = {}, {}, {}, None
    for park in names:
        volumes = scen.volume(park)
        cash = (prices * volumes).sum(axis=1)
        average_mw = float(volumes.sum(axis=1).mean()) / hours
        t = hedge_strategies(cash, prices, masks, forwards, average_mw, q)
        tables[park] = t.drop(columns=["products_mw"], errors="ignore")
        month_mw = t.loc["months_min_variance", "products_mw"]
        monthly[park] = pd.DataFrame({
            "expected_mw": [float(volumes[:, masks[m]].mean()) for m in MONTHS],
            "hedge_mw": [month_mw[m] for m in MONTHS]}, index=MONTHS)
        if hedged_lead is None:
            payoff = hedge_payoffs(prices, masks, forwards, ["cal_base"])
            hedged_lead = (park, cash, cash + payoff @ min_variance_hedge(cash, payoff))
        buyer = buyer_hedge(prices, volumes, q)
        annual = annual_energy(inputs["gen"][park], tz).loc[
            settings.weather_first_year:settings.scenarios.weather_last_year]
        p50_mw = p_values(annual)["p50"] / 8760
        ratio = float(t.loc["cal_base_min_variance", "hedge_ratio"])
        back = backtest_hedge(history, inputs["gen"][park], tz, list(hg.backtest_years),
                              ratio * p50_mw)
        market = {}
        if pricing is not None and park in pricing["parks"]:
            base_quotes = [x for x in hg.market_quotes
                           if x.product == "cal_base" and x.delivery_year == ppa.start_year]
            if base_quotes:
                latest = max(base_quotes, key=lambda x: x.date)
                d = default_assumptions(pricing, park)
                model_forward = pricing["parks"][park]["stack_eur_mwh"]["forward"]
                shift = latest.price_eur_mwh / model_forward - 1.0
                market = {"quote": latest.price_eur_mwh, "date": str(latest.date),
                          "model_forward": model_forward,
                          "indicative_model": offer(pricing, park, d)["stack"]["indicative"],
                          "indicative_market": offer(pricing, park, Assumptions(
                              **{**d.__dict__, "forward_shift": shift}))["stack"]["indicative"]}
        results[park] = {
            "average_mw": average_mw, "p50_mw": p50_mw,
            "strategies": t.drop(columns=["products_mw"], errors="ignore").to_dict(orient="index"),
            "months_min_variance_mw": month_mw,
            "quarters_min_variance_mw": t.loc["quarters_min_variance", "products_mw"],
            "buyer": buyer,
            "backtest": {str(k): v for k, v in back.to_dict(orient="index").items()},
            "market_check": market,
        }

    out_json = settings.processed_dir / "hedging.json"
    out_json.write_text(json.dumps(to_strict_json({
        "generated_utc": f"{datetime.now(UTC):%Y-%m-%d %H:%M}", "delivery_year": ppa.start_year,
        "model_forwards": {k: v for k, v in forwards.items() if k in ("cal_base", "cal_peak",
                                                                       *QUARTERS)},
        "market_quotes": [{"product": x.product, "delivery_year": x.delivery_year,
                           "price_eur_mwh": x.price_eur_mwh, "date": str(x.date),
                           "source": x.source} for x in hg.market_quotes],
        "parks": results}), indent=1, allow_nan=False))

    fig_dir = settings.reports_dir / "figures"
    lead, lead_cash, lead_hedged = hedged_lead
    figs = {
        "cfar": fig_cfar(tables, names, fig_dir / "step08_cfar.png"),
        "months": fig_months(monthly, names, fig_dir / "step08_monthly_hedge.png"),
        "distribution": fig_distribution(lead_cash, lead_hedged, names[lead],
                                         fig_dir / "step08_revenue.png"),
    }

    curve = pd.DataFrame({"Product": ["Cal base", "Cal peak", *QUARTERS],
                          "Model forward (EUR/MWh)": [f"{forwards[k]:.2f}" for k in
                                                      ("cal_base", "cal_peak", *QUARTERS)]})
    buyer_rows = pd.DataFrame([{
        "Park": names[p], "Full band (MW)": f"{r['buyer']['band_mw']:.2f}",
        "Premium, full band": f"{r['buyer']['premium_full_band']:.2f}",
        "Minimum-variance band (MW)": f"{r['buyer']['min_variance_mw']:.2f} "
                                      f"({r['buyer']['min_variance_ratio']:.0%})",
        "Premium, min-var band": f"{r['buyer']['premium_min_variance']:.2f}"}
        for p, r in results.items()]).to_markdown(index=False)
    back_rows = []
    for p, r in results.items():
        for y, b in r["backtest"].items():
            back_rows.append({
                "Park": names[p], "Year": y, "Forward proxy (EUR/MWh)": f"{b['forward_proxy']:.2f}",
                "Realised base (EUR/MWh)": f"{b['realised_base']:.2f}",
                "Merchant (EUR m)": f"{b['merchant_revenue_eur'] / 1e6:.2f}",
                "Hedge P&L (EUR m)": f"{b['hedge_pnl_eur'] / 1e6:+.2f}",
                "Hedged (EUR m)": f"{b['hedged_revenue_eur'] / 1e6:.2f}"})
    market_rows = [f"- {names[p]}: indicative {r['market_check']['indicative_model']:.1f} EUR/MWh "
                   f"at the model forward {r['market_check']['model_forward']:.1f}; "
                   f"**{r['market_check']['indicative_market']:.1f} EUR/MWh** at the market quote "
                   f"{r['market_check']['quote']:.2f} ({r['market_check']['date']})"
                   for p, r in results.items() if r["market_check"]]
    spreads = []
    for park, r in results.items():
        b = pd.DataFrame(r["backtest"]).T
        merchant = b["merchant_revenue_eur"].max() - b["merchant_revenue_eur"].min()
        hedged = b["hedged_revenue_eur"].max() - b["hedged_revenue_eur"].min()
        spreads.append(f"{names[park].lower()}: merchant revenue moved by EUR "
                       f"{merchant / 1e6:.2f} m between the years, hedged revenue by EUR "
                       f"{hedged / 1e6:.2f} m")
    best = results[lead]["strategies"]["cal_base_min_variance"]
    n_scen = prices.shape[0]
    report = header + f"""Inputs: the Step 7 scenarios for {ppa.start_year} ({n_scen} scenarios,
analog days from {ppa.analog_pool_start}). Selling a product at its forward pays, per MW,
the sum over its hours of (forward − spot). Forwards below are the model's expected prices,
so every hedge is fair in expectation and only changes the spread.

## 1. The forward curve

{curve.to_markdown(index=False)}

### Market check

{_market_md(hg.market_quotes, forwards, ppa.start_year)}

The model is calibrated to the assumed forward of {settings.price_model.forward_eur_mwh:.0f}
EUR/MWh; the published quotes are higher. At the latest market quote, with the same capture
rate, premium and costs (the dashboard's forward knob):

{chr(10).join(market_rows) if market_rows else "Run `ppa-lab pricing` first for the market check."}

## 2. Hedging merchant output

What each park's revenue risk would be if it sold at spot, and with each hedge. Hedge ratio =
MW sold / average output in MW.

{_strategies_md(tables, names)}

For the {names[lead].lower()}, the minimum-variance Cal base hedge sells
{best['hedge_mw']:.1f} MW ({best['hedge_ratio']:.0%} of average output) and cuts the cash flow
at risk by {best['cfar_reduction']:.0%}; quarters and months add little, and
their monthly amounts are noisy (some even negative): with {n_scen} scenarios the
finer split mostly fits noise.

## 3. The PPA buyer's hedge

Step 7 assumed the buyer sells a band equal to the average output. The minimum-variance band
is smaller, because the parks produce more in cheap hours than a flat band:

{buyer_rows}

## 4. Back-test on history

Cal base sold for year Y at year Y-1's average spot price (a naive forward proxy), at the
minimum-variance ratio of the P50 average output; real futures quotes would replace the proxy.

{pd.DataFrame(back_rows).to_markdown(index=False)}

Across the back-test years, {"; ".join(spreads)}. A hedge can lose money in a single year,
and with a naive forward (last year's price) it can even add variation, because the proxy moves
against the realised price. Two years are an illustration, not evidence: the scenario results
in section 2 measure the risk.

## 5. Charts

![Cash flow at risk by hedge](figures/{figs["cfar"].name})

![Monthly hedge vs expected output](figures/{figs["months"].name})

![Revenue with and without the hedge](figures/{figs["distribution"].name})

Results for the memo and the dashboard: `data/processed/{out_json.name}`.
"""
    path.write_text(report)
    log.info("wrote %s and %s", path, out_json)
    return {"report": path, "results": out_json, **figs}
