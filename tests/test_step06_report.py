"""End-to-end: weather + prices -> weather-price link -> joint scenarios -> Step 6 report."""

import dataclasses
from datetime import date

import pandas as pd

from conftest import FakeWeatherClient, write_synthetic_market
from ppa_lab.analysis.step06_report import write_step06_report
from ppa_lab.config import PriceModelSettings, ScenarioSettings
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather


def small_settings(settings):
    pm = PriceModelSettings(calibration_start=date(2024, 1, 1), calibration_end=date(2025, 12, 31),
                            scale_eur_mwh=80.0, n_paths=20, seed=1, delivery_year=2026,
                            forward_eur_mwh=85.0, level_volatility=0.15)
    sc = ScenarioSettings(weather_last_year=2025, paths_per_weather_year=3, analog_window_days=30,
                          analog_k=5, validation_exclusion_days=7, seed=2)
    return dataclasses.replace(settings, start=date(2024, 1, 1), end=date(2025, 12, 31),
                               weather_first_year=2024, price_model=pm, scenarios=sc)


def test_step06_report_end_to_end(settings):
    s = small_settings(settings)
    store = RawStore(s.raw_dir, source="open_meteo")
    fetch_weather(s, FakeWeatherClient(), store, today=date(2026, 6, 1))
    build_generation(s, store)
    write_synthetic_market(s)

    out = write_step06_report(s)

    text = out["report"].read_text()
    assert "weather-price link" in text.lower() and "Validation" in text
    assert "2026" in text and "6 scenarios" in text           # 2 weather years x 3 paths
    for key in ("capture_rates", "link", "convergence"):
        assert out[key].exists()
    table = pd.read_parquet(out["scenarios"])
    assert len(table) == 2 * 6                                 # linked and independent
    assert set(table["prices"]) == {"linked", "independent"}
    assert {"solar_park_capture_rate", "wind_park_revenue_eur"} <= set(table.columns)


def test_step06_report_explains_missing_weather(settings):
    s = small_settings(settings)
    write_synthetic_market(s)                                  # prices only, no Step 4 output

    out = write_step06_report(s)

    assert "run `ppa-lab weather` first" in out["report"].read_text()
    assert out["scenarios"] is None


def test_pool_start_options_cover_window_latest_year_and_last_twelve_months():
    from ppa_lab.analysis.step06_report import pool_start_options
    opts = pool_start_options(date(2024, 1, 1), date(2026, 9, 30))
    assert [d for _, d in opts] == [pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01"),
                                   pd.Timestamp("2025-10-01")]
    opts = pool_start_options(date(2024, 1, 1), date(2025, 12, 31))
    assert [d for _, d in opts] == [pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")]
