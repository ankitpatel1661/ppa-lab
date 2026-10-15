"""Step 6 report: the weather-price link, its validation, and joint scenarios.

Output:
    data/processed/scenarios_<year>.parquet   one row per scenario, linked and independent
    reports/step06_joint_scenarios.md
    reports/figures/step06_*.png
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.plotting import BLUE, INK, INK_2, ORANGE, save, style
from ppa_lab.analysis.step05_report import calibration_history, hourly_prices
from ppa_lab.config import Park, Settings
from ppa_lab.prices.model import fit, simulate
from ppa_lab.prices.validation import compare_with_history
from ppa_lab.pricing.forwards import quarter_forwards
from ppa_lab.scenarios.generator import build_scenarios, fair_price, scenario_table
from ppa_lab.scenarios.link import WeatherLink, fit_link, restrict_pool, simulate_linked
from ppa_lab.scenarios.out_of_sample import out_of_sample, park_statistics
from ppa_lab.scenarios.weather import (
    FEATURES,
    daily_features,
    day_hour_matrix,
    monthly_climatology,
)

log = logging.getLogger(__name__)

LABELS = {"mean": "Mean (EUR/MWh)", "std": "Standard deviation", "p01": "1% quantile",
          "p05": "5% quantile", "p50": "Median", "p95": "95% quantile", "p99": "99% quantile",
          "negative_share": "Share of negative hours", "acf_1h": "Autocorrelation, 1 hour",
          "acf_24h": "Autocorrelation, 24 hours", "acf_168h": "Autocorrelation, 1 week"}
GREY = "#a9a9a4"


def parks(settings: Settings) -> tuple[Park, Park]:
    """The solar park and the wind park of the configuration."""
    solar = next(p for p in settings.parks if p.technology == "solar")
    wind = next(p for p in settings.parks if p.technology.startswith("wind"))
    return solar, wind


def load_weather_inputs(settings: Settings) -> dict | None:
    """Daily weather features and day x hour generation of both parks (None if Step 4 is
    missing). Temperature comes from the solar site."""
    proc, tz = settings.processed_dir, settings.timezone
    solar, wind = parks(settings)
    files = [proc / f"generation_{solar.name}.parquet", proc / f"generation_{wind.name}.parquet",
             proc / f"weather_{solar.name}.parquet"]
    if not all(f.exists() for f in files):
        return None
    gen = {p.name: pd.read_parquet(proc / f"generation_{p.name}.parquet")["mw"]
           for p in (solar, wind)}
    temp = pd.read_parquet(proc / f"weather_{solar.name}.parquet")["temp_air_c"]
    features = daily_features(gen[solar.name], gen[wind.name], temp, solar.capacity_mw,
                              wind.capacity_mw, tz)
    return {"gen": gen, "features": features,
            "matrices": {name: day_hour_matrix(g, tz) for name, g in gen.items()}}


def complete_weather_years(matrices: dict[str, pd.DataFrame], first: int, last: int) -> list[int]:
    """Weather years with a full day x hour matrix for every park."""
    years = []
    for y in range(first, last + 1):
        days = pd.date_range(f"{y}-01-01", f"{y}-12-31", freq="D")
        if all(m.reindex(days).notna().all().all() for m in matrices.values()):
            years.append(y)
    return years


# --------------------------------------------------------------------------- #
# Calculations used by the report
# --------------------------------------------------------------------------- #
def eur_per_unit(link: WeatherLink, scale: float, price: float) -> pd.DataFrame:
    """The weather response in EUR/MWh at a given price level: per +0.1 capacity factor
    (solar, wind) and per +1 degree C. dP/dy = s cosh(arcsinh(P / s))."""
    slope = scale * np.cosh(np.arcsinh(price / scale))
    step = pd.Series({"solar": 0.1, "wind": 0.1, "temp": 1.0})
    return link.beta[list(FEATURES)] * step * slope


def capture_rates_by_year(history: pd.Series, gen: dict[str, pd.Series],
                          sims: dict[str, np.ndarray], tz: str) -> pd.DataFrame:
    """Per complete local year and park: history and each model's median and 5-95% range."""
    year = history.index.tz_convert(tz).year
    rows = []
    for y in sorted(set(year)):
        mask = np.asarray(year == y)
        if mask.sum() < 8760:
            continue
        p_hist = history.to_numpy()[mask]
        for park, mw in gen.items():
            q = mw.reindex(history.index[mask]).to_numpy()
            if np.isnan(q).any():
                continue
            row = {"year": y, "park": park,
                   "history": (p_hist * q).sum() / q.sum() / p_hist.mean()}
            for name, paths in sims.items():
                p = paths[:, mask]
                r = (p * q).sum(axis=1) / q.sum() / p.mean(axis=1)
                row[f"{name}_p50"] = np.median(r)
                row[f"{name}_p05"], row[f"{name}_p95"] = np.percentile(r, [5, 95])
            rows.append(row)
    return pd.DataFrame(rows)


