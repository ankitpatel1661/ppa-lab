"""Client for the ENTSO-E Transparency Platform: a second, independent price source.

API: https://web-api.tp.entsoe.eu/api (RESTful, XML responses). Documentation now
lives in the Transparency Platform knowledge base and ENTSO-E's Postman collection.

Authentication uses a personal security token, read from the environment variable
ENTSOE_API_KEY or from the git-ignored `.env` file. Security rules in this module:
- the token is never printed, logged or included in error messages;
- the API expects the token as a URL parameter, and exception messages from
  `requests` often contain the full URL, so network errors are re-raised WITHOUT
  the original exception attached (`from None`).

Day-ahead prices (documentType A44) can use curve type A03: when consecutive
prices are equal, ENTSO-E omits the repeated points. Missing positions are
therefore forward-filled from the previous point.

For DE-LU, ENTSO-E returns TWO day-ahead price series per day, told apart by
`classificationSequence_AttributeInstanceComponent.position`. Sequence 1 is the
SDAC auction: on 1 Oct 2025 it matched SMARD/Energy-Charts on all 96
quarter-hours to the cent. Sequence 2 is a second day-ahead auction with
different prices (unconfirmed which; EXAA is a candidate). The client returns
sequence 1 unless asked otherwise.

Day-ahead wind and solar forecasts (documentType A69, processType A01, v1.10) come as one
TimeSeries per production type (psrType B16 solar, B18 wind offshore, B19 wind onshore), in MW
per quarter-hour, also with curve type A03.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from ppa_lab.timeutils import normalise_index

API_URL = "https://web-api.tp.entsoe.eu/api"
ENV_VAR = "ENTSOE_API_KEY"
# Energy Identification Codes (EIC) of bidding zones.
EIC = {"DE-LU": "10Y1001A1001A82H"}


class EntsoeError(RuntimeError):
    """Raised when ENTSO-E cannot be reached or returns no usable data."""


def load_api_key(env_file: Path | None = None) -> str | None:
    """Token from the environment, else from KEY=VALUE lines in a .env file."""
    key = os.environ.get(ENV_VAR, "").strip()
    if key:
        return key
    if env_file is not None and env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if line.startswith(f"{ENV_VAR}="):
                value = line.split("=", 1)[1].strip().strip("'\"")
                return value or None
    return None


def _name(tag: str) -> str:
    """Element name without its XML namespace: '{urn:...}Point' -> 'Point'."""
    return tag.rsplit("}", 1)[-1]


def _child(element: ET.Element, name: str) -> ET.Element:
    found = next((c for c in element if _name(c.tag) == name), None)
    if found is None:
        raise EntsoeError(f"Expected <{name}> inside <{_name(element.tag)}>")
    return found


def parse_day_ahead_xml(xml: str | bytes) -> pd.DataFrame:
    """Parse an A44 Publication_MarketDocument into rows of prices.

    Returns columns `price_eur_mwh`, `resolution_min` and `sequence`, indexed by
    UTC interval start. A response can contain several auction sequences,
    periods and resolutions; callers choose what they need.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise EntsoeError(f"Response is not valid XML: {exc}") from None

    if _name(root.tag) == "Acknowledgement_MarketDocument":
        reasons = [e.text.strip() for e in root.iter() if _name(e.tag) == "text" and e.text]
        raise EntsoeError("ENTSO-E returned no data: " + ("; ".join(reasons) or "no reason given"))

    frames = [
        _parse_period(period, _sequence_of(series))
        for series in (e for e in root.iter() if _name(e.tag) == "TimeSeries")
        for period in (c for c in series if _name(c.tag) == "Period")
    ]
    if not frames:
        raise EntsoeError("No price periods found in the ENTSO-E response")

    out = pd.concat(frames).sort_index(kind="stable")
    out.index = normalise_index(out.index)
    return out


SEQUENCE_TAG = "classificationSequence_AttributeInstanceComponent.position"


