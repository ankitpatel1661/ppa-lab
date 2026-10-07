import dataclasses
from datetime import date

import pandas as pd
import pytest

from conftest import make_power_frame
from ppa_lab.data.quality import check_power, check_prices


def status(results, name):
    return next(r.status for r in results if r.name == name)


@pytest.fixture
def switch_settings(settings):
    return dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1))


def test_real_prices_pass_all_checks(switch_prices, switch_settings):
    results = check_prices(switch_prices, switch_settings)
    assert all(r.status != "fail" for r in results), results
    regimes = next(r.detail for r in results if r.name == "resolution regimes")
    assert "60 min 2025-09-30" in regimes and "15 min 2025-10-01" in regimes


def test_duplicate_timestamp_fails(switch_prices, switch_settings):
    duplicated = pd.concat([switch_prices, switch_prices.iloc[[5]]]).sort_index()
    assert status(check_prices(duplicated, switch_settings), "no duplicate timestamps") == "fail"


def test_missing_quarter_hour_fails_completeness(switch_prices, switch_settings):
    gappy = switch_prices.drop(switch_prices.index[50])
    results = check_prices(gappy, switch_settings)
    assert status(results, "complete delivery days (DST-aware)") == "fail"


def test_impossible_price_fails(switch_prices, switch_settings):
    broken = switch_prices.copy()
    broken.iloc[3, 0] = 5000.0  # above the +4000 EUR/MWh harmonised maximum
    results = check_prices(broken, switch_settings)
    assert status(results, "within SDAC clearing-price limits") == "fail"


def _hourly_day(day: date, value_at_noon: float) -> pd.DataFrame:
    idx = pd.date_range(pd.Timestamp(day).tz_localize("Europe/Berlin"), periods=24, freq="1h")
    prices = pd.Series(50.0, index=idx.tz_convert("UTC"), name="price_eur_mwh")
    prices.iloc[12] = value_at_noon
    prices.index.name = "ts_utc"
    return prices.to_frame()


def test_price_floor_moved_to_minus_600_on_29_may_2026(settings):
    s = dataclasses.replace(settings, start=date(2026, 5, 28), end=date(2026, 5, 29))
    before = _hourly_day(date(2026, 5, 28), -550.0)
    after = _hourly_day(date(2026, 5, 29), -550.0)
    check = "within SDAC clearing-price limits"
    assert status(check_prices(pd.concat([before, _hourly_day(date(2026, 5, 29), 50.0)]), s),
                  check) == "fail"
    assert status(check_prices(pd.concat([_hourly_day(date(2026, 5, 28), 50.0), after]), s),
                  check) == "pass"


def test_power_checks_pass_on_plausible_data(settings):
    s = dataclasses.replace(settings, start=date(2025, 3, 30), end=date(2025, 3, 31))
    results = check_power(make_power_frame(s.start, s.end), s)
    assert all(r.status != "fail" for r in results), results


def test_time_zone_bug_is_caught_by_night_solar_check(settings):
    s = dataclasses.replace(settings, start=date(2025, 6, 1), end=date(2025, 6, 1))
    frame = make_power_frame(s.start, s.end)
    frame.index = frame.index + pd.Timedelta(hours=12)  # simulate a botched conversion
    assert status(check_power(frame, s), "no solar at night (00-03 local)") == "fail"