TAIL_CANDIDATES = (None, 40.0, 15.0, 5.0)     # scales b of negative prices compared in-sample
TAIL_KEYS = ("p01", "negative_share", "negative_output")


def _tail_row(prices: np.ndarray, solar_mw: np.ndarray) -> dict[str, float]:
    p = np.atleast_2d(prices)
    stats = park_statistics(p, solar_mw)
    return {"p01": float(np.mean(np.quantile(p, 0.01, axis=1))),
            "negative_share": float((p < 0).mean()),
            "negative_output": float(np.median(stats["negative_output_share"])),
            "capture_rate": float(np.median(stats["capture_rate"]))}


def tail_check(settings: Settings, history: pd.Series, features: pd.DataFrame,
               solar_mw: pd.Series, climatology: pd.DataFrame, n_paths: int) -> pd.DataFrame:
    """The negative tail in-sample (real weather, analog days at least the exclusion away)
    for several scales b of negative prices, history first: 1% quantile, share of negative
    hours, the solar park's output share at negative prices and capture rate, and the largest
    relative error of the first three."""
    pm, sc, tz = settings.price_model, settings.scenarios, settings.timezone
    days = pd.DatetimeIndex(sorted(set(history.index.tz_convert(tz).normalize().tz_localize(None))))
    q = solar_mw.reindex(history.index).to_numpy()
    ok = ~np.isnan(q)
    rows = {"History": _tail_row(history.to_numpy()[ok], q[ok])}
    candidates = list(dict.fromkeys([*TAIL_CANDIDATES, pm.negative_scale_eur_mwh]))
    for b in candidates:
        model = fit(history, tz, pm.scale_eur_mwh, b)
        link = fit_link(model, history, features, climatology, tz, sc.analog_window_days,
                        sc.analog_k)
        paths = simulate_linked(model, link, history.index, tz, features.reindex(days), n_paths,
                                seed=pm.seed, exclude_days=sc.validation_exclusion_days)
        label = f"b = {pm.scale_eur_mwh:g} (symmetric)" if b is None else f"b = {b:g}"
        if b == pm.negative_scale_eur_mwh:
            label += " (configured)"
        rows[label] = _tail_row(paths[:, ok], q[ok])
    table = pd.DataFrame(rows).T
    truth = table.loc["History", list(TAIL_KEYS)]
    error = (table[list(TAIL_KEYS)] - truth).abs() / truth.abs()
    table["largest_error"] = error.max(axis=1).where(table.index != "History")
    return table


def out_of_sample_check(settings: Settings, inputs: dict, n_paths: int) -> dict | None:
    """Each configured test year simulated by a model fitted on the days before it only,
    and by one that has seen it (see `scenarios.out_of_sample`). None if not configured."""
    pm, sc, tz = settings.price_model, settings.scenarios, settings.timezone
    if not sc.out_of_sample_years:
        return None
    prices = hourly_prices(settings)
    years = []
    for year in sc.out_of_sample_years:
        start, end = date(year, 1, 1), min(date(year, 12, 31), settings.end)
        weather_years = complete_weather_years(inputs["matrices"], settings.weather_first_year,
                                               year - 1)
        climatology = monthly_climatology(inputs["features"], weather_years[0],
                                          weather_years[-1])
        runs = {seen: out_of_sample(prices, inputs["features"], inputs["gen"], climatology, tz,
                                    pm.scale_eur_mwh, sc.out_of_sample_train_start, start, end,
                                    sc.analog_window_days, sc.analog_k, n_paths=n_paths,
                                    seed=pm.seed, negative_scale=pm.negative_scale_eur_mwh,
                                    seen=seen, exclude_days=sc.validation_exclusion_days)
                for seen in (False, True)}
        table = runs[False]["statistics"]
        years.append({"year": year, "test": runs[False]["test"],
                      "inside": int(table["inside_range"].sum()), "statistics": len(table),
                      "table": table.drop(columns="inside_range").to_dict(orient="index"),
                      "parks": runs[False]["parks"], "seen": runs[True]["parks"]})
    bias = {}
    for park in inputs["gen"]:
        errors = [y["parks"][park]["capture_rate"]["p50"] - y["parks"][park]["capture_rate"]
                  ["history"] for y in years]
        seen = [y["seen"][park]["capture_rate"]["p50"] - y["seen"][park]["capture_rate"]
                ["history"] for y in years]
        bias[park] = {"capture_rate": float(np.mean(errors)), "min": float(np.min(errors)),
                      "max": float(np.max(errors)), "seen": float(np.mean(seen))}
    return {"train_start": str(sc.out_of_sample_train_start), "years": years, "bias": bias}


