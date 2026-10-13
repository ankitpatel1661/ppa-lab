"""Annual energy per weather year and the P50 / P90 statistics used for volume risk."""

import pandas as pd
import pytest

from ppa_lab.weather.yields import annual_energy, p_values

TZ = "Europe/Berlin"


def test_annual_energy_sums_each_complete_local_year():
    # 1 MW flat from 1 Jan 2023 to 31 Dec 2024 (local), plus half of January 2025.
    idx = pd.date_range("2023-01-01", "2025-01-16", freq="h", tz=TZ, inclusive="left")
    mw = pd.Series(1.0, index=idx.tz_convert("UTC"))
    energy = annual_energy(mw, TZ)
    assert energy.to_dict() == {2023: 8760.0, 2024: 8784.0}  # 2024 is a leap year; 2025 incomplete


def test_p_values_from_three_weather_years():
    # mean 100, sample std 10 -> P90 (1 year) = 100 - 1.2816 * 10 = 87.18;
    # P90 (10-year average) = 100 - 1.2816 * 10 / sqrt(10) = 95.95
    stats = p_values(pd.Series([90.0, 100.0, 110.0], index=[2001, 2002, 2003]))
    assert stats["mean"] == pytest.approx(100.0)
    assert stats["p50"] == pytest.approx(100.0)
    assert stats["std"] == pytest.approx(10.0)
    assert stats["cov"] == pytest.approx(0.10)
    assert stats["p90_1y"] == pytest.approx(87.184, abs=1e-3)
    assert stats["p90_10y"] == pytest.approx(95.947, abs=1e-3)
    assert stats["min_year"] == 2001 and stats["max_year"] == 2003
