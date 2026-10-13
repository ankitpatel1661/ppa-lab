"""Does the price model behave like history? Statistics of simulated vs observed prices."""

from __future__ import annotations

import numpy as np
import pandas as pd

QUANTILES = {"p01": 0.01, "p05": 0.05, "p50": 0.50, "p95": 0.95, "p99": 0.99}
LAGS = (1, 24, 168)


def price_statistics(prices: np.ndarray) -> dict[str, float]:
    """Mean, spread, quantiles and share of negative prices of one price series."""
    p = np.asarray(prices, dtype="float64")
    stats = {"mean": float(p.mean()), "std": float(p.std())}
    stats.update({k: float(np.quantile(p, q)) for k, q in QUANTILES.items()})
    stats["negative_share"] = float((p < 0).mean())
    return stats


def autocorrelation(paths: np.ndarray, lags: tuple[int, ...] = LAGS) -> dict[int, float]:
    """Autocorrelation at the given lags, averaged over paths (rows)."""
    x = np.asarray(paths, dtype="float64")
    x = x - x.mean(axis=1, keepdims=True)
    denom = (x * x).sum(axis=1)
    return {k: float(np.mean((x[:, k:] * x[:, :-k]).sum(axis=1) / denom)) for k in lags}


def compare_with_history(history: np.ndarray, paths: np.ndarray) -> pd.DataFrame:
    """History vs simulation: the statistic for history, the mean over simulated paths,
    and the 5-95% range across paths (does history fall inside?)."""
    hist = price_statistics(history)
    hist.update({f"acf_{k}h": v for k, v in autocorrelation(np.asarray(history)[None, :]).items()})
    per_path = pd.DataFrame([price_statistics(row) for row in paths])
    acf = {f"acf_{k}h": [autocorrelation(row[None, :])[k] for row in paths] for k in LAGS}
    per_path = per_path.assign(**acf)
    table = pd.DataFrame({
        "history": pd.Series(hist),
        "simulated_mean": per_path.mean(),
        "simulated_p05": per_path.quantile(0.05),
        "simulated_p95": per_path.quantile(0.95),
    })
    table["inside_range"] = (table["history"] >= table["simulated_p05"]) & (
        table["history"] <= table["simulated_p95"])
    return table
