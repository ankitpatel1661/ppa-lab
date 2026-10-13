"""Weather pipeline: ERA5 years per site into the raw cache, then hourly park generation.

Raw layer:       data/raw/open_meteo/weather_<park>/<YYYY>.parquet (+ manifest), exactly
                 as the API labels it (radiation at the end of its hour).
Processed layer: data/processed/weather_<park>.parquet    interval-beginning weather
                 data/processed/generation_<park>.parquet column `mw` (MWh per hour)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from ppa_lab.config import Park, Settings
from ppa_lab.data.open_meteo import radiation_timing_offset, to_interval_beginning
from ppa_lab.data.pipeline import FetchResult
from ppa_lab.data.store import RawStore
from ppa_lab.weather.pv import solar_power_mw
from ppa_lab.weather.wind import wind_power_mw

log = logging.getLogger(__name__)

# ERA5 is published with a delay of about five days; a year is final after that.
ERA5_LATENCY = timedelta(days=6)


def sited_parks(settings: Settings) -> list[Park]:
    """Parks with a location, i.e. those a site model can be run for."""
    return [p for p in settings.parks if p.latitude is not None and p.longitude is not None]


def weather_dataset(park: Park) -> str:
    return f"weather_{park.name}"


def fetch_weather(settings: Settings, client, store: RawStore, refresh: bool = False,
                  today: date | None = None) -> list[FetchResult]:
    """Download every (site, year) that is not cached as complete yet."""
    today = today or date.today()
    results: list[FetchResult] = []
    for park in sited_parks(settings):
        dataset = weather_dataset(park)
        for year in range(settings.weather_first_year, settings.end.year + 1):
            start, end = date(year, 1, 1), min(date(year, 12, 31), settings.end)
            key = str(year)
            if not refresh and store.exists(dataset, key):
                meta = store.read_meta(dataset, key)
                same = (meta.get("end") == end.isoformat()
                        and meta.get("params", {}).get("latitude") == park.latitude
                        and meta.get("params", {}).get("longitude") == park.longitude)
                if same and meta.get("complete", False):
                    results.append(FetchResult(dataset, key, "cached", meta["rows"]))
                    continue
            frame, grid = client.hourly(park.latitude, park.longitude, start, end)
            meta = {
                "source_url": f"{client.base_url}/archive",
                "params": {"latitude": park.latitude, "longitude": park.longitude,
                           "start_date": start.isoformat(), "end_date": end.isoformat(),
                           "models": "era5", "timezone": "GMT", "wind_speed_unit": "ms"},
                "start": start.isoformat(),
                "end": end.isoformat(),
                "grid": grid,
                "complete": end + ERA5_LATENCY < today,
                "license": settings.weather_license,
            }
            store.save(frame, dataset, key, meta, overwrite=True)
            log.info("%-22s %s downloaded %5d rows", dataset, key, len(frame))
            results.append(FetchResult(dataset, key, "downloaded", len(frame)))
            client.sleep(settings.weather_pause_s)
    return results


def park_output_mw(park: Park, weather: pd.DataFrame) -> pd.Series:
    """Hourly park output (MW = MWh per hour) from interval-beginning weather."""
    if park.technology == "solar":
        # Fail loudly if the radiation timestamps are not where we think they are:
        # one year of data must line up with the sun at mid-interval.
        sample = weather.iloc[-8760:]
        offset = radiation_timing_offset(sample, park.latitude, park.longitude)
        if offset != 30:
            raise ValueError(f"{park.name}: radiation timestamp check failed (best match at "
                             f"{offset:+d} min instead of +30); is the data shifted by an hour?")
        return solar_power_mw(weather, park.latitude, park.longitude, park.capacity_mw,
                              **park.model)
    if park.technology.startswith("wind"):
        return wind_power_mw(weather, park.capacity_mw, **park.model)
    raise ValueError(f"no site model for technology {park.technology!r}")


def build_generation(settings: Settings, store: RawStore) -> dict[str, Path]:
    """Processed weather and generation per park; returns the generation file paths."""
    out = settings.processed_dir
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for park in sited_parks(settings):
        raw = store.load(weather_dataset(park))
        raw = raw[~raw.index.duplicated(keep="last")]
        weather = to_interval_beginning(raw)
        weather.to_parquet(out / f"weather_{park.name}.parquet")
        generation = pd.DataFrame({"mw": park_output_mw(park, weather)})
        written[park.name] = out / f"generation_{park.name}.parquet"
        generation.to_parquet(written[park.name])
        log.info("wrote %s (%d hours)", written[park.name], len(generation))
    return written
