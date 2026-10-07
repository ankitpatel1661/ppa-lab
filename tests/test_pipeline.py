import dataclasses
from datetime import date

import pandas as pd
import pytest

from conftest import FakeClient
from ppa_lab.data.pipeline import Chunk, build_processed, fetch, month_chunks
from ppa_lab.data.store import RawStore


def test_month_chunks_split_on_calendar_months_including_leap_february():
    chunks = month_chunks(date(2024, 1, 15), date(2024, 3, 10))
    assert chunks == [
        Chunk("2024-01", date(2024, 1, 15), date(2024, 1, 31)),
        Chunk("2024-02", date(2024, 2, 1), date(2024, 2, 29)),
        Chunk("2024-03", date(2024, 3, 1), date(2024, 3, 10)),
    ]


def test_month_chunks_reject_inverted_range():
    with pytest.raises(ValueError):
        month_chunks(date(2025, 2, 1), date(2025, 1, 1))


@pytest.fixture
def small_settings(settings):
    """Two delivery days spanning the 15-minute switch: 30 Sep and 1 Oct 2025."""
    return dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1))


def test_fetch_downloads_once_then_uses_cache(small_settings):
    store, client = RawStore(small_settings.raw_dir), FakeClient()

    first = fetch(small_settings, client, store, today=date(2026, 1, 1))
    assert {(r.dataset, r.month, r.action) for r in first} == {
        ("prices", "2025-09", "downloaded"), ("prices", "2025-10", "downloaded"),
        ("power", "2025-09", "downloaded"), ("power", "2025-10", "downloaded"),
    }
    second = fetch(small_settings, client, store, today=date(2026, 1, 1))
    assert {r.action for r in second} == {"cached"}
    assert len(client.calls) == 4  # no extra API calls on the second run

    meta = store.read_meta("prices", "2025-10")
    assert meta["params"] == {"bzn": "DE-LU", "start": "2025-10-01", "end": "2025-10-01"}
    assert meta["complete"] is True


def test_incomplete_months_are_downloaded_again(small_settings):
    store, client = RawStore(small_settings.raw_dir), FakeClient()
    # "today" is inside the range, so the October file is provisional.
    fetch(small_settings, client, store, datasets=("prices",), today=date(2025, 10, 1))
    again = fetch(small_settings, client, store, datasets=("prices",), today=date(2025, 10, 2))
    actions = {r.month: r.action for r in again}
    assert actions == {"2025-09": "cached", "2025-10": "downloaded"}


def test_build_processed_creates_native_and_hourly_views(small_settings):
    store = RawStore(small_settings.raw_dir)
    fetch(small_settings, FakeClient(), store, today=date(2026, 1, 1))
    paths = build_processed(small_settings, store)

    native = pd.read_parquet(paths["prices_native"])
    assert len(native) == 24 + 96
    assert native["interval_min"].value_counts().to_dict() == {15.0: 96, 60.0: 24}

    hourly = pd.read_parquet(paths["prices_hourly"])
    assert len(hourly) == 48
    assert hourly["n_intervals"].value_counts().to_dict() == {1: 24, 4: 24}

    power_hourly = pd.read_parquet(paths["power_hourly"])
    assert len(power_hourly) == 48
