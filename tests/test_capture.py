"""Capture prices: what a generation profile actually earns on the day-ahead market.

Expected values are worked out by hand in the comments, never by the code under test.
"""

import numpy as np
import pandas as pd
import pytest

from conftest import make_power_frame
from ppa_lab.analysis.capture import (
    capture_price,
    capture_rate,
    capture_table,
    compare_monthly,
    load_market_values,
    prices_on_grid,
    reconciliation_metrics,
)

TZ = "Europe/Berlin"


def quarter_hours(start_utc: str, periods: int) -> pd.DatetimeIndex:
    return pd.date_range(start_utc, periods=periods, freq="15min", tz="UTC", name="ts_utc")


def series(values, start_utc="2025-06-01 10:00"):
    return pd.Series(values, index=quarter_hours(start_utc, len(values)), dtype="float64")


# --------------------------------------------------------------------------- #
# capture_price / capture_rate
# --------------------------------------------------------------------------- #
def test_capture_price_is_volume_weighted():
    # (10*3 + 100*1) / (3 + 1) = 130 / 4 = 32.5, not the simple mean 55.
    assert capture_price(series([10.0, 100.0]), series([3.0, 1.0])) == pytest.approx(32.5)


def test_capture_rate_divides_by_the_time_weighted_base_price():
    # Base = (10 + 100) / 2 = 55; capture rate = 32.5 / 55.
    assert capture_rate(series([10.0, 100.0]), series([3.0, 1.0])) == pytest.approx(32.5 / 55)


def test_flat_profile_has_capture_rate_one():
    prices = series([-20.0, 0.0, 35.5, 80.0, 250.0, 12.0])
    flat = series([7.0] * 6)
    assert capture_rate(prices, flat) == pytest.approx(1.0)


def test_generation_only_in_negative_hours_gives_negative_capture_price():
    # Only the first two intervals produce: (-10*5 + -20*5) / 10 = -15.
    prices = series([-10.0, -20.0, 50.0, 60.0])
    generation = series([5.0, 5.0, 0.0, 0.0])
    assert capture_price(prices, generation) == pytest.approx(-15.0)


def test_capture_price_requires_the_same_time_grid():
    # Hourly prices against quarter-hourly generation would silently drop 3 of 4 quarters.
    hourly_index = pd.date_range("2025-06-01", periods=2, freq="h", tz="UTC")
    hourly = pd.Series([50.0, 60.0], index=hourly_index)
    with pytest.raises(ValueError, match="same time grid"):
        capture_price(hourly, series([1.0] * 8, start_utc="2025-06-01 00:00"))


def test_capture_price_without_generation_is_undefined():
    with pytest.raises(ValueError, match="no generation"):
        capture_price(series([50.0, 60.0]), series([0.0, 0.0]))


# --------------------------------------------------------------------------- #
# prices_on_grid: hourly prices (until 30 Sep 2025) onto the 15-minute generation grid
# --------------------------------------------------------------------------- #
def test_prices_on_grid_repeats_each_hourly_price_for_its_four_quarters(switch_prices):
    # Real data: 30 Sep 2025 is hourly, 1 Oct 2025 is quarter-hourly.
    grid = quarter_hours("2025-09-29 22:00", 2 * 96)  # both local days
    on_grid = prices_on_grid(switch_prices, grid)

    assert on_grid.index.equals(grid)
    assert not on_grid.isna().any()
    noon_30_sep = pd.Timestamp("2025-09-30 10:00", tz="UTC")
    for minutes in (0, 15, 30, 45):
        assert on_grid[noon_30_sep + pd.Timedelta(minutes=minutes)] == (
            switch_prices.loc[noon_30_sep, "price_eur_mwh"]
        )
    quarter_1_oct = pd.Timestamp("2025-10-01 10:45", tz="UTC")
    assert on_grid[quarter_1_oct] == switch_prices.loc[quarter_1_oct, "price_eur_mwh"]


def test_prices_on_grid_leaves_missing_hours_empty():
    # Hours 00:00 and 02:00 exist, 01:00 is missing: its quarters must stay NaN,
    # not be forward-filled with a price that was never published.
    idx = pd.DatetimeIndex(["2025-06-01 00:00", "2025-06-01 02:00"], tz="UTC", name="ts_utc")
    prices = pd.DataFrame({"price_eur_mwh": [40.0, 70.0], "interval_min": [60.0, 60.0]}, index=idx)
    on_grid = prices_on_grid(prices, quarter_hours("2025-06-01 00:00", 12))
    assert on_grid.isna().tolist() == [False] * 4 + [True] * 4 + [False] * 4
    assert on_grid.iloc[-1] == 70.0


# --------------------------------------------------------------------------- #
# capture_table: by local month or year, per technology
# --------------------------------------------------------------------------- #
def _hourly_prices(start_utc: str, values: list[float]) -> pd.DataFrame:
    idx = pd.date_range(start_utc, periods=len(values), freq="h", tz="UTC", name="ts_utc")
    return pd.DataFrame({"price_eur_mwh": values, "interval_min": 60.0}, index=idx)


def test_capture_table_groups_by_local_month_not_utc_month():
    # 31 Jan 2025 23:00 UTC is already 1 Feb 00:00 in Berlin (UTC+1).
    prices = _hourly_prices("2025-01-31 22:00", [10.0, 50.0])
    power = pd.DataFrame({"solar_mw": 1.0}, index=quarter_hours("2025-01-31 22:00", 8))
    table = capture_table(prices, power, TZ, freq="M", technologies={"solar": "solar_mw"})

    assert table.loc[(pd.Period("2025-01", "M"), "solar"), "capture_price_eur_mwh"] == 10.0
    assert table.loc[(pd.Period("2025-02", "M"), "solar"), "capture_price_eur_mwh"] == 50.0


