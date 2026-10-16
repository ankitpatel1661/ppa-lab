"""Does a capture rate move with the price level? The regression behind PPA-8d."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.analysis.level_effect import level_regression, monthly_panel, share_pace

TZ = "Europe/Berlin"


def synthetic_panel(slope: float, n_years: int = 6, seed: int = 0) -> pd.DataFrame:
    """Months with a seasonal pattern, a level that varies, and build-out that lowers the rate."""
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2021-01", periods=12 * n_years, freq="M")
    base = np.exp(rng.normal(np.log(100), 0.35, len(idx)))
    share = np.linspace(0.08, 0.20, len(idx)) + 0.03 * np.sin(2 * np.pi * idx.month / 12)
    season = 0.05 * np.cos(2 * np.pi * idx.month / 12)
    rate = 0.9 + season + slope * np.log(base) - 3.0 * share + rng.normal(0, 0.005, len(idx))
    return pd.DataFrame({"base": base, "capture_rate_solar": rate, "share_solar": share}, index=idx)


def test_the_regression_recovers_a_known_level_effect_and_build_out():
    r = level_regression(synthetic_panel(slope=0.25), "solar")
    assert r["coef"] == pytest.approx(0.25, abs=0.02)
    assert r["share_coef"] == pytest.approx(-3.0, abs=0.3)
    assert r["ci_low"] < 0.25 < r["ci_high"] and r["t"] > 10 and r["n"] == 72


def test_no_level_effect_is_not_mistaken_for_one():
    r = level_regression(synthetic_panel(slope=0.0, seed=3), "solar")
    assert r["ci_low"] < 0.0 < r["ci_high"]


def test_the_sample_can_start_later():
    r = level_regression(synthetic_panel(slope=0.25), "solar", start_year=2023)
    assert r["n"] == 48


def test_monthly_panel_measures_capture_rate_and_share():
    idx = pd.date_range("2025-01-01", "2025-03-01", freq="h", tz=TZ, inclusive="left")
    hour = idx.hour.to_numpy()
    midday = (hour >= 10) & (hour < 14)
    price = pd.Series(np.where(midday, 50.0, 100.0), index=idx.tz_convert("UTC"))
    solar = np.where((hour >= 10) & (hour < 14), 20.0, 0.0)
    power = pd.DataFrame({"solar_mw": solar, "load_mw": 100.0}, index=idx.tz_convert("UTC"))
    panel = monthly_panel(price, power, TZ, {"solar": "solar_mw"})
    assert list(panel.index.astype(str)) == ["2025-01", "2025-02"]
    base = (50 * 4 + 100 * 20) / 24
    assert panel["capture_rate_solar"].iloc[0] == pytest.approx(50 / base)
    assert panel["share_solar"].iloc[0] == pytest.approx(20 * 4 / (100 * 24))


def test_no_answer_when_the_data_cannot_separate_the_effects():
    panel = synthetic_panel(slope=0.25)
    assert level_regression(panel.assign(share_solar=0.1), "solar") is None      # share fixed
    assert level_regression(panel.iloc[:14], "solar") is None                    # 14 months


def test_share_pace_uses_complete_years():
    idx = pd.date_range("2022-01-01", "2025-07-01", freq="h", tz=TZ, inclusive="left")
    solar = np.select([idx.year == 2022, idx.year == 2023, idx.year == 2024], [10.0, 12.0, 14.0],
                      default=40.0)                         # 2025 is incomplete: ignored
    power = pd.DataFrame({"solar_mw": solar, "load_mw": 100.0}, index=idx.tz_convert("UTC"))
    pace = share_pace(power, TZ, "solar_mw", first_year=2023)
    assert pace["from"] == 2022 and pace["to"] == 2024
    assert pace["per_year"] == pytest.approx(0.02)
    assert share_pace(power, TZ, "solar_mw", first_year=2022) is None     # no 2021


def test_the_log_form_recovers_a_proportional_share_effect():
    panel = synthetic_panel(slope=0.0)
    share = panel["share_solar"].to_numpy()
    rate = 0.8 * np.exp(-5.0 * share + 0.003 * np.sin(np.arange(len(share))))
    r = level_regression(panel.assign(capture_rate_solar=rate), "solar", log=True)
    assert r["share_coef"] == pytest.approx(-5.0, abs=0.2) and r["share_se"] > 0
