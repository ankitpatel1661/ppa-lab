"""End-to-end: joint scenarios -> structures, premia, price stack, tenor price -> Step 7 report."""

import dataclasses
import json
from datetime import date

import pytest

from conftest import FakeWeatherClient, write_synthetic_market
from ppa_lab.analysis.step07_report import write_step07_report
from ppa_lab.config import PpaParkSettings, PpaSettings
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather
from test_step06_report import small_settings as step06_settings


def small_settings(settings):
    s = step06_settings(settings)
    park = PpaParkSettings(balancing_eur_mwh=1.5, credit_eur_mwh=1.0, capture_rate_drift=0.0,
                           degradation=0.005)
    ppa = PpaSettings(start_year=2026, tenor_years=3, discount_rate=0.06, risk_quantile=0.05,
                      analog_pool_start=date(2025, 1, 1),
                      parks={"solar_park": park, "wind_park": park})
    return dataclasses.replace(s, ppa=ppa)


def test_step07_report_end_to_end(settings):
    s = small_settings(settings)
    store = RawStore(s.raw_dir, source="open_meteo")
    fetch_weather(s, FakeWeatherClient(), store, today=date(2026, 6, 1))
    build_generation(s, store)
    write_synthetic_market(s)

    out = write_step07_report(s)

    text = out["report"].read_text()
    for phrase in ("risk premium", "Indicative", "cash flow at risk", "2026-2028"):
        assert phrase in text
    for key in ("stack", "revenue", "buyer"):
        assert out[key].exists()
    assert "NaN" not in out["results"].read_text()          # strict JSON: null, not NaN
    results = json.loads(out["results"].read_text())
    solar = results["parks"]["solar_park"]
    stack = solar["stack_eur_mwh"]
    assert stack["indicative"] == pytest.approx(
        stack["fair_price"] - stack["risk_premium"] - stack["balancing"] - stack["credit"])
    assert stack["fair_price"] == pytest.approx(stack["forward"] + stack["shape"])
    assert solar["tenor"]["years"] == [2026, 2027, 2028]
    # the analog-pool sensitivity is stored too (the dashboard offers both pools)
    assert solar["whole_window"]["fair_price"] > 0 and solar["whole_window"]["premium"] >= 0
    # the assumptions behind the numbers travel with them
    assert results["discount_rate"] == 0.06
    assert solar["assumptions"] == {"balancing_eur_mwh": 1.5, "credit_eur_mwh": 1.0,
                                    "capture_rate_drift": 0.0, "degradation": 0.005}


def test_step07_report_explains_missing_weather(settings):
    s = small_settings(settings)
    write_synthetic_market(s)

    out = write_step07_report(s)

    assert "run `ppa-lab weather` first" in out["report"].read_text()
    assert out["results"] is None


def test_tenor_rows_follow_the_curve_and_add_the_scaled_shape_case():
    from ppa_lab.analysis.step07_report import SCALED_SHAPE, tenor_rows
    from ppa_lab.config import PpaParkSettings
    priced = {"stack": {"forward": 100.0, "fair_price": 60.0, "risk_premium": 5.0,
                        "balancing": 1.5, "credit": 1.0}, "energy_mwh": 1000.0}
    cost = PpaParkSettings(balancing_eur_mwh=1.5, credit_eur_mwh=1.0, capture_rate_drift=0.0,
                           degradation=0.0)
    flat = tenor_rows(priced, cost, 2027, 3, 0.0)
    curve = tenor_rows(priced, cost, 2027, 3, 0.0, curve={2028: 70.0}, scaled_shape_fair=50.0)
    assert flat[0]["fair_price"] == pytest.approx(60.0)
    assert curve[0]["fair_price"] == pytest.approx((60.0 + 42.0 + 42.0) / 3)   # 0.6 x 70, flat
    up = next(r for r in curve if r["case"] == "Forward +10%")
    assert up["fair_price"] == pytest.approx(1.1 * curve[0]["fair_price"])    # whole curve
    scaled = next(r for r in curve if r["case"] == SCALED_SHAPE)
    assert scaled["fair_price"] == pytest.approx((50.0 + 35.0 + 35.0) / 3)     # capture rate 0.5
    assert scaled["indicative"] == pytest.approx(scaled["fair_price"] - 7.5)
