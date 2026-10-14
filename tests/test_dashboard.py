"""Dashboard logic: from the committed results file to an offer for any assumptions."""

import json

import pytest

from ppa_lab.dashboard import Assumptions, default_assumptions, load_results, offer
from ppa_lab.pricing.risk import tenor_price


def results_fixture() -> dict:
    """The shape of reports/results.json, with simple numbers."""
    return {
        "delivery_year": 2027, "tenor_years": 10, "discount_rate": 0.06,
        "analog_pool_start": "2025-10-01",
        "parks": {"solar_park": {
            "stack_eur_mwh": {"forward": 80.0, "shape": -40.0, "fair_price": 40.0,
                              "risk_premium": 5.0, "balancing": 1.5, "credit": 1.0,
                              "indicative": 32.5},
            "whole_window": {"fair_price": 48.0, "premium": 5.5},
            "energy_mwh_expected": 55_000.0,
            "assumptions": {"balancing_eur_mwh": 1.5, "credit_eur_mwh": 1.0,
                            "capture_rate_drift": 0.0, "degradation": 0.005},
        }},
    }


def test_default_assumptions_reproduce_the_step07_answer():
    r = results_fixture()
    a = default_assumptions(r, "solar_park")
    assert a == Assumptions(balancing=1.5, credit=1.0, drift=0.0, degradation=0.005,
                            discount_rate=0.06, tenor_years=10)
    o = offer(r, "solar_park", a)
    assert o["stack"]["indicative"] == pytest.approx(32.5)      # flat: tenor price = year 1
    assert len(o["years"]) == 10


def test_the_stack_adds_up_and_shows_the_trend():
    r = results_fixture()
    a = Assumptions(balancing=2.0, credit=0.5, drift=-0.01, degradation=0.0,
                    discount_rate=0.06, tenor_years=10)
    s = offer(r, "solar_park", a)["stack"]
    expected = tenor_price(40.0, 80.0, 55_000.0, 2027, 10, 0.06, capture_rate_drift=-0.01)
    assert s["tenor_fair_price"] == pytest.approx(expected.attrs["price"])
    assert s["trend"] == pytest.approx(s["tenor_fair_price"] - 40.0) and s["trend"] < 0
    assert s["indicative"] == pytest.approx(
        s["forward"] + s["shape"] + s["trend"] - s["risk_premium"] - s["balancing"] - s["credit"])


def test_the_whole_window_pool_and_a_forward_shift():
    r = results_fixture()
    base = default_assumptions(r, "solar_park")
    whole = offer(r, "solar_park", Assumptions(**{**base.__dict__, "pool": "whole"}))["stack"]
    assert whole["fair_price"] == pytest.approx(48.0) and whole["risk_premium"] == 5.5
    shifted = offer(r, "solar_park", Assumptions(**{**base.__dict__, "forward_shift": -0.1}))
    assert shifted["stack"]["forward"] == pytest.approx(72.0)
    assert shifted["stack"]["fair_price"] == pytest.approx(36.0)   # same capture rate
    assert shifted["stack"]["risk_premium"] == 5.0


def test_missing_results_say_how_to_make_them(tmp_path):
    with pytest.raises(FileNotFoundError, match="ppa-lab memo"):
        load_results(tmp_path / "results.json")
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results_fixture()))
    assert load_results(path)["delivery_year"] == 2027


def test_structures_table_is_in_eur_millions():
    from ppa_lab.dashboard import structures_table
    r = results_fixture()
    r["parks"]["solar_park"]["structures"] = {
        "merchant": {"fair_price_eur_mwh": None, "expected_revenue_eur": 2.26e6,
                     "p05_revenue_eur": 0.82e6, "cfar_eur": 1.44e6},
        "pay_as_produced": {"fair_price_eur_mwh": 41.1, "expected_revenue_eur": 2.26e6,
                            "p05_revenue_eur": 2.06e6, "cfar_eur": 0.20e6}}
    t = structures_table(r, "solar_park")
    assert t.loc["merchant", "Cash flow at risk 95% (EUR m)"] == pytest.approx(1.44)
    assert t.loc["pay_as_produced", "Strike (EUR/MWh)"] == pytest.approx(41.1)


def test_hedging_table_when_step8_results_are_published():
    from ppa_lab.dashboard import hedging_table
    r = results_fixture()
    assert hedging_table(r, "solar_park") is None              # no Step 8 results yet
    r["hedging"] = {"parks": {"solar_park": {"strategies": {
        "none": {"hedge_mw": 0.0, "hedge_ratio": 0.0, "cfar_eur": 1.44e6, "cfar_reduction": 0.0,
                 "effectiveness": 0.0},
        "cal_base_min_variance": {"hedge_mw": 5.6, "hedge_ratio": 0.89, "cfar_eur": 0.27e6,
                                  "cfar_reduction": 0.81, "effectiveness": 0.97}}}}}
    t = hedging_table(r, "solar_park")
    assert list(t.index) == ["No hedge (merchant)", "Cal base, minimum-variance"]
    assert t.loc["Cal base, minimum-variance", "CFaR95 (EUR m)"] == pytest.approx(0.27)
    assert t.loc["Cal base, minimum-variance", "Hedge ratio (%)"] == pytest.approx(89.0)
