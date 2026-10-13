"""Checks of the site models against national data, and the yield trend over weather years."""

import numpy as np
import pandas as pd
import pytest

from ppa_lab.analysis.generation import monthly_shares, site_vs_national, yield_trend

TZ = "Europe/Berlin"


def hourly_local(first: str, last_exclusive: str) -> pd.DatetimeIndex:
    idx = pd.date_range(first, last_exclusive, freq="h", tz=TZ, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


def test_yield_trend_per_decade():
    # +2 MWh per year on a mean of 100 -> +20 MWh (+20 %) per decade.
    annual = pd.Series([90.0, 92.0, 94.0, 96.0, 98.0, 100.0, 102.0, 104.0, 106.0, 108.0, 110.0],
                       index=range(2015, 2026))
    trend = yield_trend(annual)
    assert trend["per_decade"] == pytest.approx(20.0)
    assert trend["per_decade_pct"] == pytest.approx(20.0)


def test_monthly_shares_sum_to_one_and_follow_the_profile():
    idx = hourly_local("2024-01-01", "2025-01-01")
    month = idx.tz_convert(TZ).month
    mw = pd.Series(np.where(month == 7, 3.0, 1.0), index=idx)  # July three times as strong
    shares = monthly_shares(mw, TZ, years=[2024])
    assert shares.sum() == pytest.approx(1.0)
    assert shares.idxmax() == 7
    assert shares[7] == pytest.approx(3 * 744 / (3 * 744 + 8784 - 744))


def test_site_vs_national_compares_correlation_and_capture():
    idx = hourly_local("2024-01-01", "2025-01-01")
    hour = idx.tz_convert(TZ).hour.to_numpy()
    national = pd.Series(np.clip(np.sin((hour - 6) / 12 * np.pi), 0, None), index=idx)
    site = national * 0.5                                   # same shape, smaller park
    prices = pd.Series(np.where((hour >= 10) & (hour < 16), 20.0, 100.0), index=idx)
    table = site_vs_national(site, national, prices, TZ, years=[2024]).loc[2024]
    assert table["correlation"] == pytest.approx(1.0)
    # Same shape -> same capture price, whatever the size.
    assert table["site_capture_eur_mwh"] == pytest.approx(table["national_capture_eur_mwh"])
    assert table["site_capture_rate"] < 0.7                 # solar-like profile, cheap middays
