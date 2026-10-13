"""Calendar features for the price model: German public holidays, day types, seasons."""

from datetime import date

import pandas as pd

from ppa_lab.prices.calendar import calendar_features, easter_sunday, german_holidays

TZ = "Europe/Berlin"


def test_easter_sunday_known_years():
    # Easter Sunday 2026 was the day solar earned -62 EUR/MWh (Day 2 notebook).
    assert easter_sunday(2024) == date(2024, 3, 31)
    assert easter_sunday(2025) == date(2025, 4, 20)
    assert easter_sunday(2026) == date(2026, 4, 5)


def test_nationwide_holidays_2025():
    days = german_holidays(2025)
    assert {date(2025, 1, 1), date(2025, 4, 18), date(2025, 4, 21), date(2025, 5, 1),
            date(2025, 5, 29), date(2025, 6, 9), date(2025, 10, 3), date(2025, 12, 25),
            date(2025, 12, 26)} == days  # Good Friday, Easter Monday, Ascension, Whit Monday


def test_calendar_features_use_local_time():
    # 2025-12-24 23:00 UTC is already Christmas Day (a holiday) in Berlin.
    idx = pd.DatetimeIndex(["2025-12-24 22:00", "2025-12-24 23:00", "2025-07-05 10:00",
                            "2025-07-07 10:00"], tz="UTC")
    f = calendar_features(idx, TZ)
    assert f["daytype"].tolist() == ["weekday", "holiday", "saturday", "weekday"]
    assert f["hour"].tolist() == [23, 0, 12, 12]
    assert f["season"].tolist() == ["winter", "winter", "summer", "summer"]
    assert f["month"].tolist() == [12, 12, 7, 7]
