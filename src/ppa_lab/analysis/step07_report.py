"""Step 7 report: price the parks' pay-as-produced PPAs on the joint scenarios.

Output:
    data/processed/ppa_pricing.json    key results per park (input for Step 9)
    reports/step07_ppa_pricing.md
    reports/figures/step07_*.png
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.level_effect import level_regression, monthly_panel, share_pace
from ppa_lab.analysis.plotting import BLUE, GREEN, INK, INK_2, ORANGE, save, style
from ppa_lab.analysis.step02_report import MARKET_VALUES_FILE
from ppa_lab.analysis.step05_report import calibration_history, hourly_prices
from ppa_lab.analysis.step06_report import complete_weather_years, load_weather_inputs, parks
from ppa_lab.config import PpaParkSettings, Settings
from ppa_lab.prices.model import fit
from ppa_lab.pricing.eeg import basis_ratio, market_premium, month_codes, official_market_values
from ppa_lab.pricing.forwards import describe_forward, quarter_forwards
from ppa_lab.pricing.risk import (
    buyer_value,
    capture_rate_at,
    cash_flow_at_risk,
    curtail,
    curtailment_value,
    daily_profile,
    level_shift,
    risk_premia,
    structure_revenues,
    structure_table,
    tenor_price,
)
from ppa_lab.scenarios.buildout import calibrate, capture_rate_factors, share_growth
from ppa_lab.scenarios.generator import Scenarios, build_scenarios
from ppa_lab.scenarios.link import fit_link, restrict_pool
from ppa_lab.scenarios.weather import monthly_climatology
from ppa_lab.timeutils import to_hourly
from ppa_lab.weather.yields import annual_energy, p_values

log = logging.getLogger(__name__)

STRUCTURES = {
    "merchant": "Merchant (no contract), curtailing at negative prices",
    "merchant_no_curtailment": "Merchant, producing at negative prices",
    "pay_as_produced": "Pay-as-produced PPA",
    "pay_as_produced_clause": "Pay-as-produced, negative-price clause (curtailed, unpaid)",
    "pay_as_produced_deemed": "Pay-as-produced, buyer curtails and pays the output",
    "baseload": "Baseload PPA (band = average output)",
}
GREY = "#a9a9a4"


# --------------------------------------------------------------------------- #
# Calculations
# --------------------------------------------------------------------------- #
def price_park(prices: np.ndarray, volumes: np.ndarray, cost: PpaParkSettings,
               quantile: float, curtail_below: float | None = None,
               structures: bool = True) -> dict:
    """Premia, price stack and structures of one park for the delivery year. `volumes` are
    the MWh the contract pays for (for the negative-price clause: the curtailed output)."""
    premia = risk_premia(prices, volumes, quantile)
    forward = float(prices.mean())
    fair = premia["fair_price"]
    stack = {"forward": forward, "shape": fair - forward, "fair_price": fair,
             "risk_premium": premia["joint"], "balancing": cost.balancing_eur_mwh,
             "credit": cost.credit_eur_mwh}
    stack["indicative"] = fair - premia["joint"] - cost.balancing_eur_mwh - cost.credit_eur_mwh
    out = {"premia": premia, "stack": stack, "energy_mwh": float(volumes.sum(axis=1).mean())}
    if structures:
        out["structures"] = structure_table(prices, volumes, curtail_below, quantile)
    return out


def tenor_rows(priced: dict, cost: PpaParkSettings, start: int, years: int, rate: float,
               alternative_fair: float | None = None,
               curve: dict[int, float] | None = None,
               response: dict | None = None,
               history: dict[str, dict] | None = None,
               capture_error: float | None = None,
               factors: dict[int, float] | None = None,
               buildout: dict[str, dict[int, float]] | None = None) -> list[dict]:
    """The tenor price under the base assumptions and the sensitivities.

    `curve` gives the forwards of later contract years (see `tenor_price`); the forward
    sensitivities shift the whole curve. `response` is the capture rate by price level (see
    `level_shift`): the capture rate moves with each year's forward and with the forward
    sensitivities. `history` maps a case name to another response, used for the first year too.
    `capture_error`: the model's out-of-sample capture-rate error (Step 6), taken off every year.
    `factors`: the base build-out scenario's capture-rate factor per year (all rows);
    `buildout`: other scenarios, case name -> factors.
    """
    stack = priced["stack"]
    deductions = stack["risk_premium"] + stack["balancing"] + stack["credit"]
    curve = curve or {}

    def row(label: str, fair: float, forward: float, drift: float, scale: float = 1.0,
            levels: dict | None = response, path: dict[int, float] | None = factors) -> dict:
        t = tenor_price(fair, forward, priced["energy_mwh"], start, years, rate,
                        capture_rate_drift=drift, degradation=cost.degradation,
                        forward_curve={y: scale * f_y for y, f_y in curve.items()},
                        level_response=levels, capture_rate_factors=path)
        return {"case": label, "fair_price": t.attrs["price"],
                "indicative": t.attrs["price"] - deductions}

    f, k, d = stack["forward"], stack["fair_price"], cost.capture_rate_drift
    rows = [row("Base case", k, f, d)]
    for step in (-0.02, -0.01, 0.01):
        rows.append(row(trend_case(step), k, f, d + step))
    for scale, label in ((0.9, "Forward −10%"), (1.1, "Forward +10%")):
        moved = scale * f * (k / f + level_shift(response, f, scale * f))
        rows.append(row(label, moved, scale * f, d, scale))
    if alternative_fair is not None:
        rows.append(row("Analog days from the whole window", alternative_fair, f, d))
    for label, levels in (history or {}).items():
        rows.append(row(label, f * capture_rate_at(levels, f), f, d, levels=levels))
    if capture_error is not None:
        rows.append(row(OUT_OF_SAMPLE, f * (k / f - capture_error), f, d))
    for label, path in (buildout or {}).items():
        rows.append(row(label, k, f, d, path=path))
    return rows


OUT_OF_SAMPLE = "Capture rate less the model's out-of-sample error"
LEVEL_LOW = "Capture rate vs price level: low end of history"
LEVEL_HIGH = "Capture rate vs price level: high end of history"
TECH_COLUMNS = {"solar": "solar_mw", "wind": "wind_onshore_mw"}


def price_clause(base: Scenarios, whole: Scenarios | None, park: str, cost: PpaParkSettings,
                 quantile: float, below: float, grid: list[dict], ppa, plain: dict,
                 prices: pd.Series, generation: pd.Series, tz: str,
                 factors: dict[int, float] | None = None) -> dict:
    """The negative-price clause for one park (v1.8): the park curtails below `below` and is
    paid only for what it delivers, at that output's own fair price. Stack, premium, tenor
    price (along the curtailed output's capture rate and delivered share by price level), the
    value of curtailing in 2027 and in history, and the deemed-volume strike."""
    potential = base.volume(park)
    sold = curtail(base.prices, potential, below)
    clause = price_park(base.prices, sold, cost, quantile, structures=False)
    response = park_response(grid, park, "clause_capture_rate")
    volumes = volume_response(grid, park)
    s = clause["stack"]
    years = tenor_price(s["fair_price"], s["forward"], clause["energy_mwh"], ppa.start_year,
                        ppa.tenor_years, ppa.discount_rate,
                        capture_rate_drift=cost.capture_rate_drift, degradation=cost.degradation,
                        forward_curve=ppa.forward_curve, level_response=response,
                        volume_response=volumes, capture_rate_factors=factors)
    weights = years["discount_factor"]
    full = plain["energy_mwh"] * (1.0 - cost.degradation) ** np.arange(len(years))
    delivered = float((weights * years["energy_mwh"]).sum() / (weights * full).sum())
    fair = years.attrs["price"]
    indicative = fair - s["risk_premium"] - s["balancing"] - s["credit"]
    whole_window = None
    if whole is not None:
        w = risk_premia(whole.prices, curtail(whole.prices, whole.volume(park), below), quantile)
        whole_window = {"fair_price": w["fair_price"], "premium": w["joint"]}
    structures = plain["structures"]
    return {
        "curtail_below_eur_mwh": below,
        "curtailment": curtailment_value(base.prices, potential, below),
        "history": curtailment_history(prices, generation, tz, below).to_dict(orient="index"),
        "deemed_strike": float(structures.loc["pay_as_produced_deemed", "fair_price_eur_mwh"]),
        "cfar_plain_eur": float(structures.loc["pay_as_produced", "cfar_eur"]),
        "cfar_clause_eur": float(structures.loc["pay_as_produced_clause", "cfar_eur"]),
        "clause": {"stack_eur_mwh": s, "premia_eur_mwh": clause["premia"],
                   "energy_mwh_expected": clause["energy_mwh"],
                   "delivered_share": clause["energy_mwh"] / plain["energy_mwh"],
                   "level_response": response, "volume_response": volumes,
                   "whole_window": whole_window,
                   "tenor": {"fair_price": fair, "indicative": indicative,
                             "delivered_share": delivered,
                             "indicative_per_potential_mwh": indicative * delivered}},
    }


def buildout_paths(settings: Settings, start: int, years: int) -> dict | None:
    """The build-out scenarios (PPA-8f): calibration on history and, per scenario, the share
    growth and the capture-rate factor of each contract year. None without [buildout] or data."""
    bo = settings.buildout
    path = settings.processed_dir / "power_15min.parquet"
    if bo is None or not path.exists():
        return None
    power = to_hourly(pd.read_parquet(path))
    panel = monthly_panel(hourly_prices(settings), power, settings.timezone, {"solar": "solar_mw"})
    reg = None
    if (panel["capture_rate_solar"] > 0).all():        # the log form needs positive rates
        reg = level_regression(panel, "solar", bo.regression_start_year, log=True)
    cal = None
    if reg is not None:
        with contextlib.suppress(KeyError):            # history years outside the data
            cal = calibrate(power, settings.timezone, bo.history_first_year,
                            bo.history_last_year, list(bo.history_pv_additions_gw),
                            bo.storage_cycles_per_year, bo.storage_solar_fraction,
                            reg["share_coef"], reg["share_se"])
    if cal is None:
        log.warning("no build-out scenarios: the data cannot calibrate [buildout]; solar's "
                    "capture rate follows capture_rate_drift alone")
        return None
    scenarios = {}
    for name, sc in bo.scenarios.items():
        growth = share_growth(cal, sc.pv_additions_gw, sc.storage_additions_gwh,
                              bo.history_storage_additions_gwh)
        scenarios[name] = {"label": sc.label, "pv_additions_gw": sc.pv_additions_gw,
                           "storage_additions_gwh": sc.storage_additions_gwh,
                           "share_growth": growth,
                           "factor_per_year": float(np.exp(cal.gamma * cal.amplification
                                                           * growth)),
                           "factors": capture_rate_factors(cal, growth, start, years)}
    return {"base": bo.base_scenario, "calibration": asdict(cal), "scenarios": scenarios,
            "regression": {k: reg[k] for k in ("share_coef", "share_se", "coef", "r2", "n")},
            "history_years": [bo.history_first_year, bo.history_last_year],
            "history_pv_additions_gw": list(bo.history_pv_additions_gw),
            "history_storage_additions_gwh": bo.history_storage_additions_gwh,
            "storage_cycles_per_year": bo.storage_cycles_per_year,
            "storage_solar_fraction": bo.storage_solar_fraction}


def eeg_comparison(grid: list[dict], park: str, spec: dict, ppa, cost: PpaParkSettings,
                   tenor: list[dict], low: float) -> dict:
    """The EEG against a PPA for one park: the tenor value per MWh of output under the EEG
    (merchant revenue plus market premium, before and after the direct marketer's fee, here
    the balancing cost), for each award and the other reference period; the revenue risk at
    the first forward and at the lowest quoted one; the PPA's tenor prices."""
    def table(key):
        return eeg_tenor(grid, park, ppa.start_year, ppa.tenor_years, ppa.discount_rate,
                         ppa.forward_curve, cost.capture_rate_drift, cost.degradation, key)

    fee = cost.balancing_eur_mwh
    base = table(f"{spec['award']:g}")
    other = "year" if spec["reference"] == "month" else "month"
    alternative = table(f"premium_{other}")
    first = next(r for r in grid if r["base"])
    lowest = min(grid, key=lambda r: abs(r["forward"] - low))
    return {
        "award_eur_mwh": spec["award"], "reference": spec["reference"], "fee_eur_mwh": fee,
        "basis": {k: spec[k] for k in ("basis", "basis_sd", "basis_months", "basis_start")},
        "tenor": {"value": base.attrs["value"], "premium": base.attrs["premium"],
                  "net": base.attrs["value"] - fee,
                  "years": [{"year": int(y), **{k: float(v) for k, v in row.items()}}
                            for y, row in base.iterrows()]},
        "awards": {f"{aw:g}": {"premium": (t := table(f"{aw:g}")).attrs["premium"],
                               "net": t.attrs["value"] - fee} for aw in spec["awards"]},
        f"tenor_{other}": {"premium": alternative.attrs["premium"],
                           "net": alternative.attrs["value"] - fee},
        "risk": {"first": {"forward": first["forward"], **first["eeg"][park]},
                 "lowest": {"forward": lowest["forward"], **lowest["eeg"][park]}},
        "ppa": {"fair": tenor[0]["fair_price"], "indicative": tenor[0]["indicative"]},
    }


def eeg_specs(settings: Settings, names, inputs: dict, prices: pd.Series) -> dict[str, dict]:
    """Per park under the EEG: its award value, the awards of the sensitivity, the reference
    period and the basis ratio of the official market value to the park's capture price."""
    if settings.eeg is None:
        return {}
    out = {}
    for park, cfg in settings.eeg.parks.items():
        if park not in names:
            continue
        official = official_market_values(settings.reference_dir / MARKET_VALUES_FILE,
                                          cfg.market_value_column)
        basis = basis_ratio(official, prices, inputs["gen"][park], settings.timezone,
                            settings.eeg.basis_start)
        out[park] = {"award": cfg.award_eur_mwh, "reference": cfg.reference,
                     "awards": sorted({cfg.award_eur_mwh, *cfg.award_range}),
                     "basis": basis["mean"], "basis_sd": basis["sd"],
                     "basis_months": basis["months"], "basis_start": settings.eeg.basis_start}
    return out


def eeg_metrics(scenarios: Scenarios, park: str, spec: dict, below: float | None, tz: str,
                quantile: float) -> dict:
    """On one scenario set, per MWh of output: merchant revenue (curtailing), the plain PPA's
    fair price and the market premium for each award (monthly, and annual at the configured
    award); and the 95% cash flow at risk and the 5% quantile per MWh of merchant, EEG and PPA
    revenue."""
    p, q = scenarios.prices, scenarios.volume(park)
    months = month_codes(scenarios.index, tz)
    energy = float(q.sum(axis=1).mean())
    merchant = (p * curtail(p, q, below)).sum(axis=1)
    k = float((p * q).sum() / q.sum())
    premia = {f"{aw:g}": market_premium(p, q, months, aw, spec["basis"], spec["reference"], below)
              for aw in spec["awards"]}
    other = "year" if spec["reference"] == "month" else "month"
    alternative = market_premium(p, q, months, spec["award"], spec["basis"], other, below)
    eeg = merchant + premia[f"{spec['award']:g}"]
    ppa = k * q.sum(axis=1)
    revenues = {"merchant": merchant, "eeg": eeg, "ppa": ppa}
    return {"merchant": float(merchant.mean()) / energy, "ppa_fair": k,
            "premium": {aw: float(v.mean()) / energy for aw, v in premia.items()},
            f"premium_{other}": float(alternative.mean()) / energy,
            "cfar": {name: cash_flow_at_risk(v, quantile) for name, v in revenues.items()},
            "p05": {name: float(np.quantile(v, quantile)) / energy
                    for name, v in revenues.items()}}


def eeg_tenor(grid: list[dict], park: str, start: int, years: int, rate: float,
              curve: dict[int, float], drift: float, degradation: float,
              key: str) -> pd.DataFrame:
    """Year by year under the EEG, per MWh of output: forward, merchant revenue (its capture
    rate read at the year's forward, plus the trend), market premium (`key`: an award label of
    the grid's premium, or "premium_year"/"premium_month"), discount factor and energy weight;
    the tenor value in `.attrs["value"]` (discounted and energy-weighted)."""
    level = np.log([r["average"] for r in grid])
    rate_m = [r["eeg"][park]["merchant"] / r["average"] for r in grid]
    prem = [r["eeg"][park]["premium"][key] if key in r["eeg"][park]["premium"]
            else r["eeg"][park][key] for r in grid]
    first = grid_level_at(grid, None)
    rows, f_y = [], first
    for i in range(years):
        y = start + i
        f_y = curve.get(y, f_y)
        x = np.log(f_y)
        merchant = f_y * (float(np.interp(x, level, rate_m)) + drift * i)
        rows.append({"year": y, "forward_eur_mwh": f_y, "merchant_eur_mwh": merchant,
                     "premium_eur_mwh": float(np.interp(x, level, prem)),
                     "discount_factor": (1.0 + rate) ** -(i + 0.5),
                     "energy_weight": (1.0 - degradation) ** i})
    table = pd.DataFrame(rows).set_index("year")
    w = table["discount_factor"] * table["energy_weight"]
    table["eeg_eur_mwh"] = table["merchant_eur_mwh"] + table["premium_eur_mwh"]
    table.attrs["value"] = float((w * table["eeg_eur_mwh"]).sum() / w.sum())
    table.attrs["premium"] = float((w * table["premium_eur_mwh"]).sum() / w.sum())
    return table


def grid_level_at(grid: list[dict], forward: float | None) -> float:
    """The scenarios' average price of the grid row at `forward` (None: the base forward,
    the row whose merchant revenue was computed on the base set)."""
    rows = [r for r in grid if r.get("base")] if forward is None else [
        r for r in grid if r["forward"] == forward]
    return rows[0]["average"]


def tenor_forwards(first: float, curve: dict[int, float], end_year: int,
                   start: int) -> dict[str, float]:
    """The forward of each contract year that has its own quote, labelled by year ("+" when
    it holds for the later years too)."""
    out = {str(start): first}
    for year, price in sorted(curve.items()):
        out[str(year)] = price
    last = max([start, *curve])
    if last < end_year:
        label = str(last)
        out[f"{label}+"] = out.pop(label)
    return out


def trend_case(step: float) -> str:
    """Name of the sensitivity that changes the capture-rate trend by `step` per year."""
    return (f"Capture-rate trend {abs(step) * 100:.0f} pp/yr "
            f"{'steeper' if step < 0 else 'flatter'}")


def recent_level(settings: Settings) -> float:
    """Average day-ahead price of the analog pool (the recent regime), EUR/MWh."""
    history = calibration_history(settings)
    local_day = history.index.tz_convert(settings.timezone).normalize().tz_localize(None)
    return float(history[local_day >= pd.Timestamp(settings.ppa.analog_pool_start)].mean())


def level_grid(settings: Settings, recent: float) -> list[float]:
    """Forwards at which the model's capture rates are measured: the tenor's forwards, the
    recent level and eight levels from 60% of the lowest to 140% of the highest forward, so the
    forward sensitivities and the dashboard's ±30% shift stay inside."""
    quoted = [settings.price_model.forward_eur_mwh, *settings.ppa.forward_curve.values()]
    spread = np.geomspace(0.6 * min(quoted), 1.4 * max(quoted), 8)
    return sorted({round(float(x), 2) for x in (*quoted, recent, *spread)})


def capture_rates(scenarios: Scenarios, names, curtail_below: float | None = None
                  ) -> dict[str, float]:
    """Each park's capture rate on a scenario set: its volume-weighted price over the average
    (of the output left after curtailing below `curtail_below`, if given)."""
    p = scenarios.prices
    average = float(p.mean())
    out = {}
    for park in names:
        q = curtail(p, scenarios.volume(park), curtail_below)
        out[park] = float((p * q).sum() / q.sum()) / average
    return out


def delivered_shares(scenarios: Scenarios, names, curtail_below: float) -> dict[str, float]:
    """Share of each park's output left after curtailing below `curtail_below`."""
    p = scenarios.prices
    return {park: float(curtail(p, scenarios.volume(park), curtail_below).sum()
                        / scenarios.volume(park).sum()) for park in names}


def model_response(settings: Settings, inputs: dict, base: Scenarios, names,
                   levels: list[float], eeg: dict[str, dict] | None = None) -> list[dict]:
    """The price model's capture rate of each park at each forward level (PPA-8d).

    The scenarios are rebuilt at each level with the same random draws (the base set is
    reused at its own forward). Per level: the forward, the scenarios' average price and the
    parks' capture rates; with curtailment (v1.8) also the capture rate of the curtailed
    output and the share of the output delivered; for parks under the EEG (`eeg`, v1.9) the
    market premium and the revenue risk (`eeg_metrics`).
    """
    pm = settings.price_model
    below = settings.ppa.curtail_below_eur_mwh
    pool = pd.Timestamp(settings.ppa.analog_pool_start)
    rows = []
    for level in levels:
        scenarios = base if level == round(pm.forward_eur_mwh, 2) else scenario_set(
            replace(settings, price_model=replace(pm, forward_eur_mwh=level)), inputs, pool)
        row = {"forward": level, "average": float(scenarios.prices.mean()),
               "capture_rate": capture_rates(scenarios, names), "base": scenarios is base}
        if below is not None:
            row["clause_capture_rate"] = capture_rates(scenarios, names, below)
            row["delivered_share"] = delivered_shares(scenarios, names, below)
        if eeg:
            row["eeg"] = {park: eeg_metrics(scenarios, park, spec, below, settings.timezone,
                                            settings.ppa.risk_quantile)
                          for park, spec in eeg.items()}
        rows.append(row)
    return sorted(rows, key=lambda r: r["average"])


def park_response(rows: list[dict], park: str, key: str = "capture_rate") -> dict:
    """One park's capture rate by price level, in the form `level_shift` reads (`key`:
    "capture_rate" or, for the negative-price clause, "clause_capture_rate")."""
    return {"level": [r["average"] for r in rows],
            "capture_rate": [r[key][park] for r in rows]}


def volume_response(rows: list[dict], park: str) -> dict:
    """One park's delivered share of its output by price level (curtailment), as
    `tenor_price` reads it."""
    return {"level": [r["average"] for r in rows],
            "share": [r["delivered_share"][park] for r in rows]}


def curtailment_history(prices: pd.Series, generation: pd.Series, tz: str,
                        below: float) -> pd.DataFrame:
    """Per complete local year: the park's output share at prices below `below`, their
    output-weighted mean price and the avoided loss per MWh of output (EUR/MWh)."""
    q = generation.reindex(prices.index)
    ok = q.notna().to_numpy()
    p, q = prices.to_numpy()[ok], q.to_numpy()[ok]
    year = prices.index[ok].tz_convert(tz).year
    rows = {}
    for y in sorted(set(year)):
        m = np.asarray(year == y)
        if m.sum() < 24 * 200:                     # at least 200 days (2026: to September)
            continue
        rows[int(y)] = curtailment_value(p[m][None, :], q[m][None, :], below)
    return pd.DataFrame(rows).T.rename_axis("year")


def line_response(levels: list[float], ref_level: float, ref_rate: float, slope: float) -> dict:
    """Capture rate ref_rate + slope ln(level / ref_level): history's view, from the recent
    level."""
    return {"level": list(levels),
            "capture_rate": [ref_rate + slope * float(np.log(x / ref_level)) for x in levels]}


def model_slope(response: dict, low: float, high: float) -> float:
    """The model's change of capture rate per unit of ln(level) between two levels (NaN when
    they are the same)."""
    span = float(np.log(high / low))
    return level_shift(response, low, high) / span if abs(span) > 1e-3 else float("nan")


def level_regressions(settings: Settings) -> dict | None:
    """The PPA-8d regression for solar and wind on monthly history: from the configured start
    year and on all years. None without power data."""
    path = settings.processed_dir / "power_15min.parquet"
    if not path.exists():
        return None
    power = to_hourly(pd.read_parquet(path))
    panel = monthly_panel(hourly_prices(settings), power, settings.timezone, TECH_COLUMNS)
    start = settings.ppa.level_effect_start_year
    years = [int(panel.index.year.min()), int(panel.index.year.max())]
    out = {"start_year": start or years[0], "first_year": years[0], "last_year": years[1]}
    for tech, column in TECH_COLUMNS.items():
        out[tech] = level_regression(panel, tech, start)
        out[f"{tech}_all_years"] = level_regression(panel, tech)
        out[f"{tech}_share_pace"] = share_pace(power, settings.timezone, column, out["start_year"])
    return out


def scenario_set(settings: Settings, inputs: dict, pool_start: pd.Timestamp) -> Scenarios:
    """The Step 6 scenarios with analog days from `pool_start` on."""
    pm, sc, tz = settings.price_model, settings.scenarios, settings.timezone
    history = calibration_history(settings)
    years = complete_weather_years(inputs["matrices"], settings.weather_first_year,
                                   sc.weather_last_year)
    model = fit(history, tz, pm.scale_eur_mwh, pm.negative_scale_eur_mwh, pm.intraday_trend)
    features = inputs["features"]
    link = fit_link(model, history, features, monthly_climatology(features, years[0], years[-1]),
                    tz, sc.analog_window_days, sc.analog_k)
    return build_scenarios(model, restrict_pool(link, pool_start), inputs["matrices"], features,
                           tz, pm.delivery_year, years, sc.paths_per_weather_year,
                           pm.forward_eur_mwh, pm.level_volatility, sc.seed,
                           quarter_forwards=quarter_forwards(pm.forward_eur_mwh, pm.quarter_quotes,
                                                             pm.delivery_year, tz))


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


def fig_level(rows: list[dict], effects: dict[str, dict], names: dict[str, str],
              tenor_forwards: dict[str, float], path: Path) -> Path:
    """Per park: the model's capture rate by price level against history's 95% band."""
    fig, axes = plt.subplots(1, len(names), figsize=(11, 3.8))
    x = np.array([r["average"] for r in rows])
    for ax, park in zip(np.atleast_1d(axes), names, strict=True):
        e = effects[park]
        ax.plot(x, [r["capture_rate"][park] for r in rows], color=BLUE, marker="o",
                markersize=3.5, linewidth=1.8, label="price model (scenarios at each level)")
        reg = e.get("history")
        if reg is not None:
            ln = np.log(x / e["ref_level"])
            ax.fill_between(x, e["ref_rate"] + reg["ci_low"] * ln,
                            e["ref_rate"] + reg["ci_high"] * ln, color=ORANGE, alpha=0.18,
                            linewidth=0, label=f"history {e['history_years']}: 95% band")
            ax.plot(x, e["ref_rate"] + reg["coef"] * ln, color=ORANGE, linestyle="--",
                    linewidth=1.2, label=f"history: slope {reg['coef']:.2f}")
        ax.plot([e["ref_level"]], [e["ref_rate"]], "o", color=INK, markersize=5,
                label=f"recent level ({e['ref_level']:.0f})")
        for label, level in tenor_forwards.items():
            ax.axvline(level, color=GREY, linestyle=":", linewidth=1.0)
            ax.text(level, 1.0, f" {label}", transform=ax.get_xaxis_transform(), fontsize=7.5,
                    color=INK_2, va="top", rotation=90)
        ax.set_xlabel("Average price of the year (EUR/MWh)", color=INK_2, fontsize=9)
        ax.legend(frameon=False, fontsize=7.5, loc="lower right")
        style(ax, f"{names[park]}: capture rate vs price level", "Capture rate")
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
                "Output sold or paid": f"{r['energy_share']:.0%}",
                "Expected revenue (EUR m)": _m(r["expected_revenue_eur"]),
                "P5 revenue (EUR m)": _m(r["p05_revenue_eur"]),
                "Cash flow at risk 95% (EUR m)": _m(r["cfar_eur"]),
                "CFaR / expected": f"{r['cfar_share']:.0%}",
            })
    return pd.DataFrame(rows).to_markdown(index=False)


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _negative_md(negative: dict[str, dict], priced: dict[str, dict], tenors: dict[str, list],
                 names: dict[str, str], start: int, years: int) -> str:
    """The negative-price table: what curtailing is worth, and the three ways to share it."""
    def row(label, cell):
        return f"| {label} | " + " | ".join(cell(p) for p in negative) + " |"

    n, s = negative, {p: priced[p]["stack"] for p in negative}
    c = {p: n[p]["clause"] for p in negative}
    lines = ["| EUR/MWh | " + " | ".join(names[p] for p in negative) + " |",
             "|---|" + "---|" * len(negative),
             row(f"Output at negative prices, {start}",
                 lambda p: _pct(n[p]["curtailment"]["share"])),
             row("Their output-weighted mean price",
                 lambda p: _n(n[p]["curtailment"]["mean_price"])),
             row("Saved by curtailing, per MWh of output",
                 lambda p: f"{n[p]['curtailment']['value']:.2f}"),
             row(f"Plain PPA: fair price {start}; {years}-year indicative",
                 lambda p: f"{s[p]['fair_price']:.2f}; {tenors[p][0]['indicative']:.2f}"),
             row(f"Clause: fair price {start} per delivered MWh",
                 lambda p: f"{c[p]['stack_eur_mwh']['fair_price']:.2f}"),
             row("Clause: buyer's premium after a baseload hedge",
                 lambda p: f"{c[p]['stack_eur_mwh']['risk_premium']:.2f} (plain "
                           f"{s[p]['risk_premium']:.2f})"),
             row(f"Clause: {years}-year fair; indicative, per delivered MWh",
                 lambda p: f"{c[p]['tenor']['fair_price']:.2f}; {c[p]['tenor']['indicative']:.2f}"),
             row(f"Clause: {years}-year indicative per MWh of output (delivered "
                 "share)", lambda p: f"{c[p]['tenor']['indicative_per_potential_mwh']:.2f} "
                                     f"({_pct(c[p]['tenor']['delivered_share'])})"),
             row(f"Deemed output: fair price {start}", lambda p: f"{n[p]['deemed_strike']:.2f}"),
             row(f"Producer's CFaR95 {start}: plain; clause (EUR m)",
                 lambda p: f"{_m(n[p]['cfar_plain_eur'])}; {_m(n[p]['cfar_clause_eur'])}")]
    return "\n".join(lines)


