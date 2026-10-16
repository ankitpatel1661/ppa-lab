"""netztransparenz.de client: credentials, OAuth token, retries, CSV parsing (offline)."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from ppa_lab.data.netztransparenz import (
    ID_VAR,
    SECRET_VAR,
    NetztransparenzClient,
    NetztransparenzError,
    load_credentials,
    parse_csv,
)

# The example of the API's own documentation, plus a CET row.
CSV = ("Datum;von;Zeitzone von;bis;Zeitzone bis;50Hertz (MW);Amprion (MW);TenneT TSO (MW);"
       "TransnetBW (MW)\n"
       "2011-03-31;21:45;UTC;22:00;UTC;N.A.;N.A.;N.A.;N.A.\n"
       "2011-03-31;22:00;UTC;22:15;UTC;0,00;0,00;0,00;0,00\n"
       "2011-04-01;07:45;UTC;08:00;UTC;598,00;716,00;1.188,17;604,90\n"
       "01.04.2011;10:00;CEST;10:15;CEST;1,5;-2,25;3;NE\n")


def test_parse_csv_reads_german_numbers_and_time_zones():
    frame = parse_csv(CSV)
    assert list(frame.columns) == ["50Hertz (MW)", "Amprion (MW)", "TenneT TSO (MW)",
                                   "TransnetBW (MW)"]
    assert str(frame.index.tz) == "UTC" and frame.index.name == "ts_utc"
    utc = pd.Timestamp("2011-04-01 07:45", tz="UTC")
    assert frame.loc[utc, "TenneT TSO (MW)"] == pytest.approx(1188.17)
    assert np.isnan(frame.iloc[0, 0])                               # N.A.
    assert frame.index[-1] == pd.Timestamp("2011-04-01 08:00", tz="UTC")   # 10:00 CEST
    assert frame.loc[pd.Timestamp("2011-04-01 08:00", tz="UTC"), "Amprion (MW)"] == -2.25


REBAP = ("Datum;Zeitzone;von;bis;Datenkategorie;Datentyp;Einheit;reBAP unterdeckt;"
         "reBAP ueberdeckt\n"
         "01.01.2025;UTC;10:00;10:15;reBAP;Qualitätsgesichert;EUR/MWh;-144,02;-144,02\n"
         "01.01.2025;UTC;10:15;10:30;reBAP;Qualitätsgesichert;EUR/MWh;1.069,36;-69,36\n")


def test_parse_csv_reads_the_rebap_layout():
    frame = parse_csv(REBAP)
    assert list(frame.columns) == ["reBAP unterdeckt", "reBAP ueberdeckt"]
    assert frame.index[0] == pd.Timestamp("2025-01-01 10:00", tz="UTC")
    assert frame.iloc[1].tolist() == [1069.36, -69.36]


def test_parse_csv_refuses_unknown_layouts():
    with pytest.raises(NetztransparenzError, match="unexpected columns"):
        parse_csv("a;b;c\n1;2;3\n")


def test_credentials_from_the_environment_or_a_dotenv_file(tmp_path, monkeypatch):
    monkeypatch.delenv(ID_VAR, raising=False)
    monkeypatch.delenv(SECRET_VAR, raising=False)
    env = tmp_path / ".env"
    assert load_credentials(env) is None
    env.write_text(f"OTHER=1\n{ID_VAR}=abc\n{SECRET_VAR}='s3cret'\n")
    assert load_credentials(env) == ("abc", "s3cret")
    monkeypatch.setenv(ID_VAR, "from-env")
    monkeypatch.setenv(SECRET_VAR, "x")
    assert load_credentials(env) == ("from-env", "x")


class FakeResponse:
    def __init__(self, status, text="", body=None):
        self.status_code, self.text, self._body = status, text, body

    def json(self):
        return self._body


class FakeSession:
    """Token endpoint and data endpoint with scripted answers; records what was sent."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.posts, self.gets = [], []

    def post(self, url, timeout, data):
        self.posts.append(data)
        return FakeResponse(200, body={"access_token": f"t{len(self.posts)}", "expires_in": 3600})

    def get(self, url, timeout, headers):
        self.gets.append((url, headers["Authorization"]))
        return self.answers.pop(0)


