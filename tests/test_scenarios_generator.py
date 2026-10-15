"""Joint scenarios: every weather year paired with price paths for the delivery year."""

import numpy as np
import pandas as pd
import pytest

from conftest import weather_market
from ppa_lab.scenarios.generator import (
    Scenarios,
    build_scenarios,
    delivery_hours,
    fair_price,
    scenario_table,
)
from ppa_lab.scenarios.link import fit_link
from ppa_lab.scenarios.weather import monthly_climatology, place_on_delivery_hours

TZ = "Europe/Berlin"
YEARS = [2023, 2024, 2025]


@pytest.fixture(scope="module")
def setup():
    m = weather_market()
    link = fit_link(m["model"], m["prices"], m["features"],
                    monthly_climatology(m["features"], 2023, 2025), TZ, window_days=30, k=5)
    return m, link


def build(setup, linked=True, level_volatility=0.0, paths=4):
    m, link = setup
    return build_scenarios(m["model"], link, m["generation"], m["features"], TZ,
                           delivery_year=2027, weather_years=YEARS, paths_per_year=paths,
                           forward=85.0, level_volatility=level_volatility, seed=3, linked=linked)


def test_delivery_hours_cover_the_local_year():
    idx = delivery_hours(2027, TZ)
    assert len(idx) == 8760 and str(idx.tz) == "UTC"
    assert idx[0].tz_convert(TZ) == pd.Timestamp("2027-01-01 00:00", tz=TZ)


def test_every_weather_year_gets_the_same_number_of_price_paths(setup):
    s = build(setup)
    assert s.prices.shape == (len(YEARS) * 4, 8760)
    assert list(s.weather_years) == [y for y in YEARS for _ in range(4)]
    assert np.isfinite(s.prices).all()


def test_volumes_are_the_weather_year_placed_on_the_delivery_calendar(setup):
    m, _ = setup
    s = build(setup)
    local = s.index.tz_convert(TZ)
    codes, days = pd.factorize(local.normalize().tz_localize(None))
    wdays = pd.DatetimeIndex([d.replace(year=2024) for d in days])
    expected = place_on_delivery_hours(m["generation"]["wind_park"], wdays, codes,
                                       local.hour.to_numpy())
    second_year_first_path = 4                       # scenarios 4..7 use weather year 2024
    np.testing.assert_allclose(s.volume("wind_park")[second_year_first_path], expected)


def test_the_average_price_over_all_scenarios_is_the_forward(setup):
    assert build(setup).prices.mean() == pytest.approx(85.0, abs=1e-6)


def test_quarterly_forwards_set_each_quarter_and_keep_the_annual_average(setup):
    m, link = setup
    targets = {1: 120.0, 2: 70.0, 3: 75.0, 4: 90.0}
    s = build_scenarios(m["model"], link, m["generation"], m["features"], TZ, delivery_year=2027,
                        weather_years=YEARS, paths_per_year=4, forward=85.0, seed=3,
                        quarter_forwards=targets)
    quarter = s.index.tz_convert(TZ).quarter.to_numpy()
    for q, target in targets.items():
        assert s.prices[:, quarter == q].mean() == pytest.approx(target, abs=1e-6)
    hours = np.bincount(quarter)[1:]
    assert s.prices.mean() == pytest.approx(np.dot(hours, list(targets.values())) / hours.sum())


def test_the_weather_link_lowers_what_solar_and_wind_earn(setup):
    # In the synthetic market sunny days have deeper middays and windy days are cheaper:
    # pairing prices with the SAME weather year as the volumes must lower both capture rates.
    parks = ["solar_park", "wind_park"]
    linked = scenario_table(build(setup, linked=True, paths=10), parks)
    independent = scenario_table(build(setup, linked=False, paths=10), parks)
    solar = "solar_park_capture_rate"
    assert linked[solar].mean() < independent[solar].mean() - 0.01
    # The wind effect is strong enough to show in EVERY weather year; prices built on
    # another year's weather would lose it.
    wind = "wind_park_capture_rate"
    by_year = pd.DataFrame({"linked": linked.groupby("weather_year")[wind].mean(),
                            "independent": independent.groupby("weather_year")[wind].mean()})
    assert (by_year["linked"] < by_year["independent"] - 0.03).all(), by_year


def test_scenario_table_and_fair_price_by_hand():
    s = Scenarios(index=pd.date_range("2027-01-01", periods=2, freq="h", tz="UTC"),
                  weather_years=np.array([2001, 2002]),
                  prices=np.array([[10.0, 30.0], [50.0, 50.0]]),
                  generation={"park": np.array([[1.0, 3.0], [2.0, 0.0]])},
                  year_row=np.array([0, 1]), level=0.0, linked=True)
    t = scenario_table(s, ["park"])
    assert t["base_price"].tolist() == pytest.approx([20.0, 50.0])
    assert t["park_mwh"].tolist() == pytest.approx([4.0, 2.0])
    assert t["park_revenue_eur"].tolist() == pytest.approx([100.0, 100.0])
    assert t["park_capture_price"].tolist() == pytest.approx([25.0, 50.0])
    assert t["park_capture_rate"].tolist() == pytest.approx([1.25, 1.0])
    # Fair pay-as-produced price = E[sum q P] / E[sum q] (Step 3), not the mean capture price.
    assert fair_price(t, "park") == pytest.approx(200.0 / 6.0)
