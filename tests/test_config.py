from datetime import date

import pytest

from ppa_lab.config import DEFAULT_CONFIG, load_settings


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
