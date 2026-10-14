"""The command line is what automation (cron, Airflow, CI) calls, so its exit codes matter."""

import dataclasses
from datetime import date

import pandas as pd
import pytest

from conftest import FakeClient, FakeWeatherClient, write_synthetic_market
from ppa_lab import cli


@pytest.fixture
def two_day_settings(settings, monkeypatch):
    s = dataclasses.replace(settings, start=date(2025, 9, 30), end=date(2025, 10, 1),
                            weather_first_year=2025)
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    monkeypatch.setattr(cli, "_client", lambda _settings: FakeClient())
    monkeypatch.setattr(cli, "_weather_client", lambda _settings: FakeWeatherClient())
    return s


def test_parser_defaults():
    args = cli.build_parser().parse_args(["fetch"])
    assert args.datasets == ["prices", "power"]
    assert args.refresh is False


def test_all_runs_the_whole_pipeline(two_day_settings):
    assert cli.main(["all"]) == 0
    assert (two_day_settings.reports_dir / "step01_market_data.md").exists()
    assert (two_day_settings.reports_dir / "step02_capture_prices.md").exists()
    # Two days contain no complete year before a delivery year: Step 3 is skipped, not failed.
    assert not (two_day_settings.reports_dir / "step03_ppa_structures.md").exists()
    # Step 4 runs (weather is fetched for 2025) and says it lacks complete weather years.
    assert (two_day_settings.reports_dir / "step04_generation.md").exists()
    # The price model's calibration window lies outside two days: Steps 5 and 6 are skipped.
    assert not (two_day_settings.reports_dir / "step05_price_model.md").exists()
    assert not (two_day_settings.reports_dir / "step06_joint_scenarios.md").exists()
    assert not (two_day_settings.reports_dir / "step07_ppa_pricing.md").exists()


def test_prices_command_writes_the_step05_report(settings, monkeypatch):
    import dataclasses as dc

    from test_step05_report import small_settings
    s = small_settings(settings)
    write_synthetic_market(s)
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    assert cli.main(["prices"]) == 0
    assert (s.reports_dir / "step05_price_model.md").exists()
    assert dc.is_dataclass(s.price_model)


def test_scenarios_command_writes_the_step06_report(settings, monkeypatch):
    from test_step06_report import small_settings
    s = small_settings(settings)
    write_synthetic_market(s)
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    monkeypatch.setattr(cli, "_weather_client", lambda _settings: FakeWeatherClient())
    assert cli.main(["weather"]) == 0
    assert cli.main(["scenarios"]) == 0
    assert (s.reports_dir / "step06_joint_scenarios.md").exists()
    assert (s.processed_dir / "scenarios_2026.parquet").exists()


def test_pricing_command_writes_the_step07_report(settings, monkeypatch):
    from test_step07_report import small_settings
    s = small_settings(settings)
    write_synthetic_market(s)
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    monkeypatch.setattr(cli, "_weather_client", lambda _settings: FakeWeatherClient())
    assert cli.main(["weather"]) == 0
    assert cli.main(["pricing"]) == 0
    assert (s.reports_dir / "step07_ppa_pricing.md").exists()
    assert (s.processed_dir / "ppa_pricing.json").exists()


def test_weather_command_builds_generation_and_the_step04_report(settings, monkeypatch):
    s = dataclasses.replace(settings, start=date(2024, 1, 1), end=date(2025, 12, 31),
                            weather_first_year=2024)
    write_synthetic_market(s)
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    monkeypatch.setattr(cli, "_weather_client", lambda _settings: FakeWeatherClient())
    assert cli.main(["weather"]) == 0
    assert (s.processed_dir / "generation_solar_park.parquet").exists()
    assert (s.reports_dir / "step04_generation.md").exists()


def test_ppa_command_writes_the_step03_report(settings, monkeypatch):
    s = dataclasses.replace(settings, start=date(2024, 1, 1), end=date(2025, 12, 31))
    write_synthetic_market(s)
    monkeypatch.setattr(cli, "load_settings", lambda path=None: s)
    assert cli.main(["ppa"]) == 0
    assert (s.reports_dir / "step03_ppa_structures.md").exists()


def test_capture_command_writes_the_step02_report(two_day_settings):
    assert cli.main(["fetch"]) == 0
    assert cli.main(["build"]) == 0
    assert cli.main(["capture"]) == 0
    assert (two_day_settings.reports_dir / "step02_capture_prices.md").exists()


def test_check_fails_with_exit_code_1_on_bad_data(two_day_settings):
    assert cli.main(["fetch"]) == 0
    assert cli.main(["build"]) == 0
    assert cli.main(["check"]) == 0

    path = two_day_settings.processed_dir / "prices_native.parquet"
    prices = pd.read_parquet(path)
    prices.iloc[0, 0] = 9999.0  # impossible price: above the +4000 EUR/MWh limit
    prices.to_parquet(path)
    assert cli.main(["check"]) == 1  # automation must stop here
