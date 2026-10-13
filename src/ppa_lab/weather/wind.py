"""Wind park model with windpowerlib: ERA5 wind at 10 m and 100 m -> park output in MW.

1. Shear: the power-law exponent alpha from the two heights, hour by hour,
   alpha = ln(v100 / v10) / ln(100 / 10), clipped to [0, 0.6] (no downward
   extrapolation; calm 10 m values cannot explode it).
2. Hub-height speed: v_hub = v100 * (hub_height / 100) ** alpha.
3. Turbine power curve from windpowerlib's turbine library (no air-density correction),
   scaled to the park capacity, then wake, availability and electrical losses.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

MAX_SHEAR = 0.6


def shear_exponent(v10: np.ndarray, v100: np.ndarray) -> np.ndarray:
    """Power-law shear exponent between 10 m and 100 m, clipped to [0, MAX_SHEAR]."""
    with np.errstate(divide="ignore", invalid="ignore"):
        alpha = np.log(np.asarray(v100, dtype="float64") / np.asarray(v10, dtype="float64"))
    alpha = alpha / np.log(10.0)
    return np.clip(np.nan_to_num(alpha, nan=0.0, posinf=MAX_SHEAR, neginf=0.0), 0.0, MAX_SHEAR)


def hub_height_speed(v10: np.ndarray, v100: np.ndarray, hub_height_m: float) -> np.ndarray:
    """Wind speed at hub height from the 100 m speed and the measured shear."""
    return np.asarray(v100, dtype="float64") * (hub_height_m / 100.0) ** shear_exponent(v10, v100)


@lru_cache(maxsize=8)
def _power_curve(turbine_type: str) -> tuple[np.ndarray, np.ndarray, float]:
    from windpowerlib import WindTurbine  # heavy import, load lazily

    turbine = WindTurbine(turbine_type=turbine_type, hub_height=100)
    if turbine.power_curve is None:
        raise ValueError(f"turbine {turbine_type!r} has no power curve in windpowerlib's library")
    curve = turbine.power_curve
    return curve["wind_speed"].to_numpy(), curve["value"].to_numpy(), float(turbine.nominal_power)


def wind_power_mw(
    weather: pd.DataFrame,
    capacity_mw: float,
    turbine_type: str,
    hub_height_m: float,
    losses_pct: float,
) -> pd.Series:
    """Hourly park output (MW) from interval-beginning wind at 10 m and 100 m."""
    from windpowerlib.power_output import power_curve

    speeds, values, nominal = _power_curve(turbine_type)
    v_hub = hub_height_speed(weather["wind_speed_10m_ms"].to_numpy(),
                             weather["wind_speed_100m_ms"].to_numpy(), hub_height_m)
    turbine_w = np.asarray(power_curve(pd.Series(v_hub), speeds, values), dtype="float64")
    park = capacity_mw * turbine_w / nominal * (1.0 - losses_pct / 100.0)
    return pd.Series(park, index=weather.index, name="wind_mw")
