"""The one-page management memo and the results file for the dashboard."""

import json

from ppa_lab.analysis.step09_memo import write_step09_memo


def pricing_fixture() -> dict:
    """The shape of data/processed/ppa_pricing.json (Step 7), with round numbers."""
    def park(fair, premium, indicative, cfar_m, cfar_p, p50):
        return {
            "stack_eur_mwh": {"forward": 85.0, "shape": fair - 85.0, "fair_price": fair,
                              "risk_premium": premium, "balancing": 1.5, "credit": 1.0,
                              "indicative": indicative},
            "premia_eur_mwh": {"fair_price": fair, "unhedged": 25.0, "joint": premium,
                               "profile": premium - 0.5, "volume": 0.5},
            "structures": {"merchant": {"cfar_eur": cfar_m, "expected_revenue_eur": 2.2e6},
                           "pay_as_produced": {"cfar_eur": cfar_p, "expected_revenue_eur": 2.2e6},
                           "pay_as_produced_clause": {"cfar_eur": cfar_p,
                                                      "expected_revenue_eur": 1.65e6}},
            "energy_mwh_expected": p50, "p50_mwh": p50, "p90_1y_mwh": 0.93 * p50,
            "whole_window": {"fair_price": fair + 7.0, "premium": premium},
            "assumptions": {"balancing_eur_mwh": 1.5, "credit_eur_mwh": 1.0,
                            "capture_rate_drift": 0.0, "degradation": 0.005},
            "tenor": {"years": list(range(2027, 2037)), "fair_price": fair,
                      "indicative": indicative,
                      "sensitivity": [
                          {"case": "Base case", "fair_price": fair, "indicative": indicative},
                          {"case": "Capture rate -1 pp per year", "fair_price": fair - 3,
                           "indicative": indicative - 3},
                          {"case": "Capture rate +1 pp per year", "fair_price": fair + 3,
                           "indicative": indicative + 3},
                          {"case": "Forward −10%", "fair_price": fair - 4,
                           "indicative": indicative - 4},
                          {"case": "Forward +10%", "fair_price": fair + 4,
                           "indicative": indicative + 4},
                          {"case": "Analog days from the whole window", "fair_price": fair + 7,
                           "indicative": indicative + 7}]},
        }
    return {"delivery_year": 2027, "tenor_years": 10, "discount_rate": 0.06,
            "analog_pool_start": "2025-10-01", "scenarios": 496, "forward_assumption": 85.0,
            "parks": {"solar_park": park(40.0, 5.0, 32.5, 1.4e6, 0.2e6, 55_000.0),
                      "wind_park": park(75.0, 3.5, 68.5, 3.0e6, 0.7e6, 110_000.0)}}


def test_memo_states_the_answer_and_publishes_the_results(settings):
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    (settings.processed_dir / "ppa_pricing.json").write_text(json.dumps(pricing_fixture()))

    out = write_step09_memo(settings, pdf=False)

    text = out["memo"].read_text()
    assert "Bottom line" in text and "32.5" in text and "40.0" in text   # indicative and fair
    assert "2027-2036" in text and "Lusatia" in text
    assert "−86%" in text                                    # CFaR 1.4 m -> 0.2 m
    assert "6.0 EUR/MWh" in text                             # premium + credit vs merchant
    assert "25% of the solar output" in text                 # clause: 1 - 1.65 / 2.2
    assert "±3.0 EUR/MWh" in text and "+7.0 EUR/MWh" in text # the levers
    assert len(text.splitlines()) < 75                        # one page
    published = json.loads(out["results"].read_text())
    assert published["parks"]["solar_park"]["stack_eur_mwh"]["indicative"] == 32.5
    assert out["pdf"] is None


def test_memo_without_pricing_results_says_what_to_run(settings):
    out = write_step09_memo(settings, pdf=False)
    assert "run `ppa-lab pricing` first" in out["memo"].read_text()
    assert out["results"] is None
