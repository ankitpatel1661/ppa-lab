import hashlib

import pandas as pd
import pytest

from ppa_lab.data.store import RawStore


def test_roundtrip_and_manifest(tmp_path, switch_prices):
    store = RawStore(tmp_path)
    path = store.save(switch_prices, "prices", "2025-10", {"start": "2025-10-01"})

    loaded = store.load("prices")
    pd.testing.assert_frame_equal(loaded, switch_prices, check_freq=False)
    assert str(loaded.index.tz) == "UTC"

    meta = store.read_meta("prices", "2025-10")
    assert meta["rows"] == len(switch_prices)
    assert meta["start"] == "2025-10-01"
    assert meta["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_raw_files_are_not_overwritten_by_accident(tmp_path, switch_prices):
    store = RawStore(tmp_path)
    store.save(switch_prices, "prices", "2025-10", {})
    with pytest.raises(FileExistsError):
        store.save(switch_prices, "prices", "2025-10", {})
    store.save(switch_prices, "prices", "2025-10", {}, overwrite=True)  # explicit is fine


def test_months_are_sorted_and_missing_data_is_explained(tmp_path, switch_prices):
    store = RawStore(tmp_path)
    for month in ("2025-10", "2025-09"):
        store.save(switch_prices, "prices", month, {})
    assert store.months("prices") == ["2025-09", "2025-10"]
    with pytest.raises(FileNotFoundError, match="ppa-lab fetch"):
        store.load("power")
