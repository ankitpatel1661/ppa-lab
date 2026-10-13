"""Solar park model with pvlib: hourly ERA5 weather -> AC output in MW.

Chain (one row = one hour, interval beginning, so the sun is placed at mid-interval):
  sun position -> plane-of-array irradiance (Hay-Davies transposition)
  -> cell temperature (Faiman) -> DC power (PVWatts, -0.35 %/K)
  -> system losses (soiling, mismatch, wiring, availability) -> inverter (PVWatts, 96 %)
  clipped at the AC capacity = DC capacity / DC-AC ratio.

`capacity_mw` is the DC (peak) capacity in MWp. The hourly mean MW equals MWh per hour.
"""

from __future__ import annotations

import pandas as pd
import pvlib

INVERTER_EFFICIENCY = 0.96
TEMPERATURE_COEFFICIENT = -0.0035  # per kelvin, typical crystalline silicon


def solar_power_mw(
    weather: pd.DataFrame,
    latitude: float,
    longitude: float,
    capacity_mw: float,
    tilt_deg: float = 25.0,
    azimuth_deg: float = 180.0,
    dc_ac_ratio: float = 1.2,
    losses_pct: float = 10.0,
    altitude_m: float = 0.0,
) -> pd.Series:
    """Hourly AC output (MW) of a fixed-tilt PV park from interval-beginning weather.

    Needs columns ghi_w_m2, dni_w_m2, dhi_w_m2, temp_air_c, wind_speed_10m_ms.
    """
    mid = weather.index + pd.Timedelta(minutes=30)
    sun = pvlib.solarposition.get_solarposition(mid, latitude, longitude, altitude=altitude_m)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt_deg,
        surface_azimuth=azimuth_deg,
        solar_zenith=sun["apparent_zenith"].to_numpy(),
        solar_azimuth=sun["azimuth"].to_numpy(),
        dni=weather["dni_w_m2"].clip(lower=0).to_numpy(),
        ghi=weather["ghi_w_m2"].clip(lower=0).to_numpy(),
        dhi=weather["dhi_w_m2"].clip(lower=0).to_numpy(),
        dni_extra=pvlib.irradiance.get_extra_radiation(mid).to_numpy(),
        model="haydavies",
    )
    poa_global = pd.Series(poa["poa_global"], index=weather.index).fillna(0.0).clip(lower=0)
    cell_temp = pvlib.temperature.faiman(
        poa_global, weather["temp_air_c"], weather["wind_speed_10m_ms"]
    )
    dc = pvlib.pvsystem.pvwatts_dc(poa_global, cell_temp, pdc0=capacity_mw,
                                   gamma_pdc=TEMPERATURE_COEFFICIENT)
    dc = dc * (1.0 - losses_pct / 100.0)
    ac_capacity = capacity_mw / dc_ac_ratio
    ac = pvlib.inverter.pvwatts(dc, pdc0=ac_capacity / INVERTER_EFFICIENCY,
                                eta_inv_nom=INVERTER_EFFICIENCY)
    return pd.Series(ac, index=weather.index, name="solar_mw").fillna(0.0).clip(0.0, ac_capacity)