def _sequence_of(series: ET.Element) -> int:
    """Auction sequence of a <TimeSeries>; 1 when the zone has only one auction."""
    return int(next((c.text for c in series if _name(c.tag) == SEQUENCE_TAG), "1"))


def _period_values(period: ET.Element, tag: str) -> pd.Series:
    """One <Period>: its points (`tag`: "price.amount" or "quantity") on the full grid of
    its interval. Curve type A03 omits repeated values: forward-fill the gaps."""
    interval = _child(period, "timeInterval")
    start = pd.Timestamp(_child(interval, "start").text)
    end = pd.Timestamp(_child(interval, "end").text)
    step = pd.Timedelta(_child(period, "resolution").text)  # e.g. "PT15M"
    n_points = int((end - start) / step)
    points: dict[int, float] = {}
    for point in (c for c in period if _name(c.tag) == "Point"):
        points[int(_child(point, "position").text)] = float(_child(point, tag).text)
    values = pd.Series([points.get(i) for i in range(1, n_points + 1)], dtype="float64").ffill()
    values.index = pd.date_range(start, periods=n_points, freq=step)
    return values


def _parse_period(period: ET.Element, sequence: int) -> pd.DataFrame:
    """One <Period> of prices: price, resolution and auction sequence per interval."""
    values = _period_values(period, "price.amount")
    step = values.index[1] - values.index[0] if len(values) > 1 else pd.Timedelta(hours=1)
    return pd.DataFrame(
        {
            "price_eur_mwh": values.to_numpy(),
            "resolution_min": step / pd.Timedelta(minutes=1),
            "sequence": sequence,
        },
        index=values.index,
    )


PSR_COLUMNS = {"B16": "solar_mw", "B18": "wind_offshore_mw", "B19": "wind_onshore_mw"}


