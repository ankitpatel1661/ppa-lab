"""Out-of-sample test of the joint price model: a year the model has never seen.

The model and the weather link are fitted on the days BEFORE the test period only (analog
days from its last `pool_months`, as in production). The test period is then simulated
with its real weather, and each local quarter's level is set to the quarter's realised
average price: the forward's job, done perfectly. So the test asks what the model adds
beyond the forward: the shape, the tails, the dynamics and the capture rates.

With `seen=True` the model is fitted on the test period too and its analog days come from
the test period (at least `exclude_days` from the simulated day): what is left of the error
then lies in the model's structure, and the difference to the out-of-sample error is what
one year of change (solar build-out) does.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from ppa_lab.prices.model import fit, inverse, seasonal_mean, solve_level
from ppa_lab.prices.validation import compare_with_history
from ppa_lab.scenarios.link import fit_link, linked_residuals, restrict_pool


def _local_days(index: pd.DatetimeIndex, tz: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(index.tz_convert(tz).normalize().tz_localize(None))


def park_statistics(prices: np.ndarray, volumes: np.ndarray) -> dict[str, np.ndarray]:
    """Per row of `prices` (paths x hours): a park's capture rate and the share of its
    output in hours with negative prices."""
    p = np.atleast_2d(prices)
    q = np.asarray(volumes, dtype="float64")
    return {"capture_rate": (p * q).sum(axis=1) / q.sum() / p.mean(axis=1),
            "negative_output_share": ((p < 0) * q).sum(axis=1) / q.sum()}


def out_of_sample(prices: pd.Series, features: pd.DataFrame, generation: dict[str, pd.Series],
                  climatology: pd.DataFrame, tz: str, scale: float, train_start: date,
                  test_start: date, test_end: date, window_days: int, k: int,
                  pool_months: int = 12, n_paths: int = 200, seed: int = 0,
                  negative_scale: float | None = None, seen: bool = False,
                  exclude_days: int = 7) -> dict:
    """Fit on [train_start, test_start), simulate [test_start, test_end] (local days).

    `prices`: hourly, UTC; `generation`: park -> hourly MW (UTC), the parks' output in the
    real weather. Returns the statistics table of `compare_with_history`, per park the
    history and the simulated 5/50/95% of the capture rate and of the output share at
    negative prices, and the simulated paths.
    """
    prices = prices.dropna()
    day = _local_days(prices.index, tz)
    train = prices[(day >= pd.Timestamp(train_start)) & (day < pd.Timestamp(test_start))]
    test = prices[(day >= pd.Timestamp(test_start)) & (day <= pd.Timestamp(test_end))]

    known = pd.concat([train, test]) if seen else train
    model = fit(known, tz, scale, negative_scale)
    link = fit_link(model, known, features, climatology, tz, window_days, k)
    pool_start = pd.Timestamp(test_start)
    if not seen:
        pool_start -= pd.DateOffset(months=pool_months)
    link = restrict_pool(link, pool_start)

    index = test.index
    weather = features.reindex(pd.DatetimeIndex(sorted(set(_local_days(index, tz)))))
    x = linked_residuals(model, link, index, tz, weather, n_paths, seed,
                         exclude_days=exclude_days if seen else None)
    mu0 = seasonal_mean(model, index, tz, annual_level=0.0)
    quarter = index.tz_convert(tz).quarter.to_numpy()
    level = np.zeros(len(index))
    for q in np.unique(quarter):
        hours = quarter == q
        level[hours] = solve_level(mu0[hours], x[:, hours], scale, float(test[hours].mean()),
                                   negative_scale)
    paths = inverse(mu0[None, :] + level + x, scale, negative_scale)

    observed = test.to_numpy()
    parks = {}
    for park, mw in generation.items():
        q = mw.reindex(index).to_numpy()
        if np.isnan(q).any():
            raise ValueError(f"generation of {park} missing in the test period")
        hist = {key: float(v[0]) for key, v in park_statistics(observed, q).items()}
        sim = park_statistics(paths, q)
        parks[park] = {key: {"history": hist[key],
                             **dict(zip(("p05", "p50", "p95"),
                                        np.percentile(v, [5, 50, 95]).tolist(), strict=True))}
                       for key, v in sim.items()}
    return {"train": (str(train_start), str(test_start)), "test": (str(test_start), str(test_end)),
            "statistics": compare_with_history(observed, paths), "parks": parks,
            "paths": paths, "index": index, "pool_days": len(link.pool_days)}
