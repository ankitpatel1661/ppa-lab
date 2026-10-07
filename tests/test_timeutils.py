from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from ppa_lab.timeutils import (
    expected_intervals,
    from_unix_seconds,
    hours_in_local_day,
    interval_minutes,
    local_dates,
    to_hourly,
)

TZ = "Europe/Berlin"


@pytest.mark.parametrize(
    ("day", "hours"),
    [
        (date(2025, 3, 30), 23),  # clocks go forward: 02:00 -> 03:00
        (date(2025, 10, 26), 25),  # clocks go back: 03:00 -> 02:00
        (date(2025, 6, 1), 24),
        (date(2024, 3, 31), 23),
        (date(2024, 10, 27), 25),
    ],
)
def test_hours_in_local_day(day, hours):
    assert hours_in_local_day(day, TZ) == hours


def test_plain_python_datetime_gets_dst_wrong():
    """Documents WHY we use pandas: same-tzinfo datetime subtraction is wall-clock."""
    zone = ZoneInfo(TZ)
    start, end = datetime(2025, 3, 30, tzinfo=zone), datetime(2025, 3, 31, tzinfo=zone)
    assert end - start == timedelta(hours=24)  # wrong for an energy day...
    assert hours_in_local_day(date(2025, 3, 30), TZ) == 23  # ...correct


def test_expected_intervals():
    assert expected_intervals(date(2025, 10, 26), TZ, 15) == 100
    assert expected_intervals(date(2025, 3, 30), TZ, 60) == 23
    assert expected_intervals(date(2025, 6, 1), TZ, 15) == 96
    with pytest.raises(ValueError):
        expected_intervals(date(2025, 6, 1), TZ, 7)


def test_from_unix_seconds_is_utc():
    idx = from_unix_seconds([1759269600])  # 2025-09-30 22:00 UTC
    assert str(idx.tz) == "UTC"
    assert idx[0] == pd.Timestamp("2025-09-30 22:00", tz="UTC")


def test_interval_minutes_handles_resolution_switch():
    idx = pd.DatetimeIndex(
        ["2025-09-30 21:00", "2025-09-30 22:00", "2025-09-30 22:15",
         "2025-09-30 22:30", "2025-09-30 22:45"],
        tz="UTC",
    )
    assert interval_minutes(idx).tolist() == [60, 15, 15, 15, 15]


def test_interval_minutes_is_robust_to_gaps():
    idx = pd.DatetimeIndex(
        ["2025-06-01 00:00", "2025-06-01 01:00", "2025-06-01 03:00", "2025-06-01 04:00"], tz="UTC"
    )
    assert interval_minutes(idx).tolist() == [60, 60, 60, 60]


def test_to_hourly_averages_quarter_hours_and_keeps_hourly_values():
    idx = pd.DatetimeIndex(
        ["2025-09-30 21:00", "2025-09-30 22:00", "2025-09-30 22:15",
         "2025-09-30 22:30", "2025-09-30 22:45"],
        tz="UTC",
    )
    s = pd.Series([100.0, 0.0, 0.0, 0.0, 400.0], index=idx)
    assert to_hourly(s).tolist() == [100.0, 100.0]


def test_to_hourly_rejects_naive_index():
    s = pd.Series([1.0], index=pd.DatetimeIndex(["2025-01-01 00:00"]))
    with pytest.raises(TypeError):
        to_hourly(s)


def test_local_dates_follow_berlin_midnight():
    idx = pd.DatetimeIndex(["2025-09-30 21:59", "2025-09-30 22:00"], tz="UTC")
    assert list(local_dates(idx, TZ)) == [date(2025, 9, 30), date(2025, 10, 1)]
