"""End-to-end: joint scenarios -> structures, premia, price stack, tenor price -> Step 7 report."""

import dataclasses
import json
from datetime import date

import numpy as np
import pytest

from conftest import FakeWeatherClient, write_synthetic_market
from ppa_lab.analysis.step07_report import write_step07_report
from ppa_lab.config import PpaParkSettings, PpaSettings
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather
from test_step06_report import small_settings as step06_settings


def small_settings(settings, solar_buildout: bool = False):
    s = step06_settings(settings)
    park = PpaParkSettings(balancing_eur_mwh=1.5, credit_eur_mwh=1.0, capture_rate_drift=0.0,
                           degradation=0.005)
    solar = dataclasses.replace(park, buildout=solar_buildout)
    ppa = PpaSettings(start_year=2026, tenor_years=3, discount_rate=0.06, risk_quantile=0.05,
                      analog_pool_start=date(2025, 1, 1),
                      parks={"solar_park": solar, "wind_park": park}, curtail_below_eur_mwh=0.0)
    return dataclasses.replace(s, ppa=ppa)


def fake_buildout(settings, start, years):
    """Two build-out scenarios: the capture rate 10% (base) and 2% lower each year."""
    def scenario(label, step):
        return {"label": label, "pv_additions_gw": 17.0, "storage_additions_gwh": 12.0,
                "share_growth": 0.01, "factor_per_year": step,
                "factors": {start + i: step ** i for i in range(years)}}
    return {"base": "central",
            "calibration": {"kappa": 0.0008, "lam": 0.0004, "amplification": 1.4, "gamma": -5.3,
                            "gamma_se": 0.8, "load_twh": 466.0, "share_start": 0.11,
                            "share_end": 0.15},
            "regression": {"share_coef": -5.3, "share_se": 0.8, "coef": 0.5, "r2": 0.9, "n": 45},
            "history_years": [2022, 2025], "history_pv_additions_gw": [15.5, 17.5, 16.5],
            "history_storage_additions_gwh": 6.5, "storage_cycles_per_year": 250,
            "storage_solar_fraction": 0.8,
            "scenarios": {"central": scenario("Central: solar +17 GW", 0.9),
                          "storage_boom": scenario("Storage boom: storage +35 GWh", 0.98)}}


def test_step07_report_end_to_end(settings, monkeypatch):
    import ppa_lab.analysis.step07_report as step07
    monkeypatch.setattr(step07, "buildout_paths", fake_buildout)
    s = small_settings(settings, solar_buildout=True)
    store = RawStore(s.raw_dir, source="open_meteo")
    fetch_weather(s, FakeWeatherClient(), store, today=date(2026, 6, 1))
    build_generation(s, store)
    write_synthetic_market(s)

    out = write_step07_report(s)

    text = out["report"].read_text()
    for phrase in ("risk premium", "Indicative", "cash flow at risk", "2026-2028"):
        assert phrase in text
    for key in ("stack", "revenue", "buyer", "level"):
        assert out[key].exists()
    assert "Does the capture rate rise with the price level?" in text
    assert "Negative prices: curtail, and who keeps the value" in text
    assert "The EEG premium against a PPA" in text and "strip of puts" in text
    assert "NaN" not in out["results"].read_text()          # strict JSON: null, not NaN
    results = json.loads(out["results"].read_text())
    solar = results["parks"]["solar_park"]
    stack = solar["stack_eur_mwh"]
    assert stack["indicative"] == pytest.approx(
        stack["fair_price"] - stack["risk_premium"] - stack["balancing"] - stack["credit"])
    assert stack["fair_price"] == pytest.approx(stack["forward"] + stack["shape"])
    assert solar["tenor"]["years"] == [2026, 2027, 2028]
    # curtailment (v1.8): the clause is priced on the delivered output, at its own strike
    neg = solar["negative_prices"]
    assert 0 < neg["curtailment"]["share"] < 1 and neg["curtailment"]["value"] > 0
    clause = neg["clause"]
    assert clause["stack_eur_mwh"]["fair_price"] > stack["fair_price"]      # negatives left out
    assert clause["delivered_share"] == pytest.approx(1 - neg["curtailment"]["share"])
    assert neg["deemed_strike"] == pytest.approx(stack["fair_price"]
                                                 + neg["curtailment"]["value"])
    curtailing = solar["structures"]["merchant"]["expected_revenue_eur"]
    producing = solar["structures"]["merchant_no_curtailment"]["expected_revenue_eur"]
    assert curtailing > producing
    # the EEG (v1.9): merchant revenue plus the market premium, against the PPA
    eeg = results["parks"]["wind_park"]["eeg"]
    years = eeg["tenor"]["years"]
    assert [r["year"] for r in years] == [2026, 2027, 2028]
    for r in years:
        assert r["premium_eur_mwh"] >= 0
        assert r["eeg_eur_mwh"] == pytest.approx(r["merchant_eur_mwh"] + r["premium_eur_mwh"])
    assert eeg["tenor"]["net"] == pytest.approx(eeg["tenor"]["value"] - eeg["fee_eur_mwh"])
    premia = [v["premium"] for _, v in sorted(eeg["awards"].items(), key=lambda kv: float(kv[0]))]
    assert premia == sorted(premia)                      # a higher strike is worth more
    assert results["parks"]["solar_park"]["eeg"] is None
    # the model's capture rate by price level, for the dashboard (PPA-8d)
    levels = solar["level_response"]["level"]
    assert levels == sorted(levels) and len(levels) == len(results["level_grid"])
    # the analog-pool sensitivity is stored too (the dashboard offers both pools)
    assert solar["whole_window"]["fair_price"] > 0 and solar["whole_window"]["premium"] >= 0
    # the assumptions behind the numbers travel with them
    assert results["discount_rate"] == 0.06
    assert solar["assumptions"] == {"balancing_eur_mwh": 1.5, "credit_eur_mwh": 1.0,
                                    "capture_rate_drift": 0.0, "degradation": 0.005}
    # build-out scenarios (v1.11): the base one prices the solar park, the others are rows
    assert "Solar and storage build-out after 2026" in text and "Storage boom" in text
    assert solar["buildout"]["base"] == "central"
    assert results["parks"]["wind_park"]["buildout"] is None
    assert results["buildout"]["calibration"]["kappa"] == 0.0008
    cases = {r["case"]: r for r in solar["tenor"]["sensitivity"]}
    boom = cases["Build-out: Storage boom: storage +35 GWh"]
    assert boom["fair_price"] > cases["Base case"]["fair_price"]      # slower fall
    assert solar["buildout"]["tenor_with_fixed_trend"] > 0


