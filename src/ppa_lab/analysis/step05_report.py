"""Step 5 report: calibrate the price model, validate it against history, simulate a year.

Output:
    data/processed/price_model.json        calibrated parameters (input for Step 6)
    reports/step05_price_model.md
    reports/figures/step05_*.png
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ppa_lab.analysis.plotting import BLUE, GRID, INK, INK_2, save, style
from ppa_lab.config import Settings
from ppa_lab.prices.calendar import SEASONS
from ppa_lab.prices.model import PriceModel, calibrate_level, fit, simulate
from ppa_lab.prices.validation import compare_with_history
from ppa_lab.timeutils import to_hourly

log = logging.getLogger(__name__)

LABELS = {"mean": "Mean (EUR/MWh)", "std": "Standard deviation", "p01": "1% quantile",
          "p05": "5% quantile", "p50": "Median", "p95": "95% quantile", "p99": "99% quantile",
          "negative_share": "Share of negative hours", "acf_1h": "Autocorrelation, 1 hour",
          "acf_24h": "Autocorrelation, 24 hours", "acf_168h": "Autocorrelation, 1 week"}


def year_index(year: int, tz: str) -> pd.DatetimeIndex:
    """Every local hour of a calendar year, as a UTC index (8,760 or 8,784 hours)."""
    idx = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", tz=tz, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #
def fig_profile(history: pd.Series, paths: np.ndarray, tz: str, path: Path) -> Path:
    local = history.index.tz_convert(tz)
    season = np.asarray(local.month.map(SEASONS))
    hour = local.hour.to_numpy()
    sim_mean = paths.mean(axis=0)
    fig, axes = plt.subplots(2, 2, figsize=(10, 6), sharey=True)
    for ax, s in zip(axes.ravel(), ["winter", "spring", "summer", "autumn"], strict=True):
        m = season == s
        hist_profile = pd.Series(history.to_numpy()[m]).groupby(hour[m]).mean()
        sim_profile = pd.Series(sim_mean[m]).groupby(hour[m]).mean()
        ax.plot(hist_profile.index, hist_profile, color=INK, linewidth=2, label="History")
        ax.plot(sim_profile.index, sim_profile, color=BLUE, linewidth=2, linestyle="--",
                label="Model (mean of paths)")
        ax.axhline(0, color=INK_2, linewidth=0.7)
        ax.set_xticks(range(0, 24, 4))
        style(ax, f"{s.title()}: average price by hour", "EUR/MWh")
    axes[0, 0].legend(frameon=False, fontsize=8.5)
    return save(fig, path)


def fig_distribution(history: np.ndarray, paths: np.ndarray, path: Path) -> Path:
    q = np.linspace(0.01, 0.99, 99)
    hist_q = np.quantile(history, q)
    sim_q = np.quantile(paths, q, axis=1)                # quantiles per path
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.fill_between(100 * q, np.percentile(sim_q, 5, axis=1), np.percentile(sim_q, 95, axis=1),
                    color=BLUE, alpha=0.25, linewidth=0, label="Model: 5-95% range across paths")
    ax.plot(100 * q, np.median(sim_q, axis=1), color=BLUE, linewidth=1.8,
            label="Model: median path")
    ax.plot(100 * q, hist_q, color=INK, linewidth=2, label="History")
    ax.axhline(0, color=INK_2, linewidth=0.7)
    ax.set_xlabel("Quantile (%)", color=INK_2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    style(ax, "Price distribution: history vs simulated paths (calibration window)", "EUR/MWh")
    return save(fig, path)


def fig_paths(history: pd.Series, paths: np.ndarray, tz: str, path: Path) -> Path:
    local = history.index.tz_convert(tz)
    june = np.flatnonzero((local.month == 6) & (local.dayofweek == 0))
    start = int(june[-1]) if len(june) else 0                 # last June Monday in the window
    week = slice(start, start + 168)
    x = local[week]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    for i, colour in zip(range(3), ("#86b6ef", "#3987e5", "#1c5cab"), strict=True):
        ax.plot(x, paths[i, week], color=colour, linewidth=1.1, label=f"Simulated path {i + 1}")
    ax.plot(x, history.to_numpy()[week], color=INK, linewidth=2, label="History")
    ax.axhline(0, color=INK_2, linewidth=0.7)
    ax.grid(axis="x", color=GRID, linewidth=0.5)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncols=4)
    style(ax, f"One June week from {x[0]:%d %b %Y}: history and three simulated paths", "EUR/MWh")
    return save(fig, path)


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #
def _validation_table(table: pd.DataFrame) -> str:
    rows = []
    for key, r in table.iterrows():
        fmt = ("{:.1%}" if key == "negative_share"
               else "{:.3f}" if key.startswith("acf") else "{:.1f}")
        low, high = fmt.format(r["simulated_p05"]), fmt.format(r["simulated_p95"])
        rows.append({
            "Statistic": LABELS.get(key, key), "History": fmt.format(r["history"]),
            "Model (mean)": fmt.format(r["simulated_mean"]),
            "Model 5-95% range": f"{low} to {high}",
            "History inside?": "yes" if r["inside_range"] else "no",
        })
    return pd.DataFrame(rows).to_markdown(index=False)


def _capture_teaser(settings: Settings, prices: pd.Series, paths: np.ndarray,
                    tz: str) -> str:
    gen_path = settings.processed_dir / "generation_solar_park.parquet"
    if not gen_path.exists():
        return "No site generation available (run `ppa-lab weather` first): teaser skipped."
    gen = pd.read_parquet(gen_path)["mw"]
    year = max(y for y in range(settings.start.year, settings.end.year + 1)
               if (gen.index.tz_convert(tz).year == y).sum() >= 8760
               and (prices.index.tz_convert(tz).year == y).sum() >= 8760)
    q = gen[gen.index.tz_convert(tz).year == year]
    p = prices.reindex(q.index)
    hist_rate = float((p * q).sum() / q.sum() / p.mean())
    q_arr = q.to_numpy()[: paths.shape[1]]
    sim = paths[:, : len(q_arr)]
    rates = (sim * q_arr).sum(axis=1) / q_arr.sum() / sim.mean(axis=1)
    p5, p50, p95 = np.percentile(rates, [5, 50, 95])
    return (
        f"The solar park's {year} weather year priced with the simulated "
        f"{settings.price_model.delivery_year} paths gives a capture rate of **{p50:.3f}** "
        f"(5-95%: {p5:.3f} to {p95:.3f}). With the real {year} prices it was **{hist_rate:.3f}**. "
        "The model knows the average midday dip, but not that sunny days are cheaper than "
        "cloudy ones: prices and weather are still independent. Step 6 links them."
    )


def hourly_prices(settings: Settings) -> pd.Series:
    """All hourly day-ahead prices (quarter-hours averaged), UTC index."""
    prices = to_hourly(pd.read_parquet(settings.processed_dir / "prices_native.parquet")
                       [["price_eur_mwh"]])
    return prices["price_eur_mwh"].dropna()


def calibration_history(settings: Settings, prices: pd.Series | None = None) -> pd.Series:
    """Hourly prices of the price model's calibration window (local days)."""
    pm = settings.price_model
    prices = hourly_prices(settings) if prices is None else prices
    local_day = prices.index.tz_convert(settings.timezone).normalize().tz_localize(None)
    window = (local_day >= pd.Timestamp(pm.calibration_start)) & (
        local_day <= pd.Timestamp(pm.calibration_end))
    return prices[window]


