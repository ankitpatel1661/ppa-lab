from datetime import date

import pandas as pd
import pytest
import requests

from conftest import load_fixture
from ppa_lab.data.energy_charts import (
    EnergyChartsClient,
    EnergyChartsError,
    parse_price_payload,
    parse_public_power_payload,
    snake_case,
)
from ppa_lab.timeutils import interval_minutes


# --------------------------------------------------------------------------- parsing
def test_price_payload_with_resolution_switch(switch_prices):
    df = switch_prices
    assert len(df) == 24 + 96  # 30 Sep hourly + 1 Oct quarter-hourly
    assert str(df.index.tz) == "UTC"
    assert df.index[0] == pd.Timestamp("2025-09-29 22:00", tz="UTC")  # 30 Sep 00:00 CEST
    minutes = interval_minutes(df.index)
    assert set(minutes.iloc[:24]) == {60}
    assert set(minutes.iloc[24:]) == {15}


@pytest.mark.parametrize(
    ("name", "rows"),
    [("price_DE-LU_2025-03-30.json", 23), ("price_DE-LU_2025-10-26.json", 100)],
)
def test_price_payload_on_dst_days(name, rows):
    assert len(parse_price_payload(load_fixture(name))) == rows


def test_price_payload_rejects_unknown_unit():
    payload = load_fixture("price_DE-LU_2025-03-30.json") | {"unit": "EUR / kWh"}
    with pytest.raises(EnergyChartsError, match="unit"):
        parse_price_payload(payload)


def test_price_payload_rejects_length_mismatch():
    payload = load_fixture("price_DE-LU_2025-03-30.json")
    payload["price"] = payload["price"][:-1]
    with pytest.raises(EnergyChartsError, match="mismatch"):
        parse_price_payload(payload)


def test_price_payload_rejects_missing_keys():
    with pytest.raises(EnergyChartsError, match="missing"):
        parse_price_payload({"unix_seconds": []})


def test_public_power_payload():
    df = parse_public_power_payload(load_fixture("public_power_de_2025-03-30.json"))
    assert len(df) == 92  # 23 hours x 4 quarter-hours on the spring DST day
    for col in ("solar_mw", "wind_onshore_mw", "wind_offshore_mw", "load_mw",
                "fossil_brown_coal_lignite_mw", "renewable_share_of_load_pct"):
        assert col in df.columns
    assert df["solar_mw"].max() == pytest.approx(18640.3)


def test_snake_case():
    assert snake_case("Fossil brown coal / lignite") == "fossil_brown_coal_lignite"
    assert snake_case("Hydro Run-of-River") == "hydro_run_of_river"


# --------------------------------------------------------------------------- client
class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(payload)
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    """Returns queued responses (or raises queued exceptions) and records calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, params))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(responses):
    waits = []
    client = EnergyChartsClient(session=FakeSession(responses), sleep=waits.append,
                                max_retries=3, backoff_s=1.0)
    return client, waits


def test_client_retries_transient_errors():
    payload = load_fixture("price_DE-LU_2025-03-30.json")
    client, waits = make_client([FakeResponse(503), FakeResponse(200, payload)])
    df = client.day_ahead_prices("DE-LU", date(2025, 3, 30), date(2025, 3, 30))
    assert len(df) == 23
    assert waits == [1.0]  # one back-off before the successful retry


def test_client_honours_retry_after_on_rate_limit():
    """The real API answers 429 with e.g. 'Retry-After: 19' (observed 7 Oct 2026)."""
    payload = load_fixture("price_DE-LU_2025-03-30.json")
    client, waits = make_client([FakeResponse(429, headers={"Retry-After": "19"}),
                                 FakeResponse(200, payload)])
    client.get_json("price", {})
    assert waits == [20.0]  # the server's 19 s plus a 1 s safety margin


def test_client_does_not_retry_client_errors():
    client, waits = make_client([FakeResponse(400, {"detail": "bad bzn"})])
    with pytest.raises(EnergyChartsError, match="HTTP 400"):
        client.get_json("price", {"bzn": "XX"})
    assert waits == []


def test_client_gives_up_after_max_retries():
    client, waits = make_client([requests.ConnectionError("down")] * 3)
    with pytest.raises(EnergyChartsError, match="Giving up"):
        client.get_json("price", {})
    assert waits == [1.0, 2.0]  # exponential back-off


def test_client_sends_iso_dates():
    payload = load_fixture("price_DE-LU_2025-03-30.json")
    client, _ = make_client([FakeResponse(200, payload)])
    client.day_ahead_prices("DE-LU", date(2025, 3, 30), date(2025, 3, 30))
    url, params = client.session.calls[0]
    assert url.endswith("/price")
    assert params == {"bzn": "DE-LU", "start": "2025-03-30", "end": "2025-03-30"}


@pytest.mark.network
def test_live_api_contract():
    """Contract test against the real API: run with `pytest -m network`."""
    df = EnergyChartsClient().day_ahead_prices("DE-LU", date(2025, 6, 1), date(2025, 6, 1))
    assert len(df) == 24
