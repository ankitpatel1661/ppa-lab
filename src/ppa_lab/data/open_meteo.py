"""ERA5 weather from the Open-Meteo archive API (free, no key, CC BY 4.0).

    GET https://archive-api.open-meteo.com/v1/archive
        ?latitude=..&longitude=..&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        &models=era5&timezone=GMT&wind_speed_unit=ms&hourly=<variables>

ERA5 is ECMWF's global reanalysis (about 0.25 degrees, hourly, since 1940); Open-Meteo
snaps the request to the nearest grid point and reports it in the response.

Time conventions (the trap of this source):
- radiation values are the MEAN OF THE PRECEDING HOUR: the value labelled 11:00 is the
  average over 10:00-11:00;
- temperature and wind are INSTANTANEOUS values at the label time.
The project stores interval-beginning hourly values (Step 1 convention), so
`to_interval_beginning` moves radiation back by one hour and averages each pair of
instants. `radiation_timing_offset` checks the result against the sun's position.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ppa_lab.data.http import ApiError, JsonApiClient
from ppa_lab.timeutils import normalise_index

# API variable -> (our column, expected unit)
VARIABLES: dict[str, tuple[str, str]] = {
    "shortwave_radiation": ("ghi_w_m2", "W/m²"),
    "direct_normal_irradiance": ("dni_w_m2", "W/m²"),
    "diffuse_radiation": ("dhi_w_m2", "W/m²"),
    "temperature_2m": ("temp_air_c", "°C"),
    "wind_speed_10m": ("wind_speed_10m_ms", "m/s"),
    "wind_speed_100m": ("wind_speed_100m_ms", "m/s"),
}
RADIATION = ("ghi_w_m2", "dni_w_m2", "dhi_w_m2")


class OpenMeteoError(ApiError):
    """Raised when the archive API fails or returns something unexpected."""


def parse_hourly_payload(payload: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, float]]:
    """Payload -> (frame indexed by the API's UTC labels, ERA5 grid point used).

    Values are kept exactly as labelled by the API (raw layer); see
    `to_interval_beginning` for the conversion to the project's convention.
    """
    hourly, units = payload.get("hourly"), payload.get("hourly_units", {})
    if not hourly or "time" not in hourly:
        raise OpenMeteoError("payload has no hourly data")
    if payload.get("utc_offset_seconds", 0) != 0:
        raise OpenMeteoError("expected timestamps in GMT/UTC (request timezone=GMT)")
    columns = {}
    for api_name, (column, unit) in VARIABLES.items():
        if api_name not in hourly:
            raise OpenMeteoError(f"variable {api_name!r} missing from the payload")
        if units.get(api_name) != unit:
            raise OpenMeteoError(f"{api_name} in {units.get(api_name)!r}, expected {unit!r}")
        columns[column] = np.asarray(hourly[api_name], dtype="float64")
    index = normalise_index(pd.DatetimeIndex(pd.to_datetime(hourly["time"])).tz_localize("UTC"))
    grid = {
        "latitude": float(payload["latitude"]),
        "longitude": float(payload["longitude"]),
        "elevation_m": float(payload["elevation"]),
    }
    return pd.DataFrame(columns, index=index), grid


def to_interval_beginning(raw: pd.DataFrame) -> pd.DataFrame:
    """Hourly values for the interval [t, t + 1 h), labelled t (project convention).

    Radiation labelled t + 1 h (mean of the preceding hour) moves to row t; every other
    column becomes the mean of its instants at t and t + 1 h. The last row has no
    complete interval and is dropped. The index must be a gap-free hourly grid.
    """
    steps = raw.index.to_series().diff().dropna()
    if not (steps == pd.Timedelta(hours=1)).all():
        raise ValueError("to_interval_beginning needs a gap-free hourly index")
    out = pd.DataFrame(index=raw.index)
    for column in raw.columns:
        nxt = raw[column].shift(-1)
        out[column] = nxt if column in RADIATION else (raw[column] + nxt) / 2.0
    return out.iloc[:-1]


def radiation_timing_offset(frame: pd.DataFrame, latitude: float, longitude: float) -> int:
    """Minutes after the row label at which `ghi_w_m2` best matches the clear-sky sun.

    For interval-beginning hourly means the answer must be +30 (the middle of the
    interval); -30 would mean the data is still labelled at the end of the interval.
    """
    import pvlib  # heavy import, only needed here

    location = pvlib.location.Location(latitude, longitude)
    ghi = frame["ghi_w_m2"].to_numpy()
    scores = {}
    for offset in (-30, 30, 90):
        clear = location.get_clearsky(frame.index + pd.Timedelta(minutes=offset))["ghi"]
        scores[offset] = float(np.corrcoef(ghi, clear.to_numpy())[0, 1])
    return max(scores, key=scores.get)


@dataclass
class OpenMeteoClient(JsonApiClient):
    base_url: str = "https://archive-api.open-meteo.com/v1"
    error_class = OpenMeteoError

    def hourly(
        self, latitude: float, longitude: float, start: date, end: date
    ) -> tuple[pd.DataFrame, dict[str, float]]:
        """ERA5 hourly weather for one point and an inclusive UTC date range."""
        payload = self.get_json(
            "archive",
            {
                "latitude": f"{latitude}",
                "longitude": f"{longitude}",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "models": "era5",
                "timezone": "GMT",
                "wind_speed_unit": "ms",
                "hourly": ",".join(VARIABLES),
            },
        )
        return parse_hourly_payload(payload)
