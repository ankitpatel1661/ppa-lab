"""End-to-end: TSO data in the raw cache -> Step 2b report (synthetic data, offline)."""

import json

import numpy as np
import pandas as pd

from conftest import write_synthetic_market
from ppa_lab.analysis.step02b_report import write_step02b_report
from ppa_lab.data.store import RawStore

TSOS = ["50Hertz (MW)", "Amprion (MW)", "TenneT TSO (MW)", "TransnetBW (MW)"]


def write_tso_cache(settings) -> None:
    """Online extrapolations 8% above the measured feed-in, reBAP around the day-ahead price,
    forecasts with noise: per month into the raw stores, as `ppa-lab tso` and `forecasts`."""
    power = pd.read_parquet(settings.processed_dir / "power_15min.parquet")
    prices = pd.read_parquet(settings.processed_dir / "prices_native.parquet")["price_eur_mwh"]
    rng = np.random.default_rng(5)
    nt = RawStore(settings.raw_dir, source="netztransparenz")
    en = RawStore(settings.raw_dir, source="entsoe")
    qh = power.index
    rebap = prices.reindex(qh).ffill() + rng.normal(0, 30, len(qh))
    forecast = pd.DataFrame({c: power[c] * (1 + rng.normal(0, 0.1, len(qh)))
                             for c in ("solar_mw", "wind_onshore_mw", "wind_offshore_mw")})
    frames = {"rebap": pd.DataFrame({"reBAP unterdeckt": rebap, "reBAP ueberdeckt": rebap})}
    for name, col in (("wind_onshore_online", "wind_onshore_mw"),
                      ("wind_offshore_online", "wind_offshore_mw"), ("solar_online", "solar_mw")):
        hourly = power[col].resample("1h").mean() * 1.08
        frames[name] = pd.DataFrame({tso: hourly / 4 for tso in TSOS})
    month = lambda f: f.index.tz_convert("UTC").strftime("%Y-%m")   # noqa: E731
    for name, frame in frames.items():
        for m, part in frame.groupby(month(frame)):
            nt.save(part, name, m, {"source": "test"})
    for m, part in forecast.groupby(month(forecast)):
        en.save(part, "wind_solar_forecast", m, {"source": "test"})


def test_step02b_report_end_to_end(settings):
    write_synthetic_market(settings)
    write_tso_cache(settings)

    out = write_step02b_report(settings)

    text = out["report"].read_text()
    assert "online extrapolation" in text and "What balancing costs" in text
    assert out["figure"].exists()
    results = json.loads(out["results"].read_text())
    cost = results["imbalance_cost_eur_mwh"]
    assert set(cost) == {"wind_onshore", "wind_offshore", "solar"}
    assert all(np.isfinite(v) for v in cost.values())
    assert set(results["by_year"]["solar"]) == {"2024", "2025"}


def test_step02b_report_explains_missing_data(settings):
    write_synthetic_market(settings)
    out = write_step02b_report(settings)
    assert "run `ppa-lab tso`" in out["report"].read_text() and out["results"] is None
