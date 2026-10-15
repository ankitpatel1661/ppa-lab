"""Weather pipeline: fetch ERA5 years per site into the raw cache, build hourly generation."""

import dataclasses
from datetime import date

import pandas as pd
import pytest

from conftest import FakeWeatherClient
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather


@pytest.fixture
def weather_settings(settings):
    # Two weather years are enough to exercise the pipeline.
    return dataclasses.replace(settings, weather_first_year=2023, end=date(2024, 12, 31))


def test_fetch_caches_one_file_per_site_and_year(weather_settings):
    store = RawStore(weather_settings.raw_dir, source="open_meteo")
    client = FakeWeatherClient()
    fetch_weather(weather_settings, client, store, today=date(2026, 1, 1))
    for park in weather_settings.parks:
        assert store.months(f"weather_{park.name}") == ["2023", "2024"]
        meta = store.read_meta(f"weather_{park.name}", "2024")
        assert meta["complete"] is True and meta["grid"]["elevation_m"] == 50.0
    calls_first = len(client.calls)
    fetch_weather(weather_settings, client, store, today=date(2026, 1, 1))
    assert len(client.calls) == calls_first  # second run: everything comes from the cache


def test_the_current_year_is_refetched_until_it_is_complete(weather_settings):
    store = RawStore(weather_settings.raw_dir, source="open_meteo")
    client = FakeWeatherClient()
    fetch_weather(weather_settings, client, store, today=date(2024, 12, 20))  # 2024 not over yet
    assert store.read_meta("weather_solar_park", "2024")["complete"] is False
    n = len(client.calls)
    fetch_weather(weather_settings, client, store, today=date(2026, 1, 1))
    assert len(client.calls) == n + len(weather_settings.parks)  # only 2024 again, per site


def test_build_generation_writes_hourly_output_per_park(weather_settings):
    store = RawStore(weather_settings.raw_dir, source="open_meteo")
    fetch_weather(weather_settings, FakeWeatherClient(), store, today=date(2026, 1, 1))
    paths = build_generation(weather_settings, store)

    solar = pd.read_parquet(paths["solar_park"])
    wind = pd.read_parquet(paths["wind_park"])
    for gen in (solar, wind):
        assert gen.index.to_series().diff().dropna().eq(pd.Timedelta(hours=1)).all()
        assert (gen["mw"] >= 0).all() and gen["mw"].notna().all()
    parks = {p.name: p for p in weather_settings.parks}
    solar_park = parks["solar_park"]
    inverter_mw = solar_park.capacity_mw / solar_park.model["dc_ac_ratio"]
    assert solar["mw"].max() <= inverter_mw + 1e-9                     # AC clipping
    assert wind["mw"].max() <= parks["wind_park"].capacity_mw + 1e-9
    local_hour = solar.index.tz_convert("Europe/Berlin").hour
    assert solar["mw"][local_hour == 1].max() == 0.0  # no sun at 01:00 local


def test_build_generation_refuses_weather_with_shifted_timestamps(weather_settings):
    # If radiation were stored one hour late, the sun check must stop the build.
    store = RawStore(weather_settings.raw_dir, source="open_meteo")
    fetch_weather(weather_settings, FakeWeatherClient(), store, today=date(2026, 1, 1))
    for year in ("2023", "2024"):
        meta = store.read_meta("weather_solar_park", year)
        frame = pd.read_parquet(store.path("weather_solar_park", year))
        frame[["ghi_w_m2", "dni_w_m2", "dhi_w_m2"]] = frame[
            ["ghi_w_m2", "dni_w_m2", "dhi_w_m2"]].shift(1).fillna(0.0)
        store.save(frame, "weather_solar_park", year, meta, overwrite=True)
    with pytest.raises(ValueError, match="timestamp"):
        build_generation(weather_settings, store)