def within_month_daily(prices: np.ndarray, index: pd.DatetimeIndex, tz: str) -> pd.Series:
    """Daily mean price minus its month's mean (local days)."""
    day = index.tz_convert(tz).normalize().tz_localize(None)
    daily = pd.Series(prices, index=day).groupby(level=0).mean()
    return daily - daily.groupby([daily.index.year, daily.index.month]).transform("mean")


def pool_start_options(start: date, end: date) -> list[tuple[str, pd.Timestamp]]:
    """Candidate first days of the analog pool: the whole window, the latest complete
    calendar year onward, and the last 12 months (duplicates dropped)."""
    last_full = end.year if (end.month, end.day) == (12, 31) else end.year - 1
    options = [("whole window", pd.Timestamp(start)),
               (f"{last_full} onward", pd.Timestamp(last_full, 1, 1)),
               ("last 12 months", pd.Timestamp(end) - pd.Timedelta(days=364))]
    seen, out = set(), []
    for label, day in options:
        day = max(day, pd.Timestamp(start))
        if day not in seen:
            seen.add(day)
            out.append((label, day))
    return out


def fair_price_standard_error(table: pd.DataFrame, park: str) -> float:
    """Monte Carlo standard error of the ratio estimator sum(rev) / sum(MWh)."""
    k = fair_price(table, park)
    q, rev = table[f"{park}_mwh"], table[f"{park}_revenue_eur"]
    return float((rev - k * q).std(ddof=1) / np.sqrt(len(table)) / q.mean())


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_capture_rates(tables: dict[str, pd.DataFrame], history: pd.DataFrame,
                      names: dict[str, str], path: Path) -> Path:
    fig, axes = plt.subplots(1, len(names), figsize=(10, 3.6))
    for ax, (park, label) in zip(np.atleast_1d(axes), names.items(), strict=True):
        col = f"{park}_capture_rate"
        both = np.concatenate([tables["linked"][col], tables["independent"][col]])
        bins = np.linspace(both.min(), both.max(), 40)
        ax.hist(tables["independent"][col], bins=bins, color=GREY, alpha=0.8,
                label="Prices independent of weather (Step 5)")
        ax.hist(tables["linked"][col], bins=bins, color=BLUE, alpha=0.75,
                label="Prices linked to weather (Step 6)")
        dashes = ("--", ":", "-.")
        for i, (_, r) in enumerate(history[history["park"] == park].iterrows()):
            ax.axvline(r["history"], color=ORANGE, linewidth=1.8, linestyle=dashes[i % 3],
                       label=f"History {int(r['year'])}")
        ax.set_xlabel("Capture rate (capture price / baseload price)", color=INK_2, fontsize=9)
        style(ax, f"{label}: capture rate per scenario", "Scenarios")
    # Same entries in both panels: one legend, where the solar panel has empty space.
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=8, loc="upper left")
    return save(fig, path)


