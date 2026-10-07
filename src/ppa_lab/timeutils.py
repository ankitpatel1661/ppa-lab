"""Time handling for power-market data.

Rules used throughout the project (see docs/decisions/0002):
1. Store every timestamp in UTC. UTC has no daylight-saving jumps, so it is
   unambiguous; local time has a missing hour in March and a repeated one in October.
2. A timestamp marks the START of its delivery interval ("interval beginning").
3. Keep the native resolution of the source (60 min until 30 Sep 2025, 15 min
   from 1 Oct 2025 for day-ahead prices) and derive coarser views from it.
4. Convert to Europe/Berlin only to group by delivery day/month/year or to display.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import numpy as np
import pandas as pd

UTC = "UTC"
# One fixed time resolution for every index in the project. pandas >= 3 infers
# the unit from the input (seconds for Unix seconds) and Parquet stores at least
# milliseconds, so without this rule the same data would come back with a
# different dtype after a save/load round trip.
TIME_UNIT = "ns"


def normalise_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return the index in UTC, at the project time unit, named 'ts_utc'."""
    return pd.DatetimeIndex(index.tz_convert(UTC).as_unit(TIME_UNIT), name="ts_utc")


def from_unix_seconds(seconds: Sequence[int]) -> pd.DatetimeIndex:
    """Convert Unix seconds (as returned by most APIs) to a UTC DatetimeIndex."""
    idx = pd.to_datetime(np.asarray(seconds, dtype="int64"), unit="s", utc=True)
    return normalise_index(pd.DatetimeIndex(idx))


def hours_in_local_day(day: date, tz: str) -> int:
    """Number of clock hours in a local delivery day: 23, 24 or 25.

    pandas computes the difference between two tz-aware Timestamps in absolute
    (UTC) time. Plain Python `datetime` objects sharing the same tzinfo do NOT:
    they subtract wall-clock times and would always return 24 hours.
    """
    start = pd.Timestamp(day).tz_localize(tz)
    end = (pd.Timestamp(day) + pd.Timedelta(days=1)).tz_localize(tz)
    return int((end - start) / pd.Timedelta(hours=1))


def expected_intervals(day: date, tz: str, resolution_min: int) -> int:
    """How many intervals a complete local day has at a given resolution."""
    if 60 % resolution_min != 0:
        raise ValueError(f"Resolution must divide 60 minutes, got {resolution_min}")
    return hours_in_local_day(day, tz) * (60 // resolution_min)


def interval_minutes(index: pd.DatetimeIndex) -> pd.Series:
    """Length in minutes of the interval that starts at each timestamp.

    The length is the distance to the neighbouring timestamp. Taking the minimum
    of the previous and next distance makes the estimate robust to gaps
    (a missing hour does not turn the previous hour into a 2-hour interval) and
    handles a change of resolution (hourly -> quarter-hourly) correctly.
    """
    if len(index) == 0:
        return pd.Series([], index=index, dtype="float64", name="interval_min")
    if len(index) == 1:
        return pd.Series([60.0], index=index, name="interval_min")
    # Subtract timestamps and divide by one minute. Never use index.asi8 here:
    # pandas >= 3 stores datetimes in seconds/microseconds/nanoseconds depending
    # on the input, so the raw integers have no fixed unit.
    steps = ((index[1:] - index[:-1]) / pd.Timedelta(minutes=1)).to_numpy(dtype="float64")
    prev_step = np.concatenate([[steps[0]], steps])
    next_step = np.concatenate([steps, [steps[-1]]])
    return pd.Series(np.minimum(prev_step, next_step), index=index, name="interval_min")


def to_hourly(frame: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Average sub-hourly values to hourly values (interval-beginning, UTC).

    For prices and for power in MW the hourly value is the time-weighted mean of
    the intervals inside the hour; because the intervals inside one hour have
    equal length, that is the simple mean. Hours without data stay NaN, so
    gaps remain visible instead of being silently filled.
    """
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
        raise TypeError("to_hourly expects a tz-aware DatetimeIndex (UTC)")
    return frame.resample("1h").mean()


def local_dates(index: pd.DatetimeIndex, tz: str) -> pd.Index:
    """Local delivery date for each UTC timestamp."""
    return pd.Index(index.tz_convert(tz).date, name="delivery_date")