def parse_generation_xml(xml: str | bytes) -> pd.DataFrame:
    """Parse an A69 GL_MarketDocument (wind and solar forecast) into one MW column per
    production type (`PSR_COLUMNS`), indexed by UTC interval start."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise EntsoeError(f"Response is not valid XML: {exc}") from None
    if _name(root.tag) == "Acknowledgement_MarketDocument":
        reasons = [e.text.strip() for e in root.iter() if _name(e.tag) == "text" and e.text]
        raise EntsoeError("ENTSO-E returned no data: " + ("; ".join(reasons) or "no reason given"))
    columns: dict[str, list[pd.Series]] = {}
    for series in (e for e in root.iter() if _name(e.tag) == "TimeSeries"):
        psr = next((e.text for e in series.iter() if _name(e.tag) == "psrType"), None)
        if psr not in PSR_COLUMNS:
            continue
        for period in (c for c in series if _name(c.tag) == "Period"):
            columns.setdefault(PSR_COLUMNS[psr], []).append(_period_values(period, "quantity"))
    if not columns:
        raise EntsoeError("No wind or solar forecast found in the ENTSO-E response")
    out = pd.DataFrame({name: pd.concat(parts).sort_index() for name, parts in columns.items()})
    out = out[~out.index.duplicated(keep="last")]
    out.index = normalise_index(out.index)
    return out


@dataclass
class EntsoeClient:
    api_key: str = field(repr=False)  # never shown by repr()
    base_url: str = API_URL
    timeout_s: float = 60.0
    session: requests.Session = field(default_factory=requests.Session, repr=False)

    def day_ahead_prices(
        self,
        zone: str,
        start: date,
        end: date,
        tz: str = "Europe/Berlin",
        sequence: int | None = 1,
    ) -> pd.DataFrame:
        """Day-ahead prices for local delivery days start..end (inclusive).

        `sequence=1` (default) keeps the SDAC auction; `None` returns all sequences.
        """
        prices = self._fetch(zone, start, end, tz)
        return prices if sequence is None else prices[prices["sequence"] == sequence]

    def wind_solar_forecast(self, zone: str, start: pd.Timestamp,
                            end: pd.Timestamp) -> pd.DataFrame:
        """Day-ahead wind and solar forecasts (MW) between two UTC times."""
        eic = EIC[zone]
        params = {"documentType": "A69", "processType": "A01", "in_Domain": eic,
                  "periodStart": pd.Timestamp(start).strftime("%Y%m%d%H%M"),
                  "periodEnd": pd.Timestamp(end).strftime("%Y%m%d%H%M")}
        return parse_generation_xml(self._get(params))

    def _get(self, params: dict) -> bytes:
        """GET with the token; errors never carry the URL (it contains the token)."""
        try:
            resp = self.session.get(self.base_url, params={"securityToken": self.api_key,
                                                           **params}, timeout=self.timeout_s)
        except requests.RequestException as exc:
            raise EntsoeError(f"Request to ENTSO-E failed ({type(exc).__name__})") from None
        if resp.status_code == 401:
            raise EntsoeError(
                "HTTP 401 Unauthorized: the token is wrong, or API access is not activated yet"
            )
        if resp.status_code != 200:
            raise EntsoeError(f"HTTP {resp.status_code} from ENTSO-E")
        return resp.content

    def _fetch(self, zone: str, start: date, end: date, tz: str) -> pd.DataFrame:
        eic = EIC[zone]
        t0 = pd.Timestamp(start).tz_localize(tz).tz_convert("UTC")
        t1 = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(tz).tz_convert("UTC")
        params = {
            "securityToken": self.api_key,
            "documentType": "A44",
            "in_Domain": eic,
            "out_Domain": eic,
            "periodStart": t0.strftime("%Y%m%d%H%M"),
            "periodEnd": t1.strftime("%Y%m%d%H%M"),
        }
        try:
            resp = self.session.get(self.base_url, params=params, timeout=self.timeout_s)
        except requests.RequestException as exc:
            # `from None`: the original message may contain the URL, including the token.
            raise EntsoeError(f"Request to ENTSO-E failed ({type(exc).__name__})") from None

        if resp.status_code == 401:
            raise EntsoeError(
                "HTTP 401 Unauthorized: the token is wrong, or API access is not activated yet"
            )
        if resp.status_code != 200:
            try:
                parse_day_ahead_xml(resp.content)
            except EntsoeError as exc:
                raise EntsoeError(f"HTTP {resp.status_code}: {exc}") from None
            raise EntsoeError(f"HTTP {resp.status_code} from ENTSO-E")
        return parse_day_ahead_xml(resp.content)


def fetch_forecasts(client: EntsoeClient, store, start: pd.Timestamp, end: pd.Timestamp,
                    zone: str = "DE-LU", refresh: bool = False,
                    sleep=None) -> list[tuple[str, str]]:
    """Day-ahead wind and solar forecasts month by month (UTC months) into the raw store
    (dataset "wind_solar_forecast"); cached months are skipped unless `refresh`."""
    import time
    sleep = sleep or time.sleep
    first = pd.Timestamp(start).tz_localize(None).to_period("M").to_timestamp()
    last = pd.Timestamp(end).tz_localize(None).to_period("M").to_timestamp()
    done = []
    for month_start in pd.date_range(first, last, freq="MS").tz_localize("UTC"):
        month = month_start.strftime("%Y-%m")
        if store.exists("wind_solar_forecast", month) and not refresh:
            done.append((month, "cached"))
            continue
        month_end = month_start + pd.offsets.MonthBegin(1)
        frame = client.wind_solar_forecast(zone, month_start, month_end)
        frame = frame[(frame.index >= month_start) & (frame.index < month_end)]
        store.save(frame, "wind_solar_forecast", month,
                   {"source": "ENTSO-E A69 day-ahead", "zone": zone}, overwrite=True)
        done.append((month, "downloaded"))
        sleep(0.5)
    return done

