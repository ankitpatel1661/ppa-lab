"""Standard German power futures as masks over the delivery hours.

EEX definitions in local time: base = every hour; peak = Monday to Friday 08:00-20:00,
public holidays included. Calendar (year), quarter and month contracts deliver a constant
MW over their hours.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

QUARTERS = [f"Q{q}" for q in range(1, 5)]
MONTHS = [f"M{m:02d}" for m in range(1, 13)]


def product_masks(index: pd.DatetimeIndex, tz: str) -> dict[str, np.ndarray]:
    """Boolean mask over `index` (UTC hours of one delivery year) for every product."""
    local = index.tz_convert(tz)
    masks = {"cal_base": np.ones(len(index), dtype=bool),
             "cal_peak": np.asarray((local.dayofweek < 5) & (local.hour >= 8) & (local.hour < 20))}
    for q, name in enumerate(QUARTERS, start=1):
        masks[name] = np.asarray(local.quarter == q)
    for m, name in enumerate(MONTHS, start=1):
        masks[name] = np.asarray(local.month == m)
    return masks
