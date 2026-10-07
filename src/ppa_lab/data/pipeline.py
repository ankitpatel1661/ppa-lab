"""Orchestration: download raw months, then build the processed datasets.

Two layers, as in most production data platforms:
- raw:       exactly what the API returned, one file per month (data/raw)
- processed: cleaned, de-duplicated, restricted to the configured range and
             enriched (interval length, hourly views)          (data/processed)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from ppa_lab.config import Settings
from ppa_lab.data.energy_charts import EnergyChartsClient
from ppa_lab.data.store import RawStore
from ppa_lab.timeutils import interval_minutes, local_dates, to_hourly

log = logging.getLogger(__name__)

DATASETS = ("prices", "power")


@dataclass(frozen=True)
class Chunk:
    month: str  # "YYYY-MM"
    start: date
    end: date  # inclusive


@dataclass(frozen=True)
class FetchResult:
    dataset: str
    month: str
    action: str  # "downloaded" | "cached"
    rows: int


def month_chunks(start: date, end: date) -> list[Chunk]:
    """Split an inclusive date range into calendar-month chunks."""
    if start > end:
        raise ValueError(f"start {start} is after end {end}")
    chunks: list[Chunk] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        chunks.append(
            Chunk(
                month=cursor.strftime("%Y-%m"),
                start=max(cursor, start),
                end=min(next_month - timedelta(days=1), end),
            )
        )
        cursor = next_month
    return chunks


def _needs_download(store: RawStore, dataset: str, chunk: Chunk, refresh: bool) -> bool:
    if refresh or not store.exists(dataset, chunk.month):
        return True
    meta = store.read_meta(dataset, chunk.month)
    # Re-download if the cached file covers a different range (e.g. the config's
    # start date moved) or was downloaded before the month was complete.
    same_range = meta.get("start") == chunk.start.isoformat() and meta.get(
        "end"
    ) == chunk.end.isoformat()
    return not (same_range and meta.get("complete", False))


def fetch(
    settings: Settings,
    client: EnergyChartsClient,
    store: RawStore,
    datasets: tuple[str, ...] = DATASETS,
    refresh: bool = False,
    today: date | None = None,
) -> list[FetchResult]:
    """Download every month of every dataset that is not cached yet."""
    tz = ZoneInfo(settings.timezone)
    today = today or datetime.now(tz).date()
    results: list[FetchResult] = []

    for dataset in datasets:
        if dataset not in DATASETS:
            raise ValueError(f"Unknown dataset {dataset!r}; choose from {DATASETS}")
        for chunk in month_chunks(settings.start, settings.end):
            if not _needs_download(store, dataset, chunk, refresh):
                rows = store.read_meta(dataset, chunk.month)["rows"]
                results.append(FetchResult(dataset, chunk.month, "cached", rows))
                continue

            if dataset == "prices":
                frame = client.day_ahead_prices(settings.bidding_zone, chunk.start, chunk.end)
                endpoint = "price"
                params = {"bzn": settings.bidding_zone}
            else:
                frame = client.public_power(settings.country, chunk.start, chunk.end)
                endpoint = "public_power"
                params = {"country": settings.country}

            meta = {
                "source_url": f"{client.base_url}/{endpoint}",
                "params": {
                    **params, "start": chunk.start.isoformat(), "end": chunk.end.isoformat()
                },
                "start": chunk.start.isoformat(),
                "end": chunk.end.isoformat(),
                # A month is only final once its last delivery day lies in the past.
                "complete": chunk.end < today,
                "license": settings.energy_charts.license,
            }
            store.save(frame, dataset, chunk.month, meta, overwrite=True)
            log.info("%-6s %s  downloaded %6d rows", dataset, chunk.month, len(frame))
            results.append(FetchResult(dataset, chunk.month, "downloaded", len(frame)))
            client.sleep(settings.energy_charts.pause_s)
    return results


def _clean(frame: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """Sort, drop duplicate timestamps and restrict to the configured delivery days."""
    frame = frame.sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    days = local_dates(frame.index, settings.timezone)
    mask = (days >= settings.start) & (days <= settings.end)
    return frame[mask]


def build_processed(settings: Settings, store: RawStore) -> dict[str, Path]:
    """Create the processed Parquet files used by all later analysis."""
    out = settings.processed_dir
    out.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    prices = _clean(store.load("prices"), settings)
    prices["interval_min"] = interval_minutes(prices.index)
    written["prices_native"] = out / "prices_native.parquet"
    prices.to_parquet(written["prices_native"])

    hourly = to_hourly(prices[["price_eur_mwh"]])
    hourly["n_intervals"] = prices["price_eur_mwh"].resample("1h").count()
    written["prices_hourly"] = out / "prices_hourly.parquet"
    hourly.to_parquet(written["prices_hourly"])

    power = _clean(store.load("power"), settings)
    written["power_15min"] = out / "power_15min.parquet"
    power.to_parquet(written["power_15min"])
    # Mean MW over one hour equals MWh produced in that hour.
    written["power_hourly"] = out / "power_hourly.parquet"
    to_hourly(power).to_parquet(written["power_hourly"])

    for name, path in written.items():
        log.info("wrote %-14s %s", name, path)
    return written
