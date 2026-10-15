"""Historical back-test of PPA structures: a park signs at the end of year Y-1 and delivers in Y."""

import pandas as pd
import pytest

from ppa_lab.pricing.backtest import backtest, park_energy, summarise

TZ = "Europe/Berlin"


def hourly_index(first_local: str, last_local_exclusive: str) -> pd.DatetimeIndex:
    idx = pd.date_range(first_local, last_local_exclusive, freq="h", tz=TZ, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


IDX = hourly_index("2024-01-01", "2026-01-01")      # two local years, hourly
YEAR = IDX.tz_convert(TZ).year


def test_park_energy_scales_each_year_to_capacity_times_full_load_hours():
    # National output doubles from 2024 to 2025 (fleet growth); the park must not.
    national = pd.Series(1_000.0, index=IDX).where(YEAR == 2024, 2_000.0)
    park = park_energy(national, capacity_mw=50, full_load_hours=1_000, tz=TZ, years=[2024, 2025])
    by_year = park.groupby(park.index.tz_convert(TZ).year).sum()
    assert by_year.tolist() == pytest.approx([50_000.0, 50_000.0])  # 50 MW x 1,000 h, each year


def test_park_energy_keeps_the_national_shape():
    shape = pd.Series(range(1, len(IDX) + 1), index=IDX, dtype="float64")
    park = park_energy(shape, capacity_mw=50, full_load_hours=1_000, tz=TZ, years=[2025])
    ratio = park / shape[park.index]
    assert ratio.max() == pytest.approx(ratio.min())  # one scale factor within the year


def test_park_energy_leaves_out_years_not_asked_for():
    park = park_energy(pd.Series(1.0, index=IDX), 50, 1_000, TZ, years=[2025])
    assert set(park.index.tz_convert(TZ).year) == {2025}


def two_year_market():
    # Prices: 100 EUR/MWh all of 2024, 50 EUR/MWh all of 2025. Flat production.
    prices = pd.Series(100.0, index=IDX).where(YEAR == 2024, 50.0)
    energy = pd.Series(2.0, index=IDX)
    return prices, energy


def test_strikes_are_fixed_at_the_previous_years_outcome():
    prices, energy = two_year_market()
    _, strikes, _ = backtest(prices, energy, TZ, delivery_years=[2025], floor=0.0)
    assert strikes.loc[2025, "pay_as_produced_strike"] == pytest.approx(100.0)  # 2024 capture
    assert strikes.loc[2025, "baseload_strike"] == pytest.approx(100.0)          # 2024 base
    assert strikes.loc[2025, "band_mw"] == pytest.approx(2.0)                   # flat 2 MWh/h


def test_backtest_cash_flows_per_structure():
    # 2025 delivery at strikes from 2024 (100): PaP earns 100/MWh, merchant 50/MWh,
    # a flat profile equal to the band makes the baseload PPA earn exactly 100/MWh too.
    prices, energy = two_year_market()
    cash, _, _ = backtest(prices, energy, TZ, delivery_years=[2025], floor=0.0)
    per_mwh = cash.sum() / energy[cash.index].sum()
    assert per_mwh["merchant"] == pytest.approx(50.0)
    assert per_mwh["pay_as_produced"] == pytest.approx(100.0)
    assert per_mwh["baseload"] == pytest.approx(100.0)
    assert per_mwh["merchant_with_floor"] == pytest.approx(50.0)  # prices never below the floor


def test_backtest_needs_the_year_before_delivery():
    prices, energy = two_year_market()
    with pytest.raises(ValueError, match="2023"):
        backtest(prices, energy, TZ, delivery_years=[2024], floor=0.0)


def test_plan_is_each_structure_applied_to_the_previous_year_at_the_same_strikes():
    # What the producer expected when signing: 2024 looked like 100 EUR/MWh everywhere,
    # so every structure planned 100 EUR/MWh for 2025.
    prices, energy = two_year_market()
    _, _, plan = backtest(prices, energy, TZ, delivery_years=[2025], floor=0.0)
    assert plan.loc[2025].tolist() == pytest.approx([100.0] * 5)


def test_summarise_reports_revenue_surprise_and_worst_month():
    prices, energy = two_year_market()
    cash, _, plan = backtest(prices, energy, TZ, delivery_years=[2025], floor=0.0)
    table = summarise(cash, energy, TZ, plan).loc[2025]
    # Prices halved: merchant missed its plan by 50 EUR/MWh, the PaP PPA by nothing.
    assert table.loc["merchant", "vs_plan_eur_per_mwh"] == pytest.approx(-50.0)
    assert table.loc["pay_as_produced", "vs_plan_eur_per_mwh"] == pytest.approx(0.0)
    assert table.loc["merchant", "revenue_eur_per_mwh"] == pytest.approx(50.0)
    # 2 MWh x 8,760 h x 100 EUR = EUR 1.752 m for the PaP PPA
    assert table.loc["pay_as_produced", "revenue_eur_m"] == pytest.approx(1.752)
    # Monthly revenue only varies with the number of hours in the month (28-31 days).
    assert table.loc["pay_as_produced", "worst_month_eur_k"] == pytest.approx(2 * 672 * 100 / 1e3)


def test_site_energy_spreads_hourly_output_over_quarter_hours():
    from ppa_lab.pricing.backtest import site_energy
    hourly = pd.Series([4.0, 8.0], index=pd.date_range("2025-06-01 10:00", periods=2, freq="h",
                                                        tz="UTC"))
    grid = pd.date_range("2025-06-01 10:00", periods=8, freq="15min", tz="UTC")
    energy = site_energy(hourly, grid)
    assert energy.tolist() == [1.0] * 4 + [2.0] * 4           # MW x 0.25 h per quarter-hour
    assert energy.sum() == 12.0                                # energy of the two hours kept
