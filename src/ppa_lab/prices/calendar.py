"""Calendar features that shape power prices: hour, day type and season, in local time.

Demand, and therefore price, differs between working days, Saturdays and Sundays or
public holidays. Only the nine nationwide German holidays are used; regional ones
(e.g. Corpus Christi in the south) affect demand less and are left out.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (anonymous Gregorian algorithm, Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month = (h + m - 7 * n + 114) // 31
    day = (h + m - 7 * n + 114) % 31 + 1
    return date(year, month, day)


def german_holidays(year: int) -> set[date]:
    """The nine nationwide public holidays in Germany."""
    easter = easter_sunday(year)
    return {
        date(year, 1, 1),                      # New Year
        easter - timedelta(days=2),            # Good Friday
        easter + timedelta(days=1),            # Easter Monday
        date(year, 5, 1),                      # Labour Day
        easter + timedelta(days=39),           # Ascension
        easter + timedelta(days=50),           # Whit Monday
        date(year, 10, 3),                     # German Unity Day
        date(year, 12, 25),                    # Christmas Day
        date(year, 12, 26),                    # Boxing Day
    }


def calendar_features(index: pd.DatetimeIndex, tz: str) -> pd.DataFrame:
    """Local hour, month, season and day type (weekday / saturday / holiday) per timestamp.

    Sundays count as 'holiday': demand on both is similarly low.
    """
    local = index.tz_convert(tz)
    days = local.date
    holidays = set().union(*(german_holidays(y) for y in set(local.year)))
    weekday = local.dayofweek
    daytype = [
        "holiday" if (dw == 6 or d in holidays) else "saturday" if dw == 5 else "weekday"
        for dw, d in zip(weekday, days, strict=True)
    ]
    return pd.DataFrame(
        {"hour": local.hour.astype("int64"), "month": local.month.astype("int64"),
         "season": local.month.map(SEASONS), "daytype": daytype,
         "year": local.year.astype("int64")},
        index=index,
    )
