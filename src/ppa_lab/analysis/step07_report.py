"""Step 7 report: price the parks' pay-as-produced PPAs on the joint scenarios.

Output:
    data/processed/ppa_pricing.json    key results per park (input for Step 9)
    reports/step07_ppa_pricing.md
    reports/figures/step07_*.png
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.plotting import BLUE, GREEN, INK, INK_2, ORANGE, save, style
from ppa_lab.analysis.step05_report import calibration_history
from ppa_lab.analysis.step06_report import complete_weather_years, load_weather_inputs, parks
from ppa_lab.config import PpaParkSettings, Settings
from ppa_lab.prices.model import fit
from ppa_lab.pricing.risk import (
    buyer_value,
    risk_premia,
    structure_revenues,
    structure_table,
    tenor_price,
)
from ppa_lab.scenarios.generator import Scenarios, build_scenarios
from ppa_lab.scenarios.link import fit_link, restrict_pool
from ppa_lab.scenarios.weather import monthly_climatology
from ppa_lab.weather.yields import annual_energy, p_values

log = logging.getLogger(__name__)

STRUCTURES = {
    "merchant": "Merchant (no contract)",
    "pay_as_produced": "Pay-as-produced PPA",
    "pay_as_produced_clause": "Pay-as-produced, nothing paid at negative prices",
    "merchant_floor": "Merchant + floor at 0 EUR/MWh (premium paid)",
    "baseload": "Baseload PPA (band = average output)",
}
GREY = "#a9a9a4"


# --------------------------------------------------------------------------- #
# Calculations
# --------------------------------------------------------------------------- #
def price_park(prices: np.ndarray, volumes: np.ndarray, cost: PpaParkSettings,
               quantile: float) -> dict:
    """Premia, price stack and structures of one park for the delivery year."""
    premia = risk_premia(prices, volumes, quantile)
    forward = float(prices.mean())
    fair = premia["fair_price"]
    stack = {"forward": forward, "shape": fair - forward, "fair_price": fair,
             "risk_premium": premia["joint"], "balancing": cost.balancing_eur_mwh,
             "credit": cost.credit_eur_mwh}
    stack["indicative"] = fair - premia["joint"] - cost.balancing_eur_mwh - cost.credit_eur_mwh
    return {"premia": premia, "stack": stack, "energy_mwh": float(volumes.sum(axis=1).mean()),
            "structures": structure_table(prices, volumes, quantile=quantile)}


def tenor_rows(priced: dict, cost: PpaParkSettings, start: int, years: int, rate: float,
               alternative_fair: float | None = None) -> list[dict]:
    """The tenor price under the base assumptions and the sensitivities."""
    stack = priced["stack"]
    deductions = stack["risk_premium"] + stack["balancing"] + stack["credit"]

    def row(label: str, fair: float, forward: float, drift: float) -> dict:
        t = tenor_price(fair, forward, priced["energy_mwh"], start, years, rate,
                        capture_rate_drift=drift, degradation=cost.degradation)
        return {"case": label, "fair_price": t.attrs["price"],
                "indicative": t.attrs["price"] - deductions}

    f, k, d = stack["forward"], stack["fair_price"], cost.capture_rate_drift
    rows = [row("Base case", k, f, d)]
    for step in (-0.02, -0.01, 0.01):
        rows.append(row(f"Capture rate {step * 100:+.0f} pp per year", k, f, d + step))
    rows.append(row("Forward −10%", 0.9 * k, 0.9 * f, d))
    rows.append(row("Forward +10%", 1.1 * k, 1.1 * f, d))
    if alternative_fair is not None:
        rows.append(row("Analog days from the whole window", alternative_fair, f, d))
    return rows


def scenario_set(settings: Settings, inputs: dict, pool_start: pd.Timestamp) -> Scenarios:
    """The Step 6 scenarios with analog days from `pool_start` on."""
    pm, sc, tz = settings.price_model, settings.scenarios, settings.timezone
    history = calibration_history(settings)
    years = complete_weather_years(inputs["matrices"], settings.weather_first_year,
                                   sc.weather_last_year)
    model = fit(history, tz, pm.scale_eur_mwh)
    features = inputs["features"]
    link = fit_link(model, history, features, monthly_climatology(features, years[0], years[-1]),
                    tz, sc.analog_window_days, sc.analog_k)
    return build_scenarios(model, restrict_pool(link, pool_start), inputs["matrices"], features,
                           tz, pm.delivery_year, years, sc.paths_per_weather_year,
                           pm.forward_eur_mwh, pm.level_volatility, sc.seed)


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_stack(stacks: dict[str, dict], names: dict[str, str], path: Path) -> Path:
    layers = [("Forward\n(model average)", "forward"), ("Shape", "shape"),
              ("Risk\npremium", "risk_premium"), ("Balancing,\nroute to market", "balancing"),
              ("Credit,\nliquidity", "credit"), ("Indicative\nPaP price", "indicative")]
    fig, axes = plt.subplots(1, len(stacks), figsize=(11, 3.8), sharey=True)
    for ax, (park, stack) in zip(np.atleast_1d(axes), stacks.items(), strict=True):
        level = 0.0
        for i, (_, key) in enumerate(layers):
            if key in ("forward", "indicative"):
                value = stack[key]
                ax.bar(i, value, color=BLUE, width=0.62)
                level = value
                text = f"{value:.1f}"
                top = value
            else:
                delta = stack[key] if key == "shape" else -stack[key]
                ax.bar(i, delta, bottom=level, color=ORANGE if delta < 0 else GREEN, width=0.62)
                top = max(level, level + delta)
                level += delta
                text = f"{delta:+.1f}"
            ax.text(i, top + 1.5, text, ha="center", fontsize=8.5, color=INK, fontweight="bold")
        ax.set_xticks(range(len(layers)), [label for label, _ in layers], fontsize=7.5)
        ax.set_ylim(0, 1.18 * stack["forward"])               # room for the labels
        style(ax, f"{names[park]}: from forward to offer", "EUR/MWh")
    return save(fig, path)


def fig_revenue(revenues: dict[str, tuple], label: str, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 3.6))
    data = [cash / 1e6 for _, cash in revenues.values()]
    box = ax.boxplot(data, orientation="horizontal", whis=(5, 95), showfliers=False,
                     patch_artist=True, widths=0.55, medianprops={"color": INK})
    for patch in box["boxes"]:
        patch.set_facecolor("#cfe0f5")
        patch.set_edgecolor(BLUE)
    ax.set_yticks(range(1, len(data) + 1), [STRUCTURES[k] for k in revenues], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Annual revenue of the producer (EUR m); box 25-75%, whiskers 5-95%",
                  color=INK_2, fontsize=9)
    ax.grid(axis="x", color="#e2e2de", linewidth=0.8)
    style(ax, f"{label}: what each structure leaves with the producer (fair strikes)", "")
    return save(fig, path)


def fig_buyer(prices: np.ndarray, volumes: np.ndarray, label: str, quantile: float,
              path: Path) -> Path:
    energy = volumes.sum(axis=1)
    k = float((prices * volumes).sum() / volumes.sum())
    forward, band = float(prices.mean()), float(energy.mean()) / prices.shape[1]
    unhedged = buyer_value(prices, volumes, k) / energy.mean()
    hedged = buyer_value(prices, volumes, k, forward, band) / energy.mean()
    fig, ax = plt.subplots(figsize=(10, 3.4))
    bins = np.linspace(min(unhedged.min(), hedged.min()), max(unhedged.max(), hedged.max()), 50)
    ax.hist(unhedged, bins=bins, color=GREY, alpha=0.8, label="no hedge")
    ax.hist(hedged, bins=bins, color=BLUE, alpha=0.75, label="baseload hedge sold")
    for values, colour in ((unhedged, INK_2), (hedged, BLUE)):
        ax.axvline(np.quantile(values, quantile), color=colour, linestyle="--", linewidth=1.4)
    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set_xlabel("Value of the PPA to its buyer per expected MWh (EUR/MWh); dashed: 5% quantile",
                  color=INK_2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    style(ax, f"{label}: the buyer's risk, with and without a baseload hedge", "Scenarios")
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
def _m(x: float) -> str:
    return f"{x / 1e6:.2f}"


def _structures_md(priced: dict[str, dict], names: dict[str, str]) -> str:
    rows = []
    for park, result in priced.items():
        for key, r in result["structures"].iterrows():
            rows.append({
                "Park": names[park], "Structure": STRUCTURES[key],
                "Strike (EUR/MWh)": "spot" if np.isnan(r["fair_price_eur_mwh"])
                else f"{r['fair_price_eur_mwh']:.2f}",
                "Expected revenue (EUR m)": _m(r["expected_revenue_eur"]),
                "P5 revenue (EUR m)": _m(r["p05_revenue_eur"]),
                "Cash flow at risk 95% (EUR m)": _m(r["cfar_eur"]),
                "CFaR / expected": f"{r['cfar_share']:.0%}",
            })
    return pd.DataFrame(rows).to_markdown(index=False)


def _premia_md(priced: dict[str, dict], names: dict[str, str]) -> str:
    rows = []
    for park, result in priced.items():
        p = result["premia"]
        rows.append({"Park": names[park], "Fair price": f"{p['fair_price']:.2f}",
                     "Premium, no hedge": f"{p['unhedged']:.2f}",
                     "Premium after baseload hedge": f"{p['joint']:.2f}",
                     "of which profile": f"{p['profile']:.2f}",
                     "of which volume (and its link to price)": f"{p['volume']:.2f}"})
    return pd.DataFrame(rows).to_markdown(index=False)


def _stack_md(priced: dict[str, dict], names: dict[str, str]) -> str:
    rows = []
    labels = [("forward", "Forward (model average baseload price)"),
              ("shape", "Shape: capture rate below 1"),
              ("fair_price", "= Fair pay-as-produced price"),
              ("risk_premium", "− Profile and volume risk premium"),
              ("balancing", "− Balancing and route to market"),
              ("credit", "− Credit and liquidity"),
              ("indicative", "= Indicative pay-as-produced price")]
    for key, label in labels:
        row = {"Layer (EUR/MWh)": label}
        for park, result in priced.items():
            v = result["stack"][key]
            row[names[park]] = f"{v:+.2f}" if key == "shape" else f"{v:.2f}"
        rows.append(row)
    return pd.DataFrame(rows).to_markdown(index=False)


def _tenor_md(tenors: dict[str, list[dict]], names: dict[str, str]) -> str:
    cases = [r["case"] for r in next(iter(tenors.values()))]
    rows = []
    for i, case in enumerate(cases):
        row = {"Case": case}
        for park, rs in tenors.items():
            row[f"{names[park]}: fair"] = f"{rs[i]['fair_price']:.2f}"
            row[f"{names[park]}: indicative"] = f"{rs[i]['indicative']:.2f}"
        rows.append(row)
    return pd.DataFrame(rows).to_markdown(index=False)


def _strict(obj):
    """JSON-safe copy: NaN becomes null, NumPy numbers become Python floats."""
    if isinstance(obj, dict):
        return {k: _strict(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [_strict(v) for v in obj]
    if isinstance(obj, int | float | np.floating | np.integer) and not isinstance(obj, bool):
        value = float(obj) if not isinstance(obj, int | np.integer) else int(obj)
        return None if isinstance(value, float) and np.isnan(value) else value
    return obj


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def write_step07_report(settings: Settings) -> dict[str, Path | None]:
    ppa, pm, tz = settings.ppa, settings.price_model, settings.timezone
    path = settings.reports_dir / "step07_ppa_pricing.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Step 7 report: pricing the PPAs and their risk\n\n"
              f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab pricing`.\n\n")
    inputs = load_weather_inputs(settings)
    if inputs is None:
        path.write_text(header + "No site weather or generation found: run `ppa-lab weather` "
                        "first (Step 4).\n")
        return {"report": path, "results": None, "stack": None, "revenue": None, "buyer": None}

    solar, wind = parks(settings)
    names = {p.name: ("Solar park" if p is solar else "Wind park") for p in (solar, wind)
             if p.name in ppa.parks}
    q = ppa.risk_quantile
    base = scenario_set(settings, inputs, pd.Timestamp(ppa.analog_pool_start))
    whole = None
    if pd.Timestamp(ppa.analog_pool_start) > pd.Timestamp(pm.calibration_start):
        whole = scenario_set(settings, inputs, pd.Timestamp(pm.calibration_start))

    priced, tenors, results = {}, {}, {}
    end_year = ppa.start_year + ppa.tenor_years - 1
    for park in names:
        cost = ppa.parks[park]
        priced[park] = price_park(base.prices, base.volume(park), cost, q)
        alt, whole_window = None, None
        if whole is not None:
            whole_premia = risk_premia(whole.prices, whole.volume(park), q)
            alt = whole_premia["fair_price"]
            whole_window = {"fair_price": alt, "premium": whole_premia["joint"]}
        tenors[park] = tenor_rows(priced[park], cost, ppa.start_year, ppa.tenor_years,
                                  ppa.discount_rate, alt)
        annual = annual_energy(inputs["gen"][park], tz).loc[
            settings.weather_first_year:settings.scenarios.weather_last_year]
        pv = p_values(annual)
        results[park] = {
            "premia_eur_mwh": priced[park]["premia"],
            "stack_eur_mwh": priced[park]["stack"],
            "structures": priced[park]["structures"].to_dict(orient="index"),
            "energy_mwh_expected": priced[park]["energy_mwh"],
            "p50_mwh": pv["p50"], "p90_1y_mwh": pv["p90_1y"],
            "whole_window": whole_window,
            "assumptions": {"balancing_eur_mwh": cost.balancing_eur_mwh,
                            "credit_eur_mwh": cost.credit_eur_mwh,
                            "capture_rate_drift": cost.capture_rate_drift,
                            "degradation": cost.degradation},
            "tenor": {"years": list(range(ppa.start_year, end_year + 1)),
                      "fair_price": tenors[park][0]["fair_price"],
                      "indicative": tenors[park][0]["indicative"],
                      "sensitivity": tenors[park]},
        }

    out_json = settings.processed_dir / "ppa_pricing.json"
    out_json.write_text(json.dumps(_strict({
        "generated_utc": f"{datetime.now(UTC):%Y-%m-%d %H:%M}", "delivery_year": ppa.start_year,
        "tenor_years": ppa.tenor_years, "discount_rate": ppa.discount_rate,
        "analog_pool_start": str(ppa.analog_pool_start),
        "scenarios": int(base.prices.shape[0]), "forward_assumption": pm.forward_eur_mwh,
        "parks": results}), indent=1, allow_nan=False))

    fig_dir = settings.reports_dir / "figures"
    lead = next(iter(names))
    figs = {
        "stack": fig_stack({p: r["stack"] for p, r in priced.items()}, names,
                           fig_dir / "step07_price_stack.png"),
        "revenue": fig_revenue(structure_revenues(base.prices, base.volume(lead)), names[lead],
                               fig_dir / "step07_revenue.png"),
        "buyer": fig_buyer(base.prices, base.volume(lead), names[lead], q,
                           fig_dir / "step07_buyer_risk.png"),
    }

    lead_r = results[lead]
    s, t = lead_r["stack_eur_mwh"], lead_r["tenor"]
    merchant_cfar = priced[lead]["structures"].loc["merchant", "cfar_eur"]
    pap_cfar = priced[lead]["structures"].loc["pay_as_produced", "cfar_eur"]
    span = f"{ppa.start_year}-{end_year}"
    answer = (
        f"For a {ppa.tenor_years}-year pay-as-produced PPA ({span}) from the "
        f"{names[lead].lower()}, "
        f"the fair price before risk premia is **{t['fair_price']:.1f} EUR/MWh** (first year: "
        f"forward {s['forward']:.1f} × expected capture rate {s['fair_price'] / s['forward']:.2f} "
        f"= {s['fair_price']:.1f}). After a profile and volume risk premium of "
        f"{s['risk_premium']:.1f} EUR/MWh and balancing and credit costs of "
        f"{s['balancing'] + s['credit']:.1f} EUR/MWh, the indicative price is "
        f"**{t['indicative']:.1f} EUR/MWh**. Expected annual energy is "
        f"{lead_r['p50_mwh'] / 1e3:.1f} GWh (P50; one-year P90 {lead_r['p90_1y_mwh'] / 1e3:.1f} "
        f"GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR "
        f"{merchant_cfar / 1e6:.2f} m (merchant) to EUR {pap_cfar / 1e6:.2f} m per year: only "
        f"volume risk is left.")

    report = header + f"""Inputs: the Step 6 joint scenarios for {ppa.start_year}
