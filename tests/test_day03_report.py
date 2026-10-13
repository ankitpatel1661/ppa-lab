"""End-to-end: the Day 3 report runs on two full synthetic years (the strikes need Y-1)."""

import dataclasses
from datetime import date

from conftest import write_synthetic_market
from ppa_lab.analysis.day03_report import write_day03_report


def test_day03_report_end_to_end(settings):
    s = dataclasses.replace(
        settings, start=date(2024, 1, 1), end=date(2025, 12, 31), delivery_years=(2025,)
    )
    write_synthetic_market(s)

    out = write_day03_report(s)

    text = out["report"].read_text()
    assert "Pay-as-produced PPA" in text and "Baseload PPA" in text
    assert out["annual"].exists() and out["monthly"].exists()
    assert "day03_structures_annual.png" in text