def test_capture_table_on_a_synthetic_day():
    # Two local days; cheap midday (20 EUR/MWh from 10:00 to 16:00 local), 100 otherwise.
    power = make_power_frame(pd.Timestamp("2025-06-02").date(), pd.Timestamp("2025-06-03").date())
    local_hour = power.index.tz_convert(TZ).hour
    price = np.where((local_hour >= 10) & (local_hour < 16), 20.0, 100.0)
    prices = pd.DataFrame({"price_eur_mwh": price, "interval_min": 15.0}, index=power.index)

    table = capture_table(prices, power, TZ, freq="Y")
    row = table.xs(pd.Period("2025", "Y"), level="period")

    # Base: 6 cheap hours of 24 -> (6*20 + 18*100) / 24 = 80.
    assert row["base_price_eur_mwh"].tolist() == pytest.approx([80.0] * 3)
    # Wind is flat, so it earns exactly the base price.
    assert row.loc["wind_onshore", "capture_rate"] == pytest.approx(1.0)
    # Solar produces mostly at midday, so it earns less than base (cannibalisation).
    assert row.loc["solar", "capture_rate"] < 0.6
    # 15,000 MW for 48 hours = 720,000 MWh = 0.72 TWh.
    assert row.loc["wind_onshore", "energy_twh"] == pytest.approx(0.72)
    assert row.loc["wind_onshore", "negative_price_share"] == 0.0


def test_negative_price_share_is_an_energy_share():
    # 1 MWh of 4 produced at a negative price -> 25 %, even though half the time is negative.
    prices = pd.DataFrame(
        {"price_eur_mwh": [-5.0, -5.0, 30.0, 30.0], "interval_min": 15.0},
        index=quarter_hours("2025-06-01 10:00", 4),
    )
    power = pd.DataFrame({"solar_mw": [4.0, 0.0, 8.0, 4.0]}, index=prices.index)
    table = capture_table(prices, power, TZ, freq="M", technologies={"solar": "solar_mw"})
    assert table["negative_price_share"].iloc[0] == pytest.approx(0.25)


def test_reconciliation_metrics_are_in_published_units():
    # The TSOs publish market values in ct/kWh: 45.95 EUR/MWh = 4.595 ct/kWh.
    idx = pd.MultiIndex.from_tuples(
        [(pd.Period("2025", "Y"), "solar")], names=["period", "technology"]
    )
    annual = pd.DataFrame(
        {"capture_price_eur_mwh": [45.95], "negative_price_share": [0.242]}, index=idx
    )
    metrics = reconciliation_metrics(annual)
    assert metrics.loc[2025, "capture_price_solar_ct_kwh"] == pytest.approx(4.595)
    assert metrics.loc[2025, "nonnegative_share_solar_pct"] == pytest.approx(75.8)


# --------------------------------------------------------------------------- #
# Official monthly market values (Monatsmarktwerte) and the monthly comparison
# --------------------------------------------------------------------------- #
def test_load_market_values_reads_the_reference_file(tmp_path):
    path = tmp_path / "mw.csv"
    path.write_text(
        "# source line is ignored\n"
        "month,spot_ct_kwh,wind_onshore_ct_kwh,wind_offshore_ct_kwh,solar_ct_kwh\n"
        "2025-06,6.399,5.141,5.823,1.843\n"
    )
    mw = load_market_values(path)
    assert mw.loc[pd.Period("2025-06", "M"), "solar_ct_kwh"] == 1.843
    assert list(mw.columns) == [
        "spot_ct_kwh", "wind_onshore_ct_kwh", "wind_offshore_ct_kwh", "solar_ct_kwh"
    ]


def test_compare_monthly_reports_the_difference_in_ct_kwh():
    june = pd.Period("2025-06", "M")
    idx = pd.MultiIndex.from_tuples([(june, "solar")], names=["period", "technology"])
    ours = pd.DataFrame(
        {"base_price_eur_mwh": [63.99], "capture_price_eur_mwh": [20.01]}, index=idx
    )
    official = pd.DataFrame(
        {"spot_ct_kwh": [6.399], "solar_ct_kwh": [1.843]},
        index=pd.PeriodIndex([june], name="month"),
    )
    out = compare_monthly(ours, official).set_index(["month", "series"])

    assert out.loc[(june, "spot"), "difference_ct_kwh"] == pytest.approx(0.0, abs=1e-9)
    assert out.loc[(june, "solar"), "ours_ct_kwh"] == pytest.approx(2.001)
    assert out.loc[(june, "solar"), "difference_ct_kwh"] == pytest.approx(0.158)


def test_compare_monthly_skips_months_without_an_official_value():
    idx = pd.MultiIndex.from_tuples(
        [(pd.Period("2026-09", "M"), "solar")], names=["period", "technology"]
    )
    ours = pd.DataFrame({"base_price_eur_mwh": [90.0], "capture_price_eur_mwh": [50.0]}, index=idx)
    official = pd.DataFrame(
        {"spot_ct_kwh": [12.689], "solar_ct_kwh": [6.359]},
        index=pd.PeriodIndex([pd.Period("2026-08", "M")], name="month"),
    )
    assert compare_monthly(ours, official).empty
