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
                          {"case": "Capture-rate trend 1 pp/yr steeper", "fair_price": fair - 3,
                           "indicative": indicative - 3},
                          {"case": "Capture-rate trend 1 pp/yr flatter", "fair_price": fair + 3,
                           "indicative": indicative + 3},
                          {"case": "Forward −10%", "fair_price": fair - 4,
                           "indicative": indicative - 4},
                          {"case": "Forward +10%", "fair_price": fair + 4,
                           "indicative": indicative + 4},
                          {"case": "Analog days from the whole window", "fair_price": fair + 7,
                           "indicative": indicative + 7},
                          {"case": "Capture rate vs price level: low end of history",
                           "fair_price": fair - 2, "indicative": indicative - 2},
                          {"case": "Capture rate less the model's out-of-sample error",
                           "fair_price": fair - 12, "indicative": indicative - 12}]},
            "level_effect": {"history": {"coef": 0.27, "ci_low": 0.10, "ci_high": 0.45},
                             "history_years": "2023-2026", "out_of_sample_error": 0.123},
        }
    return {"delivery_year": 2027, "tenor_years": 10, "discount_rate": 0.06,
            "analog_pool_start": "2025-10-01", "scenarios": 496,
            "forward": {"price_eur_mwh": 85.0, "date": "2026-10-09",
                        "source": "https://www.tacto.ai/en/energy/electricity-price"},
            "forward_curve": {"2028": 70.0, "2029": 60.0}, "recent_level_eur_mwh": 104.0,
            "parks": {"solar_park": park(40.0, 5.0, 32.5, 1.4e6, 0.2e6, 55_000.0),
                      "wind_park": park(75.0, 3.5, 68.5, 3.0e6, 0.7e6, 110_000.0)}}


def test_memo_states_the_answer_and_publishes_the_results(settings):
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    (settings.processed_dir / "ppa_pricing.json").write_text(json.dumps(pricing_fixture()))

    out = write_step09_memo(settings, pdf=False)

    text = out["memo"].read_text()
    assert "Bottom line" in text and "32.5" in text and "40.0" in text   # indicative and fair
    assert "2027-2036" in text and "Borrentin" in text
    assert "−86%" in text                                    # CFaR 1.4 m -> 0.2 m
    assert "6.0 EUR/MWh" in text                             # premium + credit vs merchant
    assert "25% of the solar output" in text                 # clause: 1 - 1.65 / 2.2
    assert "±3.0 EUR/MWh" in text and "+7.0 EUR/MWh" in text # the levers
    assert "Forward curve −10% / +10%: **−4.0 / +4.0 EUR/MWh**" in text
    assert "Cal-27 base 85.00 EUR/MWh (quote of 2026-10-09, via tacto.ai)" in text
    assert "out of sample in earlier years (+0.12, Step 6): **−12.0 EUR/MWh**" in text
    assert "2028: 70.00, 2029: 60.00" in text and "Later years: forward curve falls" in text
    assert len(text.splitlines()) < 75                        # one page
    published = json.loads(out["results"].read_text())
    assert published["parks"]["solar_park"]["stack_eur_mwh"]["indicative"] == 32.5
    assert out["pdf"] is None


def test_memo_without_pricing_results_says_what_to_run(settings):
    out = write_step09_memo(settings, pdf=False)
    assert "run `ppa-lab pricing` first" in out["memo"].read_text()
    assert out["results"] is None


def hedging_fixture() -> dict:
    """The shape of data/processed/hedging.json (Step 8)."""
    strategies = {"none": {"hedge_mw": 0.0, "hedge_ratio": 0.0, "cfar_eur": 1.4e6,
                           "cfar_reduction": 0.0, "effectiveness": 0.0},
                  "cal_base_min_variance": {"hedge_mw": 5.6, "hedge_ratio": 0.89,
                                            "cfar_eur": 0.27e6, "cfar_reduction": 0.81,
                                            "effectiveness": 0.97}}
    park = {"strategies": strategies,
            "buyer": {"premium_full_band": 5.0, "premium_min_variance": 4.2,
                      "min_variance_ratio": 0.9},
            "market_check": {"quote": 113.45, "date": "2026-08-28", "model_forward": 85.4,
                             "indicative_model": 32.5, "indicative_market": 46.8}}
    return {"delivery_year": 2027, "parks": {"solar_park": park, "wind_park": park}}


def test_memo_uses_the_hedging_results_when_present(settings):
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    (settings.processed_dir / "ppa_pricing.json").write_text(json.dumps(pricing_fixture()))
    (settings.processed_dir / "hedging.json").write_text(json.dumps(hedging_fixture()))

    out = write_step09_memo(settings, pdf=False)

    text = out["memo"].read_text()
    assert "89%" in text and "81%" in text                     # the hedge recommendation
    assert "113.45" in text and "46.8" in text                 # the market check
    assert len(text.splitlines()) < 80
    published = json.loads(out["results"].read_text())
    assert published["hedging"]["parks"]["solar_park"]["buyer"]["premium_min_variance"] == 4.2


def test_memo_anchored_to_the_market_says_how_far_the_forward_moved(settings):
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    (settings.processed_dir / "ppa_pricing.json").write_text(json.dumps(pricing_fixture()))
    hedging = hedging_fixture()
    for park in hedging["parks"].values():
        park["market_check"] = {**park["market_check"], "quote": 85.2, "model_forward": 85.4}
    hedging["market_quotes"] = [
        {"product": "cal_base", "delivery_year": 2027, "price_eur_mwh": p, "date": d}
        for p, d in ((104.24, "2026-07-31"), (140.21, "2026-10-09"), (119.48, "2026-08-28"))]
    (settings.processed_dir / "hedging.json").write_text(json.dumps(hedging))

    text = write_step09_memo(settings, pdf=False)["memo"].read_text()
    assert "moved between 104 and 140 EUR/MWh since 2026-07-31" in text
    assert "differs from the model" not in text
