"""Smoke test: the Day 2 report runs end to end on two real days of prices."""

import dataclasses
from datetime import date

import numpy as np
import pandas as pd

from conftest import FakeClient, make_power_frame
from ppa_lab.analysis.capture import capture_table, compare_monthly
from ppa_lab.analysis.day02_report import (
    complete_months,
    fig_official_gap,
    fig_solar_cannibalisation,
    monthly_comparison_text,
    negative_hours_by_month,
    solar_share_of_load,
    write_day02_report,
)
from ppa_lab.data.pipeline import build_processed, fetch
from ppa_lab.data.store import RawStore


def test_day02_report_end_to_end(settings):
    s = dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1))
    store = RawStore(s.raw_dir)
    fetch(s, FakeClient(), store, today=date(2026, 1, 1))
    build_processed(s, store)

    out = write_day02_report(s)

    text = out["report"].read_text()
    assert "Capture prices" in text
    assert out["capture_rate"].exists()
    assert "day02_capture_rate_monthly.png" in text
    # Two days never cover a whole month, so nothing is compared with monthly values.
    assert "No complete month" in text


def test_complete_months_drops_partial_first_and_last_month():
    months = complete_months(date(2023, 1, 15), date(2023, 4, 30))
    assert [str(m) for m in months] == ["2023-02", "2023-03", "2023-04"]


def test_monthly_comparison_text_summarises_each_series():
    jun, jul = pd.Period("2025-06", "M"), pd.Period("2025-07", "M")
    comparison = pd.DataFrame(
        {
            "month": [jun, jun, jul, jul],
            "series": ["spot", "solar", "spot", "solar"],
            "ours_ct_kwh": [6.399, 2.001, 8.780, 5.980],
            "official_ct_kwh": [6.399, 1.843, 8.780, 5.923],
            "difference_ct_kwh": [0.0, 0.158, 0.0, 0.057],
        }
    )
    text = monthly_comparison_text(comparison)
    assert "2 complete months compared (Jun 2025 to Jul 2025)" in text
    assert "+0.158 (Jun 2025)" in text  # largest solar difference and its month


def test_gap_and_cannibalisation_charts_render_for_several_months(tmp_path):
    # Seven synthetic months: enough for every chart (the two-day smoke test skips two).
    power = make_power_frame(date(2025, 1, 1), date(2025, 7, 31))
    local_hour = power.index.tz_convert("Europe/Berlin").hour
    price = np.where((local_hour >= 11) & (local_hour < 15), -5.0, 90.0)
    prices = pd.DataFrame({"price_eur_mwh": price, "interval_min": 15.0}, index=power.index)
    monthly = capture_table(prices, power, "Europe/Berlin", freq="M")
    official = pd.DataFrame(
        {"spot_ct_kwh": 7.0, "solar_ct_kwh": 3.0, "wind_onshore_ct_kwh": 6.5,
         "wind_offshore_ct_kwh": 6.6},
        index=pd.period_range("2025-01", "2025-07", freq="M", name="month"),
    )
    comparison = compare_monthly(monthly, official)

    gap = fig_official_gap(
        comparison, negative_hours_by_month(prices, "Europe/Berlin"), tmp_path / "gap.png"
    )
    cannibal = fig_solar_cannibalisation(
        monthly, solar_share_of_load(power, "Europe/Berlin"), tmp_path / "cannibal.png"
    )
    assert gap is not None and gap.exists()
    assert cannibal is not None and cannibal.exists()
