import math

import pandas as pd
import pytest

from ppa_lab.analysis.reconcile import annual_price_stats, longest_run, reconcile
from ppa_lab.config import Reference

TZ = "Europe/Berlin"


def frame(times, prices):
    idx = pd.DatetimeIndex(times, tz="UTC", name="ts_utc")
    return pd.DataFrame({"price_eur_mwh": prices}, index=idx)


def test_mean_price_is_time_weighted_across_resolutions():
    # One hourly price of 100, then one hour of quarter-hours [0, 0, 0, 400] (mean 100).
    df = frame(
        ["2025-09-30 21:00", "2025-09-30 22:00", "2025-09-30 22:15",
         "2025-09-30 22:30", "2025-09-30 22:45"],
        [100.0, 0.0, 0.0, 0.0, 400.0],
    )
    stats = annual_price_stats(df, TZ)
    assert stats.loc[2025, "mean_price_eur_mwh"] == pytest.approx(100.0)
    assert stats.loc[2025, "hours"] == pytest.approx(2.0)


def test_negative_hour_definitions_differ_after_15_minute_switch():
    # Quarter-hours [-10, 10, 10, 10]: hourly mean +2.5 is NOT negative,
    # but the hour contains a negative interval lasting 0.25 h.
    df = frame(
        ["2025-10-05 10:00", "2025-10-05 10:15", "2025-10-05 10:30", "2025-10-05 10:45"],
        [-10.0, 10.0, 10.0, 10.0],
    )
    stats = annual_price_stats(df, TZ)
    assert stats.loc[2025, "negative_hours"] == 0
    assert stats.loc[2025, "hours_with_any_negative_interval"] == 1
    assert stats.loc[2025, "negative_time_hours"] == pytest.approx(0.25)


def test_longest_run():
    assert longest_run(pd.Series([True, True, False, True, True, True, False])) == 3
    assert longest_run(pd.Series([False, False])) == 0


def test_reconcile_flags_differences_beyond_tolerance():
    stats = pd.DataFrame({"negative_hours": [575, 300]}, index=pd.Index([2025, 2023], name="year"))
    refs = (
        Reference("negative_hours", 2025, 573, 5, "a"),
        Reference("negative_hours", 2023, 320, 5, "b"),
        Reference("negative_hours", 2019, 211, 5, "c"),  # year not in our data
    )
    out = reconcile(stats, refs).set_index("year")
    assert out.loc[2025, "status"] == "within tolerance"
    assert out.loc[2023, "status"] == "OUTSIDE tolerance"
    assert math.isnan(out.loc[2019, "ours"])
    assert out.loc[2019, "status"] == "not available"


def test_difference_with_a_documented_cause_is_marked_explained():
    stats = pd.DataFrame({"mean_price_eur_mwh": [78.51]}, index=pd.Index([2024], name="year"))
    refs = (
        Reference("mean_price_eur_mwh", 2024, 79.46, 0.5, "a", note="26 Jun 2024 decoupling"),
    )
    out = reconcile(stats, refs).set_index("year")
    assert out.loc[2024, "status"] == "explained difference"
    assert out.loc[2024, "note"] == "26 Jun 2024 decoupling"


def test_a_note_does_not_hide_a_difference_within_tolerance():
    stats = pd.DataFrame({"mean_price_eur_mwh": [89.32]}, index=pd.Index([2025], name="year"))
    refs = (Reference("mean_price_eur_mwh", 2025, 89.32, 0.5, "a", note="irrelevant"),)
    assert reconcile(stats, refs).loc[0, "status"] == "within tolerance"