def _curtailment_history_md(negative: dict[str, dict], names: dict[str, str]) -> str:
    years = sorted({int(y) for v in negative.values() for y in v["history"]})
    lines = ["| Year | " + " | ".join(f"{names[p]}: output at negative prices; saved per MWh"
                                     for p in negative) + " |",
             "|---|" + "---|" * len(negative)]
    for y in years:
        cells = []
        for p in negative:
            h = negative[p]["history"].get(y) or negative[p]["history"].get(str(y))
            cells.append("–" if h is None else f"{_pct(h['share'])}; {h['value']:.2f}")
        lines.append(f"| {y} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _eeg_md(e: dict, label: str, start: int, years: int) -> str:
    """Section text: one park's EEG market premium against a PPA."""
    tenor, risk, aw = e["tenor"], e["risk"], e["award_eur_mwh"]
    other = "year" if e["reference"] == "month" else "month"
    by_year = tenor["years"]
    rows = [r for r in by_year if r["year"] <= start + 1] + [by_year[-1]]
    year_lines = ["| Year | Forward | Merchant | Market premium | Under the EEG |",
                  "|---|---|---|---|---|"]
    for r in rows:
        name = f"{r['year']}" if r["year"] <= start + 1 else f"{start + 2}-{start + years - 1}"
        year_lines.append(f"| {name} | {r['forward_eur_mwh']:.1f} | {r['merchant_eur_mwh']:.1f} "
                          f"| {r['premium_eur_mwh']:.2f} | {r['eeg_eur_mwh']:.1f} |")
    risk_lines = ["| Price level | CFaR95, EUR m: merchant / EEG / PPA | 5% quantile, EUR/MWh: "
                  "merchant / EEG / PPA |", "|---|---|---|"]
    for key, name in (("first", f"{start} forward"), ("lowest", "lowest quoted forward")):
        r = risk[key]
        risk_lines.append(
            f"| {name} ({r['forward']:.0f}) | {_m(r['cfar']['merchant'])} / {_m(r['cfar']['eeg'])}"
            f" / {_m(r['cfar']['ppa'])} | {r['p05']['merchant']:.1f} / {r['p05']['eeg']:.1f} / "
            f"{r['p05']['ppa']:.1f} |")
    award_lines = ["| Award value AW (EUR/MWh) | Market premium, ten years | Under the EEG, after "
                   "the fee |", "|---|---|---|"]
    for key, v in sorted(e["awards"].items(), key=lambda kv: float(kv[0])):
        mark = " (assumed)" if float(key) == aw else ""
        award_lines.append(f"| {key}{mark} | {v['premium']:.2f} | {v['net']:.1f} |")
    alt = e[f"tenor_{other}"]
    award_lines.append(f"| {aw:g}, {other}ly market value | {alt['premium']:.2f} | "
                       f"{alt['net']:.1f} |")
    gap = tenor["net"] - e["ppa"]["indicative"]
    b = e["basis"]
    low = risk["lowest"]["p05"]
    floor_text = "" if low["eeg"] <= low["ppa"] else (
        f"; but at the lowest forward the EEG's bad year is better than the PPA's ("
        f"{low['eeg']:.1f} against {low['ppa']:.1f} EUR/MWh): the put floors the price and the "
        "EEG keeps the upside")
    worst = min(e["awards"].items(), key=lambda kv: kv[1]["net"])
    margin = worst[1]["net"] - e["ppa"]["indicative"]
    if margin > 0:
        verdict = (
            f"For every award value in the range the EEG pays more than a PPA at the indicative "
            f"price (by {margin:.1f} EUR/MWh even at AW {worst[0]}). Leaving the EEG for a PPA "
            f"pays only at a price of at least about {tenor['net']:.0f} EUR/MWh, less what the "
            "producer would pay to be rid of the remaining risk, plus the guarantees of origin "
            "it could then sell. The PPA price of section 4 is a what-if for this park.")
    else:
        awards = sorted((float(k), v["net"]) for k, v in e["awards"].items())
        level = float(np.interp(e["ppa"]["indicative"], [n for _, n in awards],
                                [a for a, _ in awards]))
        verdict = (
            f"Below an award value of about {level:.0f} EUR/MWh a PPA at the indicative price "
            "pays more than the EEG; above it, the EEG does.")
    return (
        f"The {label.lower()} is paid under the EEG market premium model: it sells at spot and "
        f"the grid operator adds max(AW − MW, 0) per MWh, MW the {e['reference']}'s official "
        "onshore wind market value. That is a strip of puts on the market value, struck at the "
        f"award value AW, here **{aw:g} EUR/MWh (an assumption: the award is not published; "
        "see `[eeg]`)**. To sign a PPA the park would leave the premium (a PPA buyer wants the "
        "guarantees of origin, which the EEG does not issue), so the PPA must be worth more "
        "than the EEG. MW in a scenario: the park's own capture price that month times "
        f"{b['basis']:.3f}, the ratio of the official value to the park's capture price in "
        f"{b['basis_months']} months from {b['basis_start']} (sd {b['basis_sd']:.3f}). No "
        "premium at negative prices (§51 EEG; the park curtails).\n\n"
        "Per MWh of output (EUR/MWh):\n\n" + "\n".join(year_lines) + "\n\n"
        f"Over {years} years (discounted, energy-weighted) the EEG pays {tenor['value']:.1f} "
        f"EUR/MWh, of which {tenor['premium']:.2f} premium; after the direct marketer's fee "
        f"({e['fee_eur_mwh']:.1f}) **{tenor['net']:.1f}**. A PPA pays {e['ppa']['fair']:.1f} at "
        f"its fair price and **{e['ppa']['indicative']:.1f}** at the indicative price: "
        f"{abs(gap):.1f} EUR/MWh {'less' if gap > 0 else 'more'} than staying in the EEG. "
        "The put is worth little at the 2027 forward but much at the lower forwards of later "
        "years.\n\nRisk in one delivery year, at two price levels:\n\n"
        + "\n".join(risk_lines) + "\n\nThe put cuts the merchant's risk most where prices "
        "are low, and a PPA removes more of it" + floor_text + ". By award value:\n\n"
        + "\n".join(award_lines) + "\n\n" + verdict)


def _buildout_md(bo: dict | None, tenors: dict[str, list], priced: dict[str, dict],
                 names: dict[str, str], results: dict[str, dict], start: int, years: int) -> str:
    """Section text: the build-out scenarios and what they do to the solar price."""
    parks = [p for p, r in results.items() if r.get("buildout")]
    if bo is None or not parks:
        return "No build-out scenarios (`[buildout]`; `buildout = true` for a park)."
    cal, reg = bo["calibration"], bo["regression"]
    first, last = bo["history_years"]
    end = start + years - 1
    mid = min(start + 3, end)
    lines = ["| Scenario | Solar (GW/yr) | Storage (GWh/yr) | Solar share of load (pp/yr) | "
             f"Capture-rate factor {mid} / {end} | "
             + " | ".join(f"{names[p]}: {years}-year fair; indicative" for p in parks) + " |",
             "|---|---|---|---|---|" + "---|" * len(parks)]
    for name, sc in bo["scenarios"].items():
        mark = " (base case)" if name == bo["base"] else ""
        cells = []
        for p in parks:
            case = "Base case" if name == bo["base"] else f"Build-out: {sc['label']}"
            r = next(x for x in tenors[p] if x["case"] == case)
            cells.append(f"{r['fair_price']:.2f}; {r['indicative']:.2f}")
        f = sc["factors"]
        lines.append(f"| {sc['label'].split(':')[0]}{mark} | {sc['pv_additions_gw']:g} | "
                     f"{sc['storage_additions_gwh']:g} | {sc['share_growth'] * 100:+.2f} | "
                     f"{f[mid]:.2f} / {f[end]:.2f} | " + " | ".join(cells)
                     + " |")
    fixed = "; ".join(f"{results[p]['buildout']['tenor_with_fixed_trend']:.2f} EUR/MWh "
                      f"({names[p].lower()})" for p in parks)
    base = bo["scenarios"][bo["base"]]["factors"]
    fall = 1.0 - base[start + 1] / base[start]
    return (
        f"Until v1.10 solar's capture rate fell 1 percentage point a year after {start}, an "
        "assumption. Now it follows build-out scenarios (`[buildout]`). History calibrates the "
        f"link: solar's share of load grew from {cal['share_start']:.1%} ({first}) to "
        f"{cal['share_end']:.1%} ({last}) while {sum(bo['history_pv_additions_gw']):g} GW of "
        f"solar were added, {cal['kappa'] * 100:.3f} share points per GW. A GWh of storage "
        f"takes {cal['lam'] * 100:.3f} points out of the cheap hours "
        f"({bo['storage_cycles_per_year']:g} cycles a year, "
        f"{bo['storage_solar_fraction']:.0%} of them charged from solar, "
        f"{cal['load_twh']:.0f} TWh of load); only storage beyond history's "
        f"{bo['history_storage_additions_gwh']:g} GWh a year counts. "
        f"On monthly history ({reg['n']} months) each point of solar share lowered the capture "
        f"rate by {abs(reg['share_coef']):.1f}% (log form, se {reg['share_se']:.1f}); new solar "
        f"adds most share in sunny months, which weigh {cal['amplification']:.2f} times as much. "
        "The level effect of section 7 and the forward curve stay as they were.\n\n"
        + "\n".join(lines) + "\n\n"
        f"With the fixed −1 pp a year of v1.10 the {years}-year fair price was {fixed}. Storage is "
        f"what decides: in the base case solar's capture rate falls by {fall:.0%} a year, and "
        "only a storage build-out several times history's slows it much. The scenarios "
        f"extrapolate a link measured on {reg['n']} months up to {last}, in which storage was "
        "small; flexible demand, exports and curtailment rules are not in it.")


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
    cases = list(dict.fromkeys(r["case"] for rs in tenors.values() for r in rs))
    rows = []
    for case in cases:
        row = {"Case": case}
        for park, rs in tenors.items():
            r = next((r for r in rs if r["case"] == case), None)
            row[f"{names[park]}: fair"] = "–" if r is None else f"{r['fair_price']:.2f}"
            row[f"{names[park]}: indicative"] = "–" if r is None else f"{r['indicative']:.2f}"
        rows.append(row)
    return pd.DataFrame(rows).to_markdown(index=False)


def _n(x: float) -> str:
    """Two decimals with a true minus sign."""
    return f"{round(x, 2) + 0.0:.2f}".replace("-", "−")


def _slope(reg: dict | None) -> str:
    if reg is None:
        return "–"
    return f"{_n(reg['coef'])} ({_n(reg['ci_low'])} to {_n(reg['ci_high'])})"


def _level_md(effects: dict[str, dict], regs: dict, names: dict[str, str], low: float,
              high: float, start: int) -> str:
    ref = next(iter(effects.values()))["ref_level"]
    rows = [
        (f"History {regs['start_year']}-{regs['last_year']}: slope (95% interval)",
         lambda e: _slope(e["history"])),
        ("t-statistic; months", lambda e: "–" if e["history"] is None
         else f"{e['history']['t']:.1f}; {e['history']['n']}"),
        (f"History {regs['first_year']}-{regs['last_year']}, all years",
         lambda e: _slope(e["history_all_years"])),
        (f"Model: recent level ({ref:.0f}) to forward {start}", lambda e: _n(e["slope_recent"])),
        (f"Model: over the tenor's forwards ({low:.0f} to {high:.0f})",
         lambda e: _n(e["slope_tenor"])),
    ]
    lines = ["| Change of capture rate per unit of ln(price) | "
             + " | ".join(names[p] for p in effects) + " |",
             "|---|" + "---|" * len(effects)]
    for label, cell in rows:
        lines.append(f"| {label} | " + " | ".join(cell(e) for e in effects.values()) + " |")
    return "\n".join(lines)


def _build_out(effects: dict[str, dict], names: dict[str, str], drifts: dict[str, float],
               scenarios: set[str] = frozenset()) -> str:
    """What history's build-out coefficient means at the recent pace, against the assumed trend
    (or the build-out scenarios of section 8 for the parks in `scenarios`)."""
    def pp(x: float, digits: int) -> str:
        return f"{round(x * 100, digits) + 0.0:+.{digits}f}".replace("-", "−")

    parts = []
    for park, e in effects.items():
        reg, pace = e["history"], e.get("share_pace")
        if reg is None or pace is None:
            continue
        parts.append(f"{names[park].lower()} {_n(reg['share_coef'])} per unit of its share of "
                     f"load, which grew {pace['per_year'] * 100:.1f} pp a year in "
                     f"{pace['from']}-{pace['to']}: {pp(reg['share_coef'] * pace['per_year'], 1)} "
                     "pp of capture rate a year ("
                     + ("base case: build-out scenarios, section 8" if park in scenarios
                        else f"base-case trend {pp(drifts[park], 0)} pp") + ")")
    if not parts:
        return ""
    close = (" Section 8 turns this into build-out scenarios, in which storage slows solar's "
             "fall." if scenarios else
             " The trend assumes that storage, flexible demand and curtailment slow solar's "
             "fall; the −2 pp row of section 4 is closer to history's pace.")
    return ("\n\nBuild-out, from the same regression at a fixed price level: " + "; ".join(parts)
            + "." + close)


def _level_verdict(effects: dict[str, dict], names: dict[str, str]) -> str:
    parts = []
    for park, e in effects.items():
        reg = e["history"]
        if reg is None:
            continue
        where = "inside" if reg["ci_low"] <= e["slope_recent"] <= reg["ci_high"] else "outside"
        if reg["ci_low"] > 0:
            history = (f"the capture rate rises with the price level (slope {_n(reg['coef'])}, "
                       f"t = {reg['t']:.1f}), so the shape-factor view (slope 0) is rejected")
        elif reg["ci_high"] < 0:
            history = f"the capture rate falls with the price level (slope {_n(reg['coef'])})"
        else:
            history = (f"history cannot tell the slope from zero ({_n(reg['coef'])}, "
                       f"t = {reg['t']:.1f})")
        parts.append(f"**{names[park]}**: {history}; the model's {_n(e['slope_recent'])} lies "
                     f"{where} the 95% interval.")
    return " ".join(parts)


def to_strict_json(obj):
    """JSON-safe copy: NaN becomes null, NumPy numbers become Python floats."""
    if isinstance(obj, dict):
        return {k: to_strict_json(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [to_strict_json(v) for v in obj]
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
        return {"report": path, "results": None, "stack": None, "revenue": None, "buyer": None,
                "level": None}

    solar, wind = parks(settings)
    names = {p.name: ("Solar park" if p is solar else "Wind park") for p in (solar, wind)
             if p.name in ppa.parks}
    q = ppa.risk_quantile
    base = scenario_set(settings, inputs, pd.Timestamp(ppa.analog_pool_start))
    whole = None
    if pd.Timestamp(ppa.analog_pool_start) > pd.Timestamp(pm.calibration_start):
        whole = scenario_set(settings, inputs, pd.Timestamp(pm.calibration_start))

    # Does the capture rate move with the price level? The model's answer at each forward,
    # and history's (PPA-8d)
    recent = recent_level(settings)
    all_prices = hourly_prices(settings)
    eeg = eeg_specs(settings, names, inputs, all_prices)
    grid = model_response(settings, inputs, base, names, level_grid(settings, recent), eeg)
    ref = next(r for r in grid if r["forward"] == round(recent, 2))
    regs = level_regressions(settings)
    techs = {p.name: ("solar" if p is solar else "wind") for p in (solar, wind)}
    f0 = float(base.prices.mean())
    low = min([pm.forward_eur_mwh, *ppa.forward_curve.values()])
    # What history's build-out trend would do in one more year, at the same forward
    implied = None
    if pm.intraday_trend:
        later = scenario_set(replace(settings, price_model=replace(
            pm, delivery_year=pm.delivery_year + 1)), inputs, pd.Timestamp(ppa.analog_pool_start))
        first = capture_rates(base, names)
        implied = {p: rate - first[p] for p, rate in capture_rates(later, names).items()}
    check_path = settings.processed_dir / "out_of_sample.json"
    check = json.loads(check_path.read_text()) if check_path.exists() else None

    priced, tenors, results, effects, negative = {}, {}, {}, {}, {}
    eeg_results = {}
    bo = buildout_paths(settings, ppa.start_year, ppa.tenor_years)
    end_year = ppa.start_year + ppa.tenor_years - 1
    below = ppa.curtail_below_eur_mwh
    for park in names:
        cost = ppa.parks[park]
        priced[park] = price_park(base.prices, base.volume(park), cost, q, below)
        alt, whole_window = None, None
        if whole is not None:
            whole_premia = risk_premia(whole.prices, whole.volume(park), q)
            alt = whole_premia["fair_price"]
            whole_window = {"fair_price": alt, "premium": whole_premia["joint"]}
        response = park_response(grid, park)
        reg = regs[techs[park]] if regs else None
        e = effects[park] = {
            "ref_level": ref["average"], "ref_rate": ref["capture_rate"][park],
            "slope_recent": model_slope(response, ref["average"], f0),
            "slope_tenor": model_slope(response, low, f0), "history": reg,
            "history_all_years": regs[f"{techs[park]}_all_years"] if regs else None,
            "history_years": f"{regs['start_year']}-{regs['last_year']}" if regs else None,
            "share_pace": regs[f"{techs[park]}_share_pace"] if regs else None}
        history = None if reg is None else {
            label: line_response(response["level"], e["ref_level"], e["ref_rate"], reg[end])
            for label, end in ((LEVEL_LOW, "ci_low"), (LEVEL_HIGH, "ci_high"))}
        error = check["bias"][park]["capture_rate"] if check and park in check["bias"] else None
        e["out_of_sample_error"] = error
        e["trend_implied_drift"] = None if implied is None else implied[park]
        factors = bo["scenarios"][bo["base"]]["factors"] if bo and cost.buildout else None
        others = None if factors is None else {
            f"Build-out: {sc['label']}": sc["factors"] for name, sc in bo["scenarios"].items()
            if name != bo["base"]}
        tenors[park] = tenor_rows(priced[park], cost, ppa.start_year, ppa.tenor_years,
                                  ppa.discount_rate, alt, ppa.forward_curve, response, history,
                                  error, factors, others)
        stack = priced[park]["stack"]
        e["tenor_fair_without_level_effect"] = tenor_price(
            stack["fair_price"], stack["forward"], priced[park]["energy_mwh"], ppa.start_year,
            ppa.tenor_years, ppa.discount_rate, capture_rate_drift=cost.capture_rate_drift,
            degradation=cost.degradation, forward_curve=ppa.forward_curve,
            capture_rate_factors=factors).attrs["price"]
        if below is not None:
            negative[park] = price_clause(base, whole, park, cost, q, below, grid, ppa,
                                          priced[park], all_prices, inputs["gen"][park], tz,
                                          factors)
        fixed_trend = None
        if factors is not None:          # the v1.10 view: -1 pp a year, no build-out scenario
            s0 = priced[park]["stack"]
            fixed_trend = tenor_price(
                s0["fair_price"], s0["forward"], priced[park]["energy_mwh"], ppa.start_year,
                ppa.tenor_years, ppa.discount_rate, capture_rate_drift=-0.01,
                degradation=cost.degradation, forward_curve=ppa.forward_curve,
                level_response=response).attrs["price"]
        if park in eeg:
            eeg_results[park] = eeg_comparison(grid, park, eeg[park], ppa, cost, tenors[park],
                                               low)
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
            "level_response": response,
            "level_effect": e,
            "daily_profile": daily_profile(base.prices, base.volume(park), base.index, tz),
            "negative_prices": negative.get(park),
            "eeg": eeg_results.get(park),
            "buildout": None if factors is None else {
                "base": bo["base"], "scenarios": bo["scenarios"],
                "tenor_with_fixed_trend": fixed_trend},
            "assumptions": {"balancing_eur_mwh": cost.balancing_eur_mwh,
                            "credit_eur_mwh": cost.credit_eur_mwh,
                            "capture_rate_drift": cost.capture_rate_drift,
                            "degradation": cost.degradation},
            "tenor": {"years": list(range(ppa.start_year, end_year + 1)),
                      "fair_price": tenors[park][0]["fair_price"],
                      "indicative": tenors[park][0]["indicative"],
                      "sensitivity": tenors[park]},
        }

    forward = {"price_eur_mwh": pm.forward_eur_mwh,
               "date": str(pm.forward_date) if pm.forward_date else None,
               "source": pm.forward_source or None}
    quarters = quarter_forwards(pm.forward_eur_mwh, pm.quarter_quotes, pm.delivery_year,
                                settings.timezone)
    if quarters:
        forward["quarters"] = {str(q): v for q, v in quarters.items()}
        forward["quarters_date"] = str(pm.quarter_quotes.date)
    out_json = settings.processed_dir / "ppa_pricing.json"
    out_json.write_text(json.dumps(to_strict_json({
        "generated_utc": f"{datetime.now(UTC):%Y-%m-%d %H:%M}", "delivery_year": ppa.start_year,
        "tenor_years": ppa.tenor_years, "discount_rate": ppa.discount_rate,
        "analog_pool_start": str(ppa.analog_pool_start),
        "scenarios": int(base.prices.shape[0]), "forward": forward,
        "recent_level_eur_mwh": recent,
        "level_effect": None if regs is None else {
            k: regs[k] for k in ("start_year", "first_year", "last_year")},
        "level_grid": grid,
        "curtail_below_eur_mwh": below,
        "buildout": None if bo is None else {k: v for k, v in bo.items() if k != "scenarios"},
        "forward_curve": {str(y): f_y for y, f_y in sorted(ppa.forward_curve.items())},
        "parks": results}), indent=1, allow_nan=False))

    fig_dir = settings.reports_dir / "figures"
    lead = next(iter(names))
    figs = {
        "stack": fig_stack({p: r["stack"] for p, r in priced.items()}, names,
                           fig_dir / "step07_price_stack.png"),
        "revenue": fig_revenue(structure_revenues(base.prices, base.volume(lead), below),
                               names[lead],
                               fig_dir / "step07_revenue.png"),
        "buyer": fig_buyer(base.prices, base.volume(lead), names[lead], q,
                           fig_dir / "step07_buyer_risk.png"),
        "level": fig_level(grid, effects, names, tenor_forwards(f0, ppa.forward_curve, end_year,
                                                                 ppa.start_year),
                           fig_dir / "step07_level_effect.png"),
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
    if lead_r.get("buildout"):
        span_bo = [r["indicative"] for r in tenors[lead]
                   if r["case"] == "Base case" or r["case"].startswith("Build-out:")]
        answer += (
            f" After {ppa.start_year} the capture rate follows the "
            f"{bo['scenarios'][bo['base']]['label'].split(':')[0].lower()} build-out scenario "
            f"(section 8); across the scenarios the indicative price ranges from "
            f"{min(span_bo):.1f} to {max(span_bo):.1f} EUR/MWh, and storage decides where.")

    scenario_parks = {p for p in names if results[p].get("buildout")}

    def trend(p: str) -> str:
        drift = ppa.parks[p].capture_rate_drift
        text = f"{drift * 100:+.0f} pp a year"
        if p not in scenario_parks:
            return f"{names[p].lower()} {text}"
        label = bo["scenarios"][bo["base"]]["label"].split(":")[0].lower()
        return (f"{names[p].lower()} the {label} build-out scenario (section 8)"
                + (f" and {text}" if drift else ""))

    trends = "; ".join(trend(p) for p in names)
    lead_e = effects[lead]
    level_note = (
        "\nEach year's capture rate moves with that year's forward along the model's own "
        "response to the price level (section 7), on top of the trend.")
    if lead_e["history"] is not None:
        level_note += (
            " The two rows on the capture rate vs price level use history's 95% interval for "
            f"that slope instead, from the recent level ({lead_e['ref_level']:.0f} EUR/MWh): a "
            f"flatter slope gives a lower capture rate at the high {ppa.start_year} forward but a "
            "higher one once the curve falls below the recent level.")
    if lead_e.get("out_of_sample_error") is not None:
        errors = ", ".join(f"{names[p].lower()} {effects[p]['out_of_sample_error']:+.3f}"
                           for p in names if effects[p].get("out_of_sample_error") is not None)
        years = check["bias"][lead].get("years") or [y["year"] for y in check["years"]]
        level_note += (
            " The last row takes the model's mean out-of-sample capture-rate error off every "
            f"year ({errors}; test years {', '.join(str(y) for y in years)}, fitted like "
            f"{ppa.start_year}; Step 6, section 4): fitted on the years before, the model "
            "overstated capture rates even with the price level given.")
    if lead_e.get("trend_implied_drift") is not None:
        pace = ", ".join(f"{names[p].lower()} "
                         + f"{effects[p]['trend_implied_drift'] * 100:+.1f} pp".replace("-", "−")
                         for p in names)
        level_note += (
            f" The {ppa.start_year} scenarios carry history's build-out trend up to "
            f"{ppa.start_year} (Step 6, section 4); continued for one more year at the same "
            f"forward it would move the capture rate by {pace}. After that the base case "
            f"follows: {trends}"
            + ("; the build-out rows show the other scenarios, and the trend rows move "
               "the capture rate by whole points a year on top." if scenario_parks else
               ": storage, flexible demand and curtailment are expected to slow the fall, and "
               "a straight line would take solar's capture rate towards zero within a decade "
               "(the −2 pp row is the steeper view)."))
    level_note += "\n"
    without = ", ".join(f"{names[p].lower()} {effects[p]['tenor_fair_without_level_effect']:.1f}"
                        for p in names)
    level_section = (
        "The price model shifts all hours together in arcsinh units, so a higher price level "
        "lifts the hours near zero and solar's capture rate rises with it. The usual "
        "shape-factor view scales all hours instead, and the capture rate stays put. The "
        f"{ppa.start_year} forward ({f0:.0f} EUR/MWh) lies above the recent level "
        f"({lead_e['ref_level']:.0f}) and the curve falls to {low:.0f}, so the answer moves "
        "the price.\n\nHistory decides: monthly capture rates regressed on ln(average price), "
        "with month effects and the technology's share of load (its build-out) held fixed; "
        "HC1 standard errors (`analysis/level_effect.py`). The model's slope comes from "
        "rebuilding the scenarios at each forward with the same random draws.\n\n"
        + (_level_md(effects, regs, names, low, f0, ppa.start_year) + "\n\n"
           + _level_verdict(effects, names)
           + _build_out(effects, names, {p: ppa.parks[p].capture_rate_drift for p in names},
                        scenario_parks)
           if regs else
           "No power data for the history check: run `ppa-lab data` first.")
        + "\n\nSo the base case moves each year's capture rate along the model's response "
        f"(chart below); holding the first year's capture rate over the tenor instead (as "
        f"before v1.5) would give fair prices of {without} EUR/MWh.")
    buildout_text = _buildout_md(bo, tenors, priced, names, results, ppa.start_year,
                                 ppa.tenor_years)
    eeg_text = "\n\n".join(f"### {names[p]}\n\n" + _eeg_md(e, names[p], ppa.start_year,
                                                             ppa.tenor_years)
                           for p, e in eeg_results.items()) or "No park under the EEG (`[eeg]`)."
    curtail_text, negative_text = "", "Not configured (`[ppa] curtail_below_eur_mwh`)."
    if negative:
        curtail_text = (
            f"A park that sells at spot, or is not paid at negative prices, stops producing "
            f"below {below:g} EUR/MWh, so those structures earn more on average by the value of "
            "curtailing (section 5); the plain PPA and the merchant that keeps producing forgo "
            "it. ")
        gap = ""
        if check:
            like = [y for y in check["years"] if y.get("trend", True)] or check["years"]
            diffs = [y["parks"][lead]["negative_output_share"]["p50"]
                     - y["parks"][lead]["negative_output_share"]["history"] for y in like]
            gap = (f" Out of sample (Step 6, section 4) the model put the {names[lead].lower()}'s "
                   f"output at negative prices {abs(np.mean(diffs)) * 100:.0f} percentage points "
                   f"{'below' if np.mean(diffs) < 0 else 'above'} history, so these values are "
                   f"{'if anything low' if np.mean(diffs) < 0 else 'if anything high'}.")
        negative_text = (
            "In hours with negative prices output is worth less than nothing. A park that sells "
            "at spot stops producing then: its marginal cost is about zero, and no subsidy is "
            "paid at negative prices (§51 EEG). Under a plain pay-as-produced PPA it is paid the "
            "strike for every MWh, so it keeps producing and the buyer sells that output at a "
            "loss: the value of curtailing is lost to both sides. Three ways to handle it:\n\n"
            "- **Plain PPA** (the base case above): nobody curtails; the fair price includes "
            "the negative hours.\n"
            "- **Negative-price clause**: nothing is paid at negative prices and the park "
            "curtails. The strike is the fair price of the output delivered, higher per MWh, "
            "and the park keeps the value of curtailing, but it takes back volume risk: sunny, "
            "cheap years have more negative hours.\n"
            "- **Deemed output**: the buyer may curtail and pays the curtailed output as if "
            "produced. The strike rises by the value of curtailing; the producer's risk stays "
            "that of the plain PPA.\n\n"
            + _negative_md(negative, priced, tenors, names, ppa.start_year, ppa.tenor_years)
            + "\n\nThe clause's tenor price follows the curtailed output's capture rate and its "
            "delivered share at each year's forward (more negative hours at lower forwards), "
            "plus the capture-rate trend"
            + (" and the solar build-out scenario of section 8 (it leaves the delivered share "
               "unchanged)" if scenario_parks else "")
            + "; the first year's premium and costs apply to every "
            "year. In history the parks' output at negative prices grew with the build-out:\n\n"
            + _curtailment_history_md(negative, names) + "\n\n2026: January to September."
            + gap)
    report = header + f"""Inputs: the Step 6 joint scenarios for {ppa.start_year}
({base.prices.shape[0]} scenarios: {len(set(base.weather_years))} weather years x
{settings.scenarios.paths_per_weather_year} price paths), with intraday patterns from analog days
from **{ppa.analog_pool_start}** on (the most recent regime; the whole window is a sensitivity).
Forward: {describe_forward(forward, ppa.forward_curve, ppa.start_year)}. The scenarios average
{base.prices.mean():.2f} EUR/MWh in {ppa.start_year}. Risk measures at the {q:.0%} quantile.

## 1. What each structure leaves with the producer ({ppa.start_year})

All structures struck at their own fair price. {curtail_text}The spread of annual revenue is
what changes most: the 95% cash flow at risk.

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

Discounted at {ppa.discount_rate:.0%} (mid-year), energy-weighted; forwards as above. Capture rate
after {ppa.start_year} (base case): {trends}. Solar output degrades
{ppa.parks[lead].degradation:.1%} per year. The risk premium and costs per MWh of the first year
are applied to every year (a simplification).

{_tenor_md(tenors, names)}
{level_note}
## 5. Negative prices: curtail, and who keeps the value

{negative_text}

## 6. The EEG premium against a PPA

{eeg_text}

## 7. Does the capture rate rise with the price level?

{level_section}

![Capture rate vs price level](figures/{figs["level"].name})

## 8. Solar and storage build-out after {ppa.start_year}

{buildout_text}

## 9. The answer

{answer}

## 10. Charts

![Price stack](figures/{figs["stack"].name})

![Revenue by structure](figures/{figs["revenue"].name})

![The buyer's risk](figures/{figs["buyer"].name})

Results for Step 9: `data/processed/{out_json.name}`.
"""
    path.write_text(report)
    log.info("wrote %s and %s", path, out_json)
    return {"report": path, "results": out_json, **figs}
