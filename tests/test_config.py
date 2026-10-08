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
