"""ERA5 weather from the Open-Meteo archive API.

Fixture: a REAL response for the solar site (51.75 N, 14.25 E), 14-15 June 2025, saved
on 13 Oct 2026. Open-Meteo labels radiation at the END of its hour (mean of the
preceding hour) and gives wind and temperature as instantaneous values.
"""

from datetime import date

import pandas as pd
import pytest

from conftest import load_fixture
from ppa_lab.data.open_meteo import (
    OpenMeteoClient,
    OpenMeteoError,
    parse_hourly_payload,
    radiation_timing_offset,
    to_interval_beginning,
)

FIXTURE = "open_meteo_era5_lusatia_2025-06-14_15.json"
UTC = "UTC"


def test_parse_keeps_the_api_labels_and_renames_columns():
    frame, grid = parse_hourly_payload(load_fixture(FIXTURE))
    assert len(frame) == 48
    assert frame.index.tz is not None and str(frame.index.tz) == UTC
    assert list(frame.columns) == [
        "ghi_w_m2", "dni_w_m2", "dhi_w_m2", "temp_air_c", "wind_speed_10m_ms", "wind_speed_100m_ms"
    ]
    # Value straight from the payload: "2025-06-15T10:00" shortwave_radiation = 759.0
    assert frame.loc[pd.Timestamp("2025-06-15 10:00", tz=UTC), "ghi_w_m2"] == 759.0
    assert grid == {"latitude": 51.75, "longitude": 14.25, "elevation_m": 68.0}


def test_parse_rejects_unexpected_units():
    payload = load_fixture(FIXTURE)
    payload["hourly_units"]["wind_speed_100m"] = "km/h"  # forgot wind_speed_unit=ms
    with pytest.raises(OpenMeteoError, match="km/h"):
        parse_hourly_payload(payload)


def hourly(values: dict, start="2025-06-15 00:00") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(next(iter(values.values()))), freq="h", tz=UTC,
                        name="ts_utc")
    return pd.DataFrame(values, index=idx)


def test_to_interval_beginning_moves_radiation_back_one_hour_and_averages_instants():
    # Radiation labelled 01:00 is the mean of 00:00-01:00, so it belongs to the row 00:00.
    # Wind at 00:00 = 4 and at 01:00 = 6 (instants): the 00:00-01:00 interval averages 5.
    raw = hourly({"ghi_w_m2": [0.0, 100.0, 300.0], "wind_speed_100m_ms": [4.0, 6.0, 8.0]})
    out = to_interval_beginning(raw)
    assert out.index.tolist() == list(raw.index[:2])  # the last, incomplete interval is dropped
    assert out["ghi_w_m2"].tolist() == [100.0, 300.0]
    assert out["wind_speed_100m_ms"].tolist() == [5.0, 7.0]


def test_to_interval_beginning_refuses_gaps():
    raw = hourly({"ghi_w_m2": [0.0, 100.0, 300.0]}).drop(
        pd.Timestamp("2025-06-15 01:00", tz=UTC))
    with pytest.raises(ValueError, match="hourly"):
        to_interval_beginning(raw)


def test_converted_radiation_matches_the_sun_at_mid_interval():
    # Data-quality check on real data: after the conversion, irradiance must line up with
    # the clear-sky curve at the MIDDLE of each interval (+30 min), not 30 min earlier.
    raw, grid = parse_hourly_payload(load_fixture(FIXTURE))
    frame = to_interval_beginning(raw)
    assert radiation_timing_offset(frame, grid["latitude"], grid["longitude"]) == 30


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code, self._payload, self.text, self.headers = status_code, payload, "", {}

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, params))
        return self.responses.pop(0)


def test_client_requests_era5_in_utc_and_metres_per_second():
    client = OpenMeteoClient(session=FakeSession([FakeResponse(200, load_fixture(FIXTURE))]),
                             sleep=lambda s: None)
    frame, grid = client.hourly(51.75, 14.25, date(2025, 6, 14), date(2025, 6, 15))
    url, params = client.session.calls[0]
    assert url.endswith("/archive")
    assert params["models"] == "era5" and params["timezone"] == "GMT"
    assert params["wind_speed_unit"] == "ms"
    assert params["start_date"] == "2025-06-14" and params["end_date"] == "2025-06-15"
    assert len(frame) == 48 and grid["elevation_m"] == 68.0


def test_client_raises_its_own_error_on_bad_requests():
    client = OpenMeteoClient(session=FakeSession([FakeResponse(400, {"reason": "bad"})]),
                             sleep=lambda s: None)
    with pytest.raises(OpenMeteoError, match="HTTP 400"):
        client.hourly(51.75, 14.25, date(2025, 6, 14), date(2025, 6, 15))
