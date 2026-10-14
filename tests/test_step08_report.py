"""End-to-end: scenarios -> hedging strategies, buyer's hedge, back-test, market check."""

import dataclasses
import json
from datetime import date

from conftest import FakeWeatherClient, write_synthetic_market
from ppa_lab.analysis.step07_report import write_step07_report
from ppa_lab.analysis.step08_report import write_step08_report
from ppa_lab.config import HedgingSettings, MarketQuote
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather
from test_step07_report import small_settings as step07_settings


def small_settings(settings):
    s = step07_settings(settings)
    quote = MarketQuote(product="cal_base", delivery_year=2026, price_eur_mwh=95.0,
                        date=date(2025, 12, 1), source="https://example.org/quote")
    return dataclasses.replace(s, hedging=HedgingSettings(backtest_years=(2025,),
                                                          market_quotes=(quote,)))


def test_step08_report_end_to_end(settings):
    s = small_settings(settings)
    store = RawStore(s.raw_dir, source="open_meteo")
    fetch_weather(s, FakeWeatherClient(), store, today=date(2026, 6, 1))
    build_generation(s, store)
    write_synthetic_market(s)
    write_step07_report(s)                       # the market check reuses the Step 7 results

    out = write_step08_report(s)

    text = out["report"].read_text()
    for phrase in ("minimum-variance", "Back-test", "Market check", "95.0", "example.org"):
        assert phrase in text
    for key in ("cfar", "months", "distribution"):
        assert out[key].exists()
    results = json.loads(out["results"].read_text())
    solar = results["parks"]["solar_park"]
    assert set(solar["strategies"]) >= {"none", "cal_base_100", "cal_base_min_variance"}
    assert solar["strategies"]["none"]["effectiveness"] == 0.0
    assert solar["backtest"]["2025"]["forward_proxy"] > 0
    assert solar["buyer"]["premium_min_variance"] <= solar["buyer"]["premium_full_band"] + 1e-9


def test_step08_report_explains_missing_weather(settings):
    s = small_settings(settings)
    write_synthetic_market(s)

    out = write_step08_report(s)

    assert "run `ppa-lab weather` first" in out["report"].read_text()
    assert out["results"] is None
