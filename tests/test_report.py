"""Smoke test: the whole Day 1 chain runs end to end on two real days."""

import dataclasses
from datetime import date

from conftest import FakeClient
from ppa_lab.analysis.day01_report import write_day01_report
from ppa_lab.data.pipeline import build_processed, fetch
from ppa_lab.data.store import RawStore


def test_day01_report_end_to_end(settings):
    s = dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1))
    store = RawStore(s.raw_dir)
    fetch(s, FakeClient(), store, today=date(2026, 1, 1))
    build_processed(s, store)

    out = write_day01_report(s)

    text = out["report"].read_text()
    assert "Reconciliation with published figures" in text
    assert out["switch"] is not None and out["switch"].exists()  # range includes 1 Oct 2025
    assert out["profile"] is None  # no complete calendar year in two days
    assert "day01_hourly_profile" not in text  # skipped charts are not linked
    assert out["quality"].exists()
