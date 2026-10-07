"""The command line is what automation (cron, Airflow, CI) calls, so its exit codes matter."""

import dataclasses
from datetime import date

import pandas as pd
import pytest

from conftest import FakeClient
from ppa_lab import cli


@pytest.fixture
def two_day_settings(settings, monkeypatch):
    s = dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1))
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    monkeypatch.setattr(cli, "_client", lambda _settings: FakeClient())
    return s


def test_parser_defaults():
    args = cli.build_parser().parse_args(["fetch"])
    assert args.datasets == ["prices", "power"]
    assert args.refresh is False


def test_all_runs_the_whole_pipeline(two_day_settings):
    assert cli.main(["all"]) == 0
    assert (two_day_settings.reports_dir / "day01_market_data.md").exists()


def test_check_fails_with_exit_code_1_on_bad_data(two_day_settings):
    assert cli.main(["fetch"]) == 0
    assert cli.main(["build"]) == 0
    assert cli.main(["check"]) == 0

    path = two_day_settings.processed_dir / "prices_native.parquet"
    prices = pd.read_parquet(path)
    prices.iloc[0, 0] = 9999.0  # impossible price: above the +4000 EUR/MWh limit
    prices.to_parquet(path)
    assert cli.main(["check"]) == 1  # automation must stop here
