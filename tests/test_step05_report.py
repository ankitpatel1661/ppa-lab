"""End-to-end: calibrate the price model, validate it, simulate a delivery year, report."""

import dataclasses
from datetime import date

from conftest import write_synthetic_market
from ppa_lab.analysis.step05_report import write_step05_report
from ppa_lab.config import PriceModelSettings
from ppa_lab.prices.model import PriceModel


def small_settings(settings):
    pm = PriceModelSettings(calibration_start=date(2024, 1, 1), calibration_end=date(2025, 12, 31),
                            scale_eur_mwh=80.0, n_paths=20, seed=1, delivery_year=2026,
                            forward_eur_mwh=85.0, level_volatility=0.15)
    return dataclasses.replace(settings, start=date(2024, 1, 1), end=date(2025, 12, 31),
                               price_model=pm)


def test_step05_report_end_to_end(settings):
    s = small_settings(settings)
    write_synthetic_market(s)

    out = write_step05_report(s)

    text = out["report"].read_text()
    assert "half-life" in text and "Validation" in text
    model = PriceModel.load(out["model"])
    assert -1 < model.phi < 1  # the synthetic market has no day-to-day memory: phi near 0
    for key in ("profile", "distribution", "paths"):
        assert out[key].exists()
    assert "2026" in text and "85.0" in text          # the delivery year and its forward
    assert "No site generation" in text                 # Step 4 output absent: teaser skipped
