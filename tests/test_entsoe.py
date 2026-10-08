"""ENTSO-E parser and client tests.

The XML below is SYNTHETIC but follows the structure of real A44 responses
(namespace, TimeSeries/Period/Point, curve type A03 with an omitted point).
Replace it with a saved real response when the full ENTSO-E client is built.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
import requests

from ppa_lab.data.entsoe import EntsoeClient, EntsoeError, load_api_key, parse_day_ahead_xml

FIXTURES = Path(__file__).parent / "fixtures"

A44_XML = """<?xml version="1.0" encoding="utf-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <TimeSeries>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2025-05-31T22:00Z</start><end>2025-06-01T02:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><price.amount>80.5</price.amount></Point>
      <Point><position>2</position><price.amount>75.0</price.amount></Point>
      <Point><position>4</position><price.amount>-1.2</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""

ACK_XML = """<?xml version="1.0" encoding="utf-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0">
  <Reason>
    <code>999</code><text>No matching data found for Data item Day-ahead Prices</text>
  </Reason>
</Acknowledgement_MarketDocument>"""


def test_parse_forward_fills_points_omitted_by_curve_type_a03():
    df = parse_day_ahead_xml(A44_XML)
    assert df["price_eur_mwh"].tolist() == [80.5, 75.0, 75.0, -1.2]  # position 3 omitted
    assert df.index[0] == pd.Timestamp("2025-05-31 22:00", tz="UTC")
    assert str(df.index.tz) == "UTC"
    assert set(df["resolution_min"]) == {60.0}


def test_real_response_contains_two_auction_sequences():
    """Real ENTSO-E answer for 1 Oct 2025 (saved 8 Oct 2026, no token inside).

    DE-LU has two day-ahead price series, told apart by
    classificationSequence position: 1 = the SDAC auction (identical to SMARD /
    Energy-Charts), 2 = a second day-ahead auction with different prices.
    """
    xml = (FIXTURES / "entsoe_A44_DE-LU_2025-10-01.xml").read_bytes()
    df = parse_day_ahead_xml(xml)
    assert df["sequence"].value_counts().to_dict() == {1: 96, 2: 96}
    sdac = df[df["sequence"] == 1]
    assert sdac.index.is_unique and len(sdac) == 96  # 95 points + 1 forward-filled (A03)
    assert sdac["price_eur_mwh"].max() == pytest.approx(408.50)
    assert sdac["price_eur_mwh"].mean() == pytest.approx(116.57, abs=0.01)


def test_client_returns_only_the_sdac_sequence_by_default():
    xml = (FIXTURES / "entsoe_A44_DE-LU_2025-10-01.xml").read_text()
    client = EntsoeClient(api_key="SECRET", session=FakeSession(FakeResponse(200, xml)))
    df = client.day_ahead_prices("DE-LU", date(2025, 10, 1), date(2025, 10, 1))
    assert len(df) == 96 and df.index.is_unique
    assert set(df["sequence"]) == {1}
    both = client.day_ahead_prices("DE-LU", date(2025, 10, 1), date(2025, 10, 1), sequence=None)
    assert len(both) == 192


def test_acknowledgement_document_becomes_a_clear_error():
    with pytest.raises(EntsoeError, match="No matching data found"):
        parse_day_ahead_xml(ACK_XML)


def test_invalid_xml_is_rejected():
    with pytest.raises(EntsoeError, match="not valid XML"):
        parse_day_ahead_xml("<html>Service unavailable")


def test_api_key_from_environment_or_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("ENTSOE_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("# comment\nENTSOE_API_KEY='abc-123'\n")
    assert load_api_key(env) == "abc-123"
    monkeypatch.setenv("ENTSOE_API_KEY", "from-env")
    assert load_api_key(env) == "from-env"  # environment wins
    monkeypatch.delenv("ENTSOE_API_KEY")
    assert load_api_key(tmp_path / "missing.env") is None


class FakeResponse:
    def __init__(self, status_code, content):
        self.status_code, self.content = status_code, content.encode()


class FakeSession:
    def __init__(self, result):
        self.result, self.params = result, None

    def get(self, url, params=None, timeout=None):
        self.params = params
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_request_uses_utc_period_for_a_local_delivery_day():
    session = FakeSession(FakeResponse(200, A44_XML))
    EntsoeClient(api_key="SECRET", session=session).day_ahead_prices(
        "DE-LU", date(2025, 6, 1), date(2025, 6, 1)
    )
    assert session.params["periodStart"] == "202505312200"  # 1 Jun 00:00 CEST
    assert session.params["periodEnd"] == "202506012200"
    assert session.params["in_Domain"] == "10Y1001A1001A82H"


def test_token_never_leaks_through_errors_or_repr():
    leaky = requests.ConnectionError("GET https://web-api.tp.entsoe.eu/api?securityToken=SECRET")
    client = EntsoeClient(api_key="SECRET", session=FakeSession(leaky))
    with pytest.raises(EntsoeError) as info:
        client.day_ahead_prices("DE-LU", date(2025, 6, 1), date(2025, 6, 1))
    assert "SECRET" not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__
    assert "SECRET" not in repr(client)


def test_unauthorized_token_gives_actionable_message():
    client = EntsoeClient(api_key="WRONG", session=FakeSession(FakeResponse(401, "")))
    with pytest.raises(EntsoeError, match="401"):
        client.day_ahead_prices("DE-LU", date(2025, 6, 1), date(2025, 6, 1))
