"""Solar and storage build-out after the delivery year (PPA-8f)."""

import dataclasses
from datetime import date

import numpy as np
import pandas as pd
import pytest

from conftest import make_power_frame
from ppa_lab.analysis.step07_report import buildout_paths
from ppa_lab.config import BuildoutScenario, BuildoutSettings
from ppa_lab.scenarios.buildout import (
    Calibration,
    calibrate,
    capture_rate_factors,
    seasonal_amplification,
    share_growth,
)

TZ = "Europe/Berlin"


def power_frame(solar_by_year: dict[int, float], summer_weight: float = 1.0) -> pd.DataFrame:
    """Hourly solar and load; solar at a constant MW per year, `summer_weight` times as much
    from April to September."""
    idx = pd.date_range("2022-01-01", "2026-01-01", freq="1h", tz=TZ, inclusive="left")
    summer = np.isin(idx.month, range(4, 10))
    level = np.array([solar_by_year[y] for y in idx.year])
    solar = level * np.where(summer, summer_weight, 1.0)
    return pd.DataFrame({"solar_mw": solar, "load_mw": 100.0}, index=idx.tz_convert("UTC"))


def test_kappa_and_lambda_from_history_and_assumptions():
    power = power_frame({2022: 10.0, 2023: 12.0, 2024: 14.0, 2025: 16.0})
    cal = calibrate(power, TZ, 2022, 2025, [2.0, 2.0, 2.0], cycles=250, solar_fraction=0.8,
                    gamma=-5.0, gamma_se=0.8)
    assert cal.share_start == pytest.approx(0.10) and cal.share_end == pytest.approx(0.16)
    assert cal.kappa == pytest.approx(0.06 / 6.0)                  # per GW added
    assert cal.load_twh == pytest.approx(0.876)                   # 100 MW for a year
    assert cal.lam == pytest.approx(250 * 0.8 / 876.0)            # per GWh of storage
    assert cal.amplification == pytest.approx(1.0)                # flat solar: no seasonality
    with pytest.raises(ValueError, match="one addition per year"):
        calibrate(power, TZ, 2022, 2025, [2.0], 250, 0.8, -5.0, 0.8)


def test_seasonal_solar_amplifies_the_share_effect():
    assert seasonal_amplification(power_frame({y: 10.0 for y in range(2022, 2026)}, 3.0),
                                  TZ, 2025) > 1.2


def test_storage_beyond_historys_pace_slows_the_share_and_the_capture_rate_falls():
    cal = Calibration(kappa=0.001, lam=0.0004, amplification=1.5, gamma=-5.0, gamma_se=0.8,
                      load_twh=466.0, share_start=0.11, share_end=0.15)
    assert share_growth(cal, 17.0, 6.5, 6.5) == pytest.approx(0.017)
    assert share_growth(cal, 17.0, 12.5, 6.5) == pytest.approx(0.017 - 0.0024)
    f = capture_rate_factors(cal, 0.01, 2027, 3)
    assert f[2027] == 1.0
    assert f[2029] == pytest.approx(np.exp(-5.0 * 1.5 * 0.02))
    flat = capture_rate_factors(cal, 0.0, 2027, 3)
    assert set(flat.values()) == {1.0}


def write_market_with_growing_solar(settings) -> None:
    """Two years of hourly prices and power: solar grows 30% from 2024 to 2025 and pushes
    midday prices down, so the capture rate falls with solar's share of load."""
    power = make_power_frame(date(2024, 1, 1), date(2025, 12, 31))
    local = power.index.tz_convert(TZ)
    season = 0.6 + 0.4 * np.sin(2 * np.pi * (local.month - 3.5) / 12)
    power["solar_mw"] *= season * np.where(local.year == 2025, 1.3, 1.0)
    hourly = power.iloc[::4]
    level = 100.0 + 15.0 * np.random.default_rng(1).standard_normal(24)
    month = (hourly.index.tz_convert(TZ).year - 2024) * 12 + hourly.index.tz_convert(TZ).month - 1
    price = level[month] - 60.0 * hourly["solar_mw"] / hourly["load_mw"]
    prices = pd.DataFrame({"price_eur_mwh": price.to_numpy(), "interval_min": 60.0},
                          index=hourly.index)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(settings.processed_dir / "prices_native.parquet")
    power.to_parquet(settings.processed_dir / "power_15min.parquet")


def buildout_settings(settings):
    bo = BuildoutSettings(
        history_first_year=2024, history_last_year=2025, history_pv_additions_gw=(10.0,),
        history_storage_additions_gwh=5.0, storage_cycles_per_year=250,
        storage_solar_fraction=0.8, regression_start_year=2024, base_scenario="central",
        scenarios={"central": BuildoutScenario("Central", 10.0, 5.0),
                   "storage": BuildoutScenario("Storage", 10.0, 50.0)})
    return dataclasses.replace(settings, start=date(2024, 1, 1), end=date(2025, 12, 31),
                               buildout=bo)


def test_buildout_paths_calibrate_on_the_processed_data(settings):
    s = buildout_settings(settings)
    write_market_with_growing_solar(s)
    paths = buildout_paths(s, 2026, 4)
    cal = paths["calibration"]
    assert cal["kappa"] == pytest.approx((cal["share_end"] - cal["share_start"]) / 10.0)
    assert paths["regression"]["share_coef"] < 0       # more solar, lower capture rate
    central, storage = paths["scenarios"]["central"], paths["scenarios"]["storage"]
    assert central["share_growth"] == pytest.approx(10.0 * cal["kappa"])   # history's storage
    assert list(central["factors"]) == [2026, 2027, 2028, 2029]
    assert central["factors"][2029] == pytest.approx(central["factor_per_year"] ** 3)
    assert central["factors"][2029] < 1.0                # the share keeps growing
    assert storage["factors"][2029] > central["factors"][2029]   # storage slows the fall
    assert buildout_paths(dataclasses.replace(s, buildout=None), 2026, 4) is None