def test_client_uses_client_credentials_and_bearer_tokens():
    session = FakeSession([FakeResponse(200, CSV)])
    client = NetztransparenzClient("id", "secret", session=session, sleep=lambda s: None)
    frame = client.fetch("rebap", datetime(2011, 3, 31, 21, 45), datetime(2011, 4, 1, 8, 0))
    assert len(frame) == 4
    assert session.posts == [{"grant_type": "client_credentials", "client_id": "id",
                              "client_secret": "secret"}]
    url, auth = session.gets[0]
    assert url.endswith("/api/v1/data/NrvSaldo/reBAP/Qualitaetsgesichert/"
                        "2011-03-31T21:45:00/2011-04-01T08:00:00")
    assert auth == "Bearer t1"
    assert "secret" not in repr(client)                    # never printed


def test_client_renews_an_expired_token_and_backs_off_on_rate_limits():
    session = FakeSession([FakeResponse(401), FakeResponse(429), FakeResponse(200, CSV)])
    waits = []
    client = NetztransparenzClient("id", "secret", session=session, sleep=waits.append)
    client.get_text("NrvSaldo/reBAP/Qualitaetsgesichert", datetime(2024, 1, 1),
                    datetime(2024, 1, 2))
    assert [a for _, a in session.gets] == ["Bearer t1", "Bearer t2", "Bearer t2"]
    assert waits == [4.0]                                  # the 429 waited, the 401 did not


def test_client_gives_up_on_other_errors():
    session = FakeSession([FakeResponse(400, "bad request")])
    client = NetztransparenzClient("id", "secret", session=session, sleep=lambda s: None)
    with pytest.raises(NetztransparenzError, match="HTTP 400"):
        client.get_text("NrvSaldo/reBAP/Qualitaetsgesichert", datetime(2024, 1, 1),
                        datetime(2024, 1, 2))
    with pytest.raises(NetztransparenzError, match="unknown dataset"):
        client.fetch("nonsense", datetime(2024, 1, 1), datetime(2024, 1, 2))


def test_fetch_tso_stores_months_and_skips_cached_ones(tmp_path):
    from ppa_lab.data.netztransparenz import fetch_tso
    from ppa_lab.data.store import RawStore

    def month_csv(month):
        days = pd.date_range(f"{month}-01", periods=3, freq="D")
        rows = "".join(f"{d:%Y-%m-%d};00:00;UTC;00:15;UTC;1,0;2,0\n" for d in days)
        return "Datum;von;Zeitzone von;bis;Zeitzone bis;A;B\n" + rows

    session = FakeSession([FakeResponse(200, month_csv("2024-01")),
                           FakeResponse(200, month_csv("2024-02")),
                           FakeResponse(200, month_csv("2024-02"))])
    client = NetztransparenzClient("id", "secret", session=session, sleep=lambda s: None)
    store = RawStore(tmp_path, source="netztransparenz")
    today = pd.Timestamp("2024-02-15", tz="UTC")
    first = fetch_tso(client, store, ["rebap"], datetime(2024, 1, 1), datetime(2024, 2, 10),
                      today=today)
    assert [a for *_, a in first] == ["downloaded", "downloaded"]
    assert store.months("rebap") == ["2024-01", "2024-02"]
    again = fetch_tso(client, store, ["rebap"], datetime(2024, 1, 1), datetime(2024, 2, 10),
                      today=today)
    assert [a for *_, a in again] == ["cached", "downloaded"]   # the current month again
    assert len(store.load("rebap")) == 6


def test_the_tso_command_explains_missing_credentials(tmp_path, monkeypatch, caplog):
    import ppa_lab.cli as cli
    monkeypatch.delenv(ID_VAR, raising=False)
    monkeypatch.delenv(SECRET_VAR, raising=False)
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)            # a folder without .env
    assert cli.main(["tso"]) == 2
    assert "api-portal.netztransparenz.de" in caplog.text
