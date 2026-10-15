from datetime import date

import pandas as pd
import pytest

from conftest import make_power_frame
from ppa_lab.analysis.capture import capture_table, reconciliation_metrics
from ppa_lab.analysis.reconcile import annual_price_stats
from ppa_lab.config import DEFAULT_CONFIG, load_settings

TZ = "Europe/Berlin"


def test_project_config_loads():
    s = load_settings()
    assert s.bidding_zone == "DE-LU"
    assert s.timezone == "Europe/Berlin"
    assert s.start <= s.end
    assert s.references, "reconciliation references should be configured"


def test_price_limits_change_on_29_may_2026():
    s = load_settings()
    assert s.price_limit_on(date(2026, 5, 28)).min_eur_mwh == -500
    assert s.price_limit_on(date(2026, 5, 29)).min_eur_mwh == -600
    assert s.price_limit_on(date(2026, 5, 29)).max_eur_mwh == 4000
    with pytest.raises(ValueError):
        s.price_limit_on(date(2020, 1, 1))


def test_inverted_date_range_is_rejected(tmp_path):
    text = DEFAULT_CONFIG.read_text()
    bad = text.replace("start = 2023-01-01", "start = 2027-01-01")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="after"):
        load_settings(path)


def test_reference_dir_holds_the_official_market_values():
    s = load_settings()
    assert (s.reference_dir / "netztransparenz_market_values_monthly.csv").exists()


def test_every_reference_metric_is_computed_by_the_pipeline():
    # A typo in a metric name would turn a reference into a silent "not available".
    power = make_power_frame(date(2025, 6, 2), date(2025, 6, 2))
    prices = pd.DataFrame({"price_eur_mwh": 50.0, "interval_min": 15.0}, index=power.index)
    produced = set(annual_price_stats(prices, TZ).columns) | set(
        reconciliation_metrics(capture_table(prices, power, TZ, freq="Y")).columns
    )
    unknown = {r.metric for r in load_settings().references} - produced
    assert not unknown, f"reference metrics nobody computes: {unknown}"


def test_backtest_parks_are_configured():
    s = load_settings()
    assert {p.technology for p in s.parks} <= {"solar", "wind_onshore", "wind_offshore"}
    assert all(p.capacity_mw > 0 and p.full_load_hours > 0 for p in s.parks)


def test_a_delivery_year_needs_the_previous_year_in_the_data_range(tmp_path):
    text = DEFAULT_CONFIG.read_text()
    bad = text.replace("delivery_years = [2024, 2025]", "delivery_years = [2023, 2024]")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="2022"):
        load_settings(path)


def test_every_park_has_a_site_and_a_model():
    s = load_settings()
    assert s.weather_first_year <= s.start.year
    for park in s.parks:
        assert -90 <= park.latitude <= 90 and -180 <= park.longitude <= 180
        assert park.site
        needed = {"solar": {"tilt_deg", "azimuth_deg", "dc_ac_ratio", "losses_pct"},
                  "wind_onshore": {"turbine_type", "hub_height_m", "losses_pct"}}[park.technology]
        assert needed <= set(park.model)


def test_price_model_window_must_lie_inside_the_market_data(tmp_path):
    s = load_settings()
    pm = s.price_model
    assert s.start <= pm.calibration_start < pm.calibration_end <= s.end
    assert pm.delivery_year > pm.calibration_end.year
    bad = DEFAULT_CONFIG.read_text().replace("calibration_end = 2026-09-30",
                                             "calibration_end = 2027-06-30")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="calibration"):
        load_settings(path)


def test_scenarios_use_complete_weather_years_and_need_the_price_model(tmp_path):
    s = load_settings()
    sc = s.scenarios
    assert s.weather_first_year <= sc.weather_last_year
    assert sc.paths_per_weather_year > 0 and sc.analog_k > 0
    bad = DEFAULT_CONFIG.read_text().replace("weather_last_year = 2025", "weather_last_year = 1990")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="weather_last_year"):
        load_settings(path)


def test_ppa_pricing_settings_match_the_scenarios(tmp_path):
    s = load_settings()
    ppa = s.ppa
    assert ppa.start_year == s.price_model.delivery_year      # scenarios exist for this year
    assert ppa.tenor_years >= 1 and 0 < ppa.risk_quantile < 0.5
    assert set(ppa.parks) <= {p.name for p in s.parks}
    assert s.price_model.calibration_start <= ppa.analog_pool_start <= s.price_model.calibration_end
    bad = DEFAULT_CONFIG.read_text().replace("start_year = 2027", "start_year = 2030")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="start_year"):
        load_settings(path)


def test_hedging_backtest_needs_the_previous_year_and_quotes_name_known_products(tmp_path):
    s = load_settings()
    hg = s.hedging
    assert all(s.start.year <= y - 1 and y <= s.end.year for y in hg.backtest_years)
    assert {q.product for q in hg.market_quotes} <= {"cal_base", "cal_peak"}
    assert all(q.source.startswith("http") for q in hg.market_quotes)
    bad = DEFAULT_CONFIG.read_text().replace("backtest_years = [2024, 2025]",
                                             "backtest_years = [2023, 2025]")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="backtest"):
        load_settings(path)


def test_the_forward_names_its_source_and_the_curve_covers_later_years(tmp_path):
    s = load_settings()
    pm, ppa = s.price_model, s.ppa
    assert pm.forward_date is not None and pm.forward_source.startswith("http")
    assert ppa.forward_curve and all(isinstance(y, int) for y in ppa.forward_curve)
    assert all(ppa.start_year < y < ppa.start_year + ppa.tenor_years for y in ppa.forward_curve)
    bad = DEFAULT_CONFIG.read_text().replace("2028 = 104.75", "2027 = 104.75")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="forward_curve"):
        load_settings(path)


def test_quarter_quotes_are_complete_and_average_to_their_cal(tmp_path):
    qq = load_settings().price_model.quarter_quotes
    assert qq is not None and set(qq.quarters) == {1, 2, 3, 4} and qq.source.startswith("http")
    bad = DEFAULT_CONFIG.read_text().replace("Q1 = 179.47", "Q1 = 150.00")
    path = tmp_path / "bad.toml"
    path.write_text(bad)
    with pytest.raises(ValueError, match="quarter_quotes"):
        load_settings(path)