def write_step05_report(settings: Settings) -> dict[str, Path | None]:
    pm = settings.price_model
    tz = settings.timezone
    proc = settings.processed_dir
    prices = hourly_prices(settings)
    history = calibration_history(settings, prices)

    model = fit(history, tz, pm.scale_eur_mwh)
    model_path = proc / "price_model.json"
    model.save(model_path)

    in_sample = simulate(model, history.index, tz, n_paths=min(pm.n_paths, 200), seed=pm.seed)
    table = compare_with_history(history.to_numpy(), in_sample)

    idx = year_index(pm.delivery_year, tz)
    level = calibrate_level(model, idx, tz, pm.forward_eur_mwh, n_paths=pm.n_paths, seed=pm.seed)
    future = simulate(model, idx, tz, pm.n_paths, annual_level=level, seed=pm.seed,
                      level_volatility=pm.level_volatility)
    annual = future.mean(axis=1)
    a5, a50, a95 = np.percentile(annual, [5, 50, 95])
    q01, q99 = np.quantile(future, [0.01, 0.99])

    fig_dir = settings.reports_dir / "figures"
    figs = {
        "profile": fig_profile(history, in_sample, tz, fig_dir / "step05_profile.png"),
        "distribution": fig_distribution(history.to_numpy(), in_sample,
                                         fig_dir / "step05_distribution.png"),
        "paths": fig_paths(history, in_sample, tz, fig_dir / "step05_paths.png"),
    }
    outside = [LABELS[k] for k, ok in table["inside_range"].items() if not ok]
    sigma = ", ".join(f"{s} {v:.3f}" for s, v in model.sigma.items())
    report = f"""# Step 5 report: stochastic price model

Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `ppa-lab prices`.
Data: {settings.energy_charts.license}. Hourly day-ahead prices (quarter-hours averaged).

## 1. Model and calibration

y = arcsinh(P / {pm.scale_eur_mwh:g}) = monthly level + daily shape (season x day type x hour)
\\+ daily factor D (AR(1) across days) + intraday pattern (whole historical days, same season).

| Item | Value |
|---|---|
| Calibration window | {model.calibration_start} to {model.calibration_end} \
({len(history):,} hours) |
| Daily factor: AR(1) coefficient phi | {model.phi:.3f} per day |
| Daily factor: half-life | {model.half_life_days:.2f} days |
| Daily shock standard deviation by season | {sigma} |
| Historical days in the resampling pool | {len(model.pool_z):,} |
| Saved parameters | `data/processed/{model_path.name}` |

## 2. Validation against history (calibration window, {in_sample.shape[0]} paths)

Same calendar and monthly levels as history; does history fall inside the 5-95% range
of the simulated paths?

{_validation_table(table)}

Outside the range: {", ".join(outside) if outside else "none"}.

## 3. Delivery year {pm.delivery_year}

Forward assumption **{pm.forward_eur_mwh:.1f} EUR/MWh** (illustrative until Step 8), level
uncertainty {pm.level_volatility:.2f} (transformed units), {pm.n_paths} paths.

| Item | Value |
|---|---|
| Average simulated price | {future.mean():.2f} EUR/MWh |
| Annual average per path, 5% / 50% / 95% | {a5:.1f} / {a50:.1f} / {a95:.1f} EUR/MWh |
| Hourly prices, 1% / 99% quantile | {q01:.1f} / {q99:.1f} EUR/MWh |
| Share of negative hours | {(future < 0).mean():.1%} |

## 4. Teaser for Step 6: what solar earns under these prices

{_capture_teaser(settings, prices, future, tz)}

## 5. Charts

![Daily profile](figures/{figs["profile"].name})

![Distribution](figures/{figs["distribution"].name})

![Sample paths](figures/{figs["paths"].name})
"""
    path = settings.reports_dir / "step05_price_model.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report)
    log.info("wrote %s and %s", path, model_path)
    return {"report": path, "model": model_path, **figs}


def load_model(settings: Settings) -> PriceModel:
    """The calibrated model saved by `ppa-lab prices`."""
    return PriceModel.load(settings.processed_dir / "price_model.json")