def test_step07_report_explains_missing_weather(settings):
    s = small_settings(settings)
    write_synthetic_market(s)

    out = write_step07_report(s)

    assert "run `ppa-lab weather` first" in out["report"].read_text()
    assert out["results"] is None


def test_tenor_rows_follow_the_curve_and_move_the_capture_rate_with_the_level():
    from ppa_lab.analysis.step07_report import (
        LEVEL_LOW,
        OUT_OF_SAMPLE,
        line_response,
        tenor_rows,
    )
    from ppa_lab.config import PpaParkSettings
    priced = {"stack": {"forward": 100.0, "fair_price": 60.0, "risk_premium": 5.0,
                        "balancing": 1.5, "credit": 1.0}, "energy_mwh": 1000.0}
    cost = PpaParkSettings(balancing_eur_mwh=1.5, credit_eur_mwh=1.0, capture_rate_drift=0.0,
                           degradation=0.0)
    flat = tenor_rows(priced, cost, 2027, 3, 0.0)
    curve = tenor_rows(priced, cost, 2027, 3, 0.0, curve={2028: 70.0})
    assert flat[0]["fair_price"] == pytest.approx(60.0)
    assert curve[0]["fair_price"] == pytest.approx((60.0 + 42.0 + 42.0) / 3)   # 0.6 x 70, flat
    up = next(r for r in curve if r["case"] == "Forward +10%")
    assert up["fair_price"] == pytest.approx(1.1 * curve[0]["fair_price"])    # whole curve

    # the model's response: capture rate 0.6 at 100, 0.5 at 70 (and 0.65 at 110)
    levels = [70.0, 100.0, 110.0]
    response = {"level": levels, "capture_rate": [0.5, 0.6, 0.65]}
    history = {LEVEL_LOW: line_response(levels, 70.0, 0.5, 0.0)}           # no level effect
    moved = tenor_rows(priced, cost, 2027, 3, 0.0, curve={2028: 70.0}, response=response,
                       history=history)
    assert moved[0]["fair_price"] == pytest.approx((60.0 + 35.0 + 35.0) / 3)   # 0.5 x 70
    up = next(r for r in moved if r["case"] == "Forward +10%")
    rate_77 = 0.5 + 0.1 * np.log(77 / 70) / np.log(100 / 70)                 # linear in ln
    assert up["fair_price"] == pytest.approx((110 * 0.65 + 2 * 77 * rate_77) / 3)
    corrected = tenor_rows(priced, cost, 2027, 3, 0.0, curve={2028: 70.0}, capture_error=0.1)
    row = next(r for r in corrected if r["case"] == OUT_OF_SAMPLE)
    assert row["fair_price"] == pytest.approx((50.0 + 35.0 + 35.0) / 3)       # 0.6 - 0.1
    low = next(r for r in moved if r["case"] == LEVEL_LOW)
    assert low["fair_price"] == pytest.approx((50.0 + 35.0 + 35.0) / 3)       # 0.5 throughout
    assert low["indicative"] == pytest.approx(low["fair_price"] - 7.5)


def test_tenor_rows_scale_the_capture_rate_by_the_build_out_factors():
    from ppa_lab.analysis.step07_report import tenor_rows, trend_case
    priced = {"stack": {"forward": 100.0, "fair_price": 60.0, "risk_premium": 5.0,
                        "balancing": 1.5, "credit": 1.0}, "energy_mwh": 1000.0}
    cost = PpaParkSettings(balancing_eur_mwh=1.5, credit_eur_mwh=1.0, capture_rate_drift=0.0,
                           degradation=0.0, buildout=True)
    base = {2027: 1.0, 2028: 0.5}
    rows = tenor_rows(priced, cost, 2027, 2, 0.0, factors=base,
                      buildout={"Build-out: storage": {2027: 1.0, 2028: 1.0}})
    cases = {r["case"]: r for r in rows}
    assert cases["Base case"]["fair_price"] == pytest.approx((60.0 + 30.0) / 2)
    assert cases["Build-out: storage"]["fair_price"] == pytest.approx(60.0)
    # the trend rows move the capture rate by whole points on top of the base path
    assert cases[trend_case(0.01)]["fair_price"] == pytest.approx((60.0 + 100 * 0.31) / 2)
