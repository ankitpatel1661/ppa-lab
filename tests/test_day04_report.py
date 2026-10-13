"""End-to-end: weather years -> generation -> Day 4 report (synthetic weather and market)."""

import dataclasses
from datetime import date

from conftest import FakeWeatherClient, write_synthetic_market
from ppa_lab.analysis.day04_report import write_day04_report
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather


def test_day04_report_end_to_end(settings):
    s = dataclasses.replace(settings, start=date(2024, 1, 1), end=date(2025, 12, 31),
                            weather_first_year=2024)
    store = RawStore(s.raw_dir, source="open_meteo")
    fetch_weather(s, FakeWeatherClient(), store, today=date(2026, 6, 1))
    build_generation(s, store)
    write_synthetic_market(s)

    out = write_day04_report(s)

    text = out["report"].read_text()
    assert "P50" in text and "P90" in text
    assert "Lusatia" in text and "North Frisia" in text
    assert out["annual"].exists() and out["monthly"].exists()
    checks = text.split("## 3.")[1].split("## 4.")[0]
    assert "2024" in checks and "2025" in checks  # both complete overlap years are checked


def test_day04_report_copes_without_complete_weather_years(settings):
    s = dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1),
                            weather_first_year=2025)
    store = RawStore(s.raw_dir, source="open_meteo")
    fetch_weather(s, FakeWeatherClient(), store, today=date(2026, 6, 1))
    build_generation(s, store)
    write_synthetic_market(s)

    out = write_day04_report(s)

    assert "No complete weather year" in out["report"].read_text()
    assert out["annual"] is None