def fig_link(features: pd.DataFrame, panels: dict[str, pd.Series], path: Path) -> Path:
    wind = features["wind"]
    wind = wind - wind.groupby([wind.index.year, wind.index.month]).transform("mean")
    fig, axes = plt.subplots(1, len(panels), figsize=(11, 3.4), sharex=True, sharey=True)
    for ax, (title, price) in zip(axes, panels.items(), strict=True):
        x = wind.reindex(price.index)
        ax.scatter(x, price, s=6, color=INK if title == "History" else BLUE, alpha=0.45,
                   linewidths=0)
        ax.axhline(0, color=INK_2, linewidth=0.6)
        ax.set_xlabel("Wind capacity factor minus month's mean", color=INK_2, fontsize=9)
        style(ax, f"{title}: correlation {x.corr(price):+.2f}", "")
    axes[0].set_ylabel("Daily price minus month's mean (EUR/MWh)", color=INK_2, fontsize=9)
    return save(fig, path)


def fig_out_of_sample(check: dict, names: dict[str, str], path: Path) -> Path:
    """Per park and test year: history, the out-of-sample 5-95% range and median, and the
    median of the model that has seen the year."""
    fig, axes = plt.subplots(1, len(names), figsize=(11, 3.6))
    for ax, (park, label) in zip(np.atleast_1d(axes), names.items(), strict=True):
        for i, y in enumerate(check["years"]):
            r, seen = y["parks"][park]["capture_rate"], y["seen"][park]["capture_rate"]
            ax.plot([i, i], [r["p05"], r["p95"]], color=BLUE, linewidth=6, alpha=0.35,
                    solid_capstyle="butt", label="out of sample: 5-95%" if i == 0 else None)
            ax.plot(i, r["p50"], "o", color=BLUE, label="out of sample: median" if i == 0 else None)
            ax.plot(i + 0.18, seen["p50"], "D", color=ORANGE, markersize=5,
                    label="year seen: median" if i == 0 else None)
            ax.plot(i - 0.18, r["history"], "s", color=INK, markersize=5,
                    label="history" if i == 0 else None)
        ax.set_xticks(range(len(check["years"])), [str(y["year"]) for y in check["years"]])
        ax.set_xlim(-0.6, len(check["years"]) - 0.4)
        ax.legend(frameon=False, fontsize=7.5, loc="best")
        style(ax, f"{label}: capture rate in years the model never saw", "Capture rate")
    return save(fig, path)


def fig_convergence(table: pd.DataFrame, names: dict[str, str], path: Path, seed: int) -> Path:
    order = np.random.default_rng(seed).permutation(len(table))
    t = table.iloc[order]
    n = np.arange(1, len(t) + 1)
    fig, axes = plt.subplots(1, len(names), figsize=(10, 3.2))
    for ax, (park, label) in zip(np.atleast_1d(axes), names.items(), strict=True):
        revenue, mwh = t[f"{park}_revenue_eur"].cumsum(), t[f"{park}_mwh"].cumsum()
        running = (revenue / mwh).to_numpy()
        final, se = fair_price(table, park), fair_price_standard_error(table, park)
        ax.fill_between(n, final - 2 * se, final + 2 * se, color=BLUE, alpha=0.15, linewidth=0,
                        label="final value ± 2 standard errors")
        ax.plot(n, running, color=BLUE, linewidth=1.4, label="estimate after n scenarios")
        ax.axhline(final, color=INK, linewidth=0.8)
        ax.set_xlabel("Number of scenarios", color=INK_2, fontsize=9)
        style(ax, f"{label}: fair pay-as-produced price", "EUR/MWh")
    np.atleast_1d(axes)[0].legend(frameon=False, fontsize=8)
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _fmt(key: str, v: float) -> str:
    return f"{v:.1%}" if key == "negative_share" else f"{v:.3f}" if key.startswith("acf") \
        else f"{v:.1f}"


def _validation_table(tables: dict[str, pd.DataFrame]) -> str:
    rows = []
    base = next(iter(tables.values()))
    for key in base.index:
        row = {"Statistic": LABELS.get(key, key), "History": _fmt(key, base.loc[key, "history"])}
        for name, t in tables.items():
            mark = "yes" if t.loc[key, "inside_range"] else "no"
            row[f"{name} (inside?)"] = f"{_fmt(key, t.loc[key, 'simulated_mean'])} ({mark})"
        rows.append(row)
    return pd.DataFrame(rows).to_markdown(index=False)


def _range(r: pd.Series, model: str) -> str:
    return f"{r[f'{model}_p50']:.3f} ({r[f'{model}_p05']:.3f}-{r[f'{model}_p95']:.3f})"