({base.prices.shape[0]} scenarios: {len(set(base.weather_years))} weather years x
{settings.scenarios.paths_per_weather_year} price paths), with intraday patterns from analog days
from **{ppa.analog_pool_start}** on (the most recent regime; the whole window is a sensitivity).
Forward assumption {pm.forward_eur_mwh:.1f} EUR/MWh; the scenarios average
{base.prices.mean():.2f} EUR/MWh. Risk measures at the {q:.0%} quantile.

## 1. What each structure leaves with the producer ({ppa.start_year})

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

{_structures_md(priced, names)}

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

{_premia_md(priced, names)}

## 3. Price stack {ppa.start_year}: from the forward to an indicative price

{_stack_md(priced, names)}

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. {ppa.tenor_years}-year price ({span})

Discounted at {ppa.discount_rate:.0%} (mid-year), energy-weighted; flat forward and capture rate
unless stated; solar output degrades {ppa.parks[lead].degradation:.1%} per year. The risk premium
and costs per MWh of the first year are applied to every year (a simplification).

{_tenor_md(tenors, names)}

## 5. The answer

{answer}

## 6. Charts

![Price stack](figures/{figs["stack"].name})

![Revenue by structure](figures/{figs["revenue"].name})

![The buyer's risk](figures/{figs["buyer"].name})

Results for Step 9: `data/processed/{out_json.name}`.
"""
    path.write_text(report)
    log.info("wrote %s and %s", path, out_json)
    return {"report": path, "results": out_json, **figs}