def _capture_history_table(rates: pd.DataFrame, names: dict[str, str]) -> str:
    rows = []
    for _, r in rates.iterrows():
        rows.append({
            "Year": int(r["year"]), "Park": names[r["park"]], "History": f"{r['history']:.3f}",
            "Step 5 (independent)": _range(r, "step5"),
            "Step 6 (linked)": _range(r, "step6"),
        })
    return pd.DataFrame(rows).to_markdown(index=False)


def _tail_md(table: pd.DataFrame) -> str:
    out = pd.DataFrame({
        "1% quantile (EUR/MWh)": table["p01"].map(lambda v: f"{v:.1f}".replace("-", "−")),
        "Negative hours": table["negative_share"].map("{:.1%}".format),
        "Solar output at negative prices": table["negative_output"].map("{:.1%}".format),
        "Solar capture rate": table["capture_rate"].map("{:.3f}".format),
        "Largest error of the first three": table["largest_error"].map(
            lambda v: "–" if pd.isna(v) else f"{v:.0%}"),
    })
    return out.rename_axis("").to_markdown()


def _out_of_sample_md(check: dict, names: dict[str, str]) -> tuple[str, str]:
    stats = []
    for y in check["years"]:
        t = y["table"]

        def pair(key: str, fmt: str, t=t) -> str:
            text = f"{format(t[key]['history'], fmt)} / {format(t[key]['simulated_mean'], fmt)}"
            return text.replace("-", "−")

        stats.append({"Test year": f"{y['year']} ({y['test'][0]} to {y['test'][1]})",
                      "Inside 5-95%": f"{y['inside']} of {y['statistics']}",
                      "Std": pair("std", ".1f"), "1% quantile": pair("p01", ".1f"),
                      "5% quantile": pair("p05", ".1f"),
                      "Negative hours": pair("negative_share", ".1%"),
                      "Autocorrelation 24 h": pair("acf_24h", ".2f")})
    parks = []
    for y in check["years"]:
        for park, label in names.items():
            r, seen = y["parks"][park], y["seen"][park]
            cr, neg = r["capture_rate"], r["negative_output_share"]
            parks.append({
                "Year": y["year"], "Park": label, "Capture rate: history": f"{cr['history']:.3f}",
                "out of sample (5-95%)": f"{cr['p50']:.3f} ({cr['p05']:.3f}-{cr['p95']:.3f})",
                "year seen": f"{seen['capture_rate']['p50']:.3f}",
                "Output at negative prices: history / model": f"{neg['history']:.1%} / "
                                                              f"{neg['p50']:.1%}"})
    return (pd.DataFrame(stats).to_markdown(index=False),
            pd.DataFrame(parks).to_markdown(index=False))


def _results_table(tables: dict[str, pd.DataFrame], names: dict[str, str]) -> str:
    rows = []
    for park, label in names.items():
        for model, t in (("independent", tables["independent"]), ("linked", tables["linked"])):
            cr = np.percentile(t[f"{park}_capture_rate"], [5, 50, 95])
            rev = np.percentile(t[f"{park}_revenue_eur"], [10, 50, 90]) / 1e6
            rows.append({
                "Park": label, "Prices": model,
                "Fair PaP price (EUR/MWh)": f"{fair_price(t, park):.2f}",
                "Capture rate 5/50/95%": " / ".join(f"{v:.3f}" for v in cr),
                "Revenue P10/P50/P90 (EUR m)": " / ".join(f"{v:.2f}" for v in rev),
                "Corr(energy, baseload price)": f"{t[f'{park}_mwh'].corr(t['base_price']):+.2f}",
            })
    return pd.DataFrame(rows).to_markdown(index=False)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def write_step06_report(settings: Settings) -> dict[str, Path | None]:
    pm, sc, tz = settings.price_model, settings.scenarios, settings.timezone
    path = settings.reports_dir / "step06_joint_scenarios.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Step 6 report: joint weather and price scenarios\n\n"
              f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab scenarios`.\n\n")
    inputs = load_weather_inputs(settings)
    if inputs is None:
        path.write_text(header + "No site weather or generation found: run `ppa-lab weather` "
                        "first (Step 4).\n")
        return {"report": path, "scenarios": None, "capture_rates": None, "link": None,
                "convergence": None, "out_of_sample": None, "out_of_sample_results": None}

    solar, wind = parks(settings)
    names = {solar.name: "Solar park", wind.name: "Wind park"}
    features, gen, matrices = inputs["features"], inputs["gen"], inputs["matrices"]
    history = calibration_history(settings)
    years = complete_weather_years(matrices, settings.weather_first_year, sc.weather_last_year)
    climatology = monthly_climatology(features, years[0], years[-1])

    model = fit(history, tz, pm.scale_eur_mwh, pm.negative_scale_eur_mwh)
    link = fit_link(model, history, features, climatology, tz, sc.analog_window_days,
                    sc.analog_k)

    # 1. In-sample validation with the real weather of the calibration window.
    n_check = min(pm.n_paths, 200)
    days = pd.DatetimeIndex(sorted(set(history.index.tz_convert(tz).normalize().tz_localize(None))))
    sims = {
        "step5": simulate(model, history.index, tz, n_check, seed=pm.seed),
        "step6": simulate_linked(model, link, history.index, tz, features.reindex(days), n_check,
                                seed=pm.seed, exclude_days=sc.validation_exclusion_days),
    }
    validation = {"Step 5 (independent)": compare_with_history(history.to_numpy(), sims["step5"]),
                  "Step 6 (linked)": compare_with_history(history.to_numpy(), sims["step6"])}
    rates = capture_rates_by_year(history, gen, sims, tz)
    panels = {"History": within_month_daily(history.to_numpy(), history.index, tz),
              "Step 5, one path": within_month_daily(sims["step5"][0], history.index, tz),
              "Step 6, one path": within_month_daily(sims["step6"][0], history.index, tz)}

    # The negative tail for several scales of negative prices, and years never seen.
    tail = tail_check(settings, history, features, gen[solar.name], climatology, n_check)
    negative = history[history < 0]
    bunched = float((negative > -5).mean()) if len(negative) else float("nan")
    check = out_of_sample_check(settings, inputs, n_check)
    check_path = None
    if check is not None:
        check_path = settings.processed_dir / "out_of_sample.json"
        check_path.write_text(json.dumps(check, indent=1))

    # 2. Joint scenarios for the delivery year: linked, and independent for comparison.
    quarters = quarter_forwards(pm.forward_eur_mwh, pm.quarter_quotes, pm.delivery_year, tz)
    quarter_text = "" if quarters is None else (
        " with each quarter at the market's seasonal shape (Q1-Q4: "
        + " / ".join(f"{v:.1f}" for v in quarters.values())
        + f" EUR/MWh, quotes of {pm.quarter_quotes.date})")
    tables = {}
    for name, linked in (("linked", True), ("independent", False)):
        scen = build_scenarios(model, link, matrices, features, tz, pm.delivery_year, years,
                               sc.paths_per_weather_year, pm.forward_eur_mwh,
                               pm.level_volatility, sc.seed, linked=linked,
                               quarter_forwards=quarters)
        tables[name] = scenario_table(scen, list(names))
    n_scen = len(tables["linked"])

    # 3. Sensitivity: which historical days represent the delivery year's intraday patterns?
    sensitivity = []
    for label, start in pool_start_options(pm.calibration_start, pm.calibration_end):
        recent = restrict_pool(link, start)
        scen = build_scenarios(model, recent, matrices, features, tz, pm.delivery_year, years,
                               sc.paths_per_weather_year, pm.forward_eur_mwh,
                               pm.level_volatility, sc.seed, linked=True,
                               quarter_forwards=quarters)
        t = scenario_table(scen, list(names))
        row = {"Analog days from": f"{start:%Y-%m-%d} ({label})",
               "Days in pool": f"{len(recent.pool_days):,}"}
        for park, lab in names.items():
            row[f"{lab}: fair price"] = f"{fair_price(t, park):.2f}"
            row[f"{lab}: median capture rate"] = f"{t[f'{park}_capture_rate'].median():.3f}"
        sensitivity.append(row)
    outside = [f"{names[r['park']].lower()} {int(r['year'])} ({r['history']:.3f} vs "
               f"{r['step6_p05']:.3f}-{r['step6_p95']:.3f})" for _, r in rates.iterrows()
               if not r["step6_p05"] <= r["history"] <= r["step6_p95"]]
    out_table = pd.concat([t.assign(prices=name) for name, t in tables.items()])
    scen_path = settings.processed_dir / f"scenarios_{pm.delivery_year}.parquet"
    out_table.to_parquet(scen_path)

    fig_dir = settings.reports_dir / "figures"
    figs = {
        "capture_rates": fig_capture_rates(tables, rates, names,
                                           fig_dir / "step06_capture_rates.png"),
        "link": fig_link(features, panels, fig_dir / "step06_link.png"),
        "convergence": fig_convergence(tables["linked"], names, fig_dir / "step06_convergence.png",
                                       sc.seed),
        "out_of_sample": None if check is None else fig_out_of_sample(
            check, names, fig_dir / "step06_out_of_sample.png"),
    }

    eur = eur_per_unit(link, model.scale, pm.forward_eur_mwh)
    link_rows = pd.DataFrame({
        "R²": link.r_squared.map("{:.2f}".format),
        "+0.1 solar CF": eur["solar"].map("{:+.1f}".format),
        "+0.1 wind CF": eur["wind"].map("{:+.1f}".format),
        "+1 °C": eur["temp"].map("{:+.1f}".format),
    }).rename_axis("Season").to_markdown()
    inside = {name: int(t["inside_range"].sum()) for name, t in validation.items()}
    latest = rates["year"].max() if len(rates) else None
    coverage = []
    for park, label in names.items():
        if latest is None:
            break
        h = rates[(rates["year"] == latest) & (rates["park"] == park)]["history"]
        if h.empty:
            continue
        lo, hi = np.percentile(tables["linked"][f"{park}_capture_rate"], [5, 95])
        verdict = "inside" if lo <= h.iloc[0] <= hi else "outside"
        coverage.append(f"{label}: {latest} history {h.iloc[0]:.3f}, linked 5-95% "
                        f"{lo:.3f} to {hi:.3f} ({verdict})")
    level_note = ""
    if latest is not None:
        local_year = history.index.tz_convert(tz).year
        past = float(history[local_year == latest].mean())
        if abs(pm.forward_eur_mwh / past - 1.0) > 0.1:
            level_note = (f" The comparison mixes in the price level: {pm.delivery_year} is "
                          f"simulated at {pm.forward_eur_mwh:.0f} EUR/MWh, {latest} averaged "
                          f"{past:.0f}, and in this model the capture rate rises with the level "
                          "(Step 7 shows the sensitivity); the validation above is the test.")
    se = {label: fair_price_standard_error(tables["linked"], park) for park, label in names.items()}
    diff = {label: fair_price(tables["independent"], park) - fair_price(tables["linked"], park)
            for park, label in names.items()}

    b = pm.negative_scale_eur_mwh
    tail_text = (
        f"In the calibration window {bunched:.0%} of the negative hours lie between −5 and 0 "
        "EUR/MWh: prices bunch just below zero, where flexible plants stop producing. A "
        "symmetric transform spreads that bunch into a deep tail. Negative prices can have "
        "their own scale b, y = −a arcsinh(|P| / b), with a chosen so that −500 EUR/MWh maps "
        f"where it does with b = s = {pm.scale_eur_mwh:g}. In-sample, with the real weather "
        f"({n_check} paths, analog days at least {sc.validation_exclusion_days} days away):"
        f"\n\n{_tail_md(tail)}\n\n"
        + ("The configured model is symmetric. " if b is None else
           f"Configured: b = {b:g}, the candidate with the smallest largest error. ")
        + "A realistic tail raises the solar capture rate a little: the deep negative tail had "
        "been hiding midday dips that are not deep enough (section 4).")
    if check is None:
        oos_text = "Not configured (`[scenarios] out_of_sample_years`)."
    else:
        stats_md, parks_md = _out_of_sample_md(check, names)
        bias = check["bias"]
        parts = ", ".join(f"the {label.lower()}'s by {bias[park]['capture_rate']:+.3f} "
                          f"({bias[park]['min']:+.3f} to {bias[park]['max']:+.3f})"
                          for park, label in names.items())
        seen = " and ".join(f"{bias[park]['seen']:+.3f}" for park in names)
        oos_text = (
            f"For each test year the model and the link are fitted on the days from "
            f"{check['train_start']} up to the day before it, with analog days from its last "
            f"12 months (as for {pm.delivery_year}). The year is then simulated with its real "
            f"weather and each quarter at its realised average price: a perfect forward, so "
            "the test is about what the model adds (shape, tails, capture rates). Year seen: "
            "the same with the test year in the fit and in the analog pool (analog days at "
            f"least {sc.validation_exclusion_days} days away), which leaves only the model's "
            f"structural error. {n_check} paths each.\n\nHistory / model mean:\n\n"
            f"{stats_md}\n\n{parks_md}\n\n"
            f"Out of sample the model overstates capture rates: on average {parts}. With the "
            f"year seen the errors fall to {seen}: most of the error is one year of change, "
            "the midday dips deepening as solar capacity grows, which the analog days and the "
            f"daily shape learn a year late. The {pm.delivery_year} scenarios are built the "
            "same way, so they likely carry a similar error; Step 7 prices it as a "
            "sensitivity (backlog PPA-8e).\n\n"
            f"![Out-of-sample capture rates](figures/{figs['out_of_sample'].name})")

    sources = f"{settings.energy_charts.license}; ERA5 via Open-Meteo ({settings.weather_license})"
    report = header + f"""Data: {sources}.

## 1. The weather-price link

The Step 5 model drew each simulated day at random from its season. Here the day's weather
decides: its level responds to the weather anomaly (regression per season on the solar and
wind capacity factors of the two parks and the temperature), and its hourly pattern comes
from one of the {link.k} historical days within ±{link.window_days} days of the date whose
weather was closest (analog days). Calibration: {pm.calibration_start} to
{pm.calibration_end}, with the real weather of those days.

Response of the daily price level, in EUR/MWh at {pm.forward_eur_mwh:.0f} EUR/MWh
(capacity factor CF: mean output / capacity):

{link_rows}

What weather does not explain still reverts with phi = {link.phi:.3f} per day (half-life
{link.half_life_days:.2f} days). Analog pool: {len(link.pool_days):,} historical days.

## 2. Validation with the real weather of the calibration window

{n_check} paths each; analog days at least {sc.validation_exclusion_days} days away from the
simulated day (no peeking). Statistics with history inside the 5-95% range of the paths:
**Step 5: {inside["Step 5 (independent)"]} of {len(validation["Step 5 (independent)"])}; Step 6:
{inside["Step 6 (linked)"]} of {len(validation["Step 6 (linked)"])}.**

{_validation_table(validation)}

Capture rates of the parks in each complete year (median and 5-95% over paths):

{_capture_history_table(rates, names) if len(rates) else "No complete year in the window."}

History outside the Step 6 range: {", ".join(outside) if outside else "none"}.

## 3. The negative tail

{tail_text}

## 4. Out of sample: years the model never saw

{oos_text}

## 5. Delivery year {pm.delivery_year}: {n_scen} scenarios

{len(years)} weather years ({years[0]}-{years[-1]}) x {sc.paths_per_weather_year} price paths
= {n_scen} scenarios; forward {pm.forward_eur_mwh:.1f} EUR/MWh{quarter_text}, level uncertainty
{pm.level_volatility:.2f}. The same scenarios with prices independent of the weather
(Step 5 model) for comparison.

{_results_table(tables, names)}

- Ignoring the weather link overstates the fair pay-as-produced price by
  {" and ".join(f"{v:.2f} EUR/MWh ({k.lower()})" for k, v in diff.items())}.
- Monte Carlo standard error of the linked fair prices:
  {", ".join(f"{k.lower()} {v:.2f} EUR/MWh" for k, v in se.items())}.
- Does the latest historical capture rate fall inside the linked range?
  {"; ".join(coverage) if coverage else "no complete historical year available"}.{level_note}

Per-scenario results: `data/processed/{scen_path.name}` (input for Step 7).

### Sensitivity: which historical days represent {pm.delivery_year}?

Intraday patterns come from the analog pool. Midday solar dips deepened year by year as
solar capacity grew, so the pool's period matters. The base case above uses the whole
calibration window (as in the validation).

{pd.DataFrame(sensitivity).to_markdown(index=False)}

## 6. Charts

![Capture rates per scenario](figures/{figs["capture_rates"].name})

![The weather-price link in daily data](figures/{figs["link"].name})

![Convergence of the fair price](figures/{figs["convergence"].name})
"""
    path.write_text(report)
    log.info("wrote %s and %s", path, scen_path)
    return {"report": path, "scenarios": scen_path, "out_of_sample_results": check_path, **figs}
