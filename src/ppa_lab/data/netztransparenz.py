"""The German TSOs' data platform netztransparenz.de: imbalance prices and wind and solar
forecasts and extrapolations (roadmap item 6).

Access needs a free account at the WebAPI-Portal (https://api-portal.netztransparenz.de) and
a client created there; its ID and secret go into the environment or the git-ignored .env as
NETZTRANSPARENZ_CLIENT_ID and NETZTRANSPARENZ_CLIENT_SECRET. Authentication is OAuth 2.0
client credentials. Endpoints and formats are those of the API's public OpenAPI description
(read on 16 Oct 2026):

    token  https://identity.netztransparenz.de/users/connect/token
    data   https://ds.netztransparenz.de/api/v1/data/{path}/{dateFrom}/{dateTo}

with times in UTC ("2020-10-10T13:00:00"). Responses are semicolon-separated text with German
numbers ("1.188,17"), one row per quarter-hour (the online extrapolation: per hour), in one of
two layouts: Datum; von; Zeitzone von; bis; Zeitzone bis; values... (forecasts, extrapolations)
or Datum; Zeitzone; von; bis; Datenkategorie; Datentyp; Einheit; values... (reBAP, with
"reBAP unterdeckt" and "reBAP ueberdeckt"). "N.A." marks missing values.

Checked on 16 Oct 2026: `prognose/Wind` and `prognose/Solar` are "N.A." throughout 2023-2026,
and `hochrechnung/*` covers only the EEG volumes the TSOs market themselves (40-180 MW of wind).
Neither measures national forecast errors; the day-ahead forecasts come from ENTSO-E instead.
"""

from __future__ import annotations

import io
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

TOKEN_URL = "https://identity.netztransparenz.de/users/connect/token"
BASE_URL = "https://ds.netztransparenz.de"
ID_VAR, SECRET_VAR = "NETZTRANSPARENZ_CLIENT_ID", "NETZTRANSPARENZ_CLIENT_SECRET"
RETRYABLE = frozenset({429, 500, 502, 503, 504})
MISSING = frozenset({"N.A.", "NA", "N/A", "NE", "N.E.", "-"})   # markers of missing values

# dataset name -> API path (data category / product)
DATASETS = {
    "rebap": "NrvSaldo/reBAP/Qualitaetsgesichert",
    "wind_onshore_online": "onlinehochrechnung/Windonshore/qualitaetsgesichert",
    "wind_offshore_online": "onlinehochrechnung/Windoffshore/qualitaetsgesichert",
    "solar_online": "onlinehochrechnung/Solar/qualitaetsgesichert",
}
TIME_COLUMNS = ("Datum", "von", "Zeitzone von", "bis", "Zeitzone bis", "Zeitzone")
TEXT_COLUMNS = ("Datenkategorie", "Datentyp", "Einheit")
OFFSETS = {"UTC": "+00:00", "CET": "+01:00", "MEZ": "+01:00", "CEST": "+02:00", "MESZ": "+02:00"}


class NetztransparenzError(RuntimeError):
    """Raised when netztransparenz.de cannot be reached or returns something unusable."""


def load_credentials(env_file: Path | None = None) -> tuple[str, str] | None:
    """Client ID and secret from the environment, else from KEY=VALUE lines in a .env file.
    None when either is missing. The values are never logged."""
    found = {var: os.environ.get(var, "").strip() for var in (ID_VAR, SECRET_VAR)}
    if not all(found.values()) and env_file is not None and env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            for var in (ID_VAR, SECRET_VAR):
                if line.startswith(f"{var}=") and not found[var]:
                    found[var] = line.split("=", 1)[1].strip().strip("'\"")
    if not all(found.values()):
        return None
    return found[ID_VAR], found[SECRET_VAR]


def _number(text: str) -> float:
    text = text.strip()
    if not text or text.upper() in MISSING:
        return float("nan")
    return float(text.replace(".", "").replace(",", "."))


def parse_csv(text: str) -> pd.DataFrame:
    """The API's text response as a DataFrame: UTC index at the start of each interval
    ("ts_utc"), one float column per value column (EUR/MWh or MW), NaN where "N.A."."""
    frame = pd.read_csv(io.StringIO(text), sep=";", dtype=str, keep_default_na=False)
    frame.columns = [c.strip() for c in frame.columns]
    zone_column = next((c for c in ("Zeitzone von", "Zeitzone") if c in frame.columns), None)
    if zone_column is None or "Datum" not in frame.columns or "von" not in frame.columns:
        raise NetztransparenzError(f"unexpected columns {list(frame.columns)[:6]}: no date, "
                                   "time or time zone")
    if frame.empty:
        return pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC", name="ts_utc"))
    zone = frame[zone_column].str.strip().map(OFFSETS)
    if zone.isna().any():
        raise NetztransparenzError(f"unknown time zones {set(frame[zone_column][zone.isna()])}")
    raw = frame["Datum"].str.strip()
    iso = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce")       # 2011-04-01
    german = pd.to_datetime(raw, format="%d.%m.%Y", errors="coerce")    # 01.04.2011
    day = iso.fillna(german)
    if day.isna().any():
        raise NetztransparenzError(f"unreadable dates {list(raw[day.isna()][:3])}")
    stamp = day.dt.strftime("%Y-%m-%d") + "T" + frame["von"].str.strip() + zone
    index = pd.DatetimeIndex(pd.to_datetime(stamp, utc=True), name="ts_utc")
    values = frame.drop(columns=[c for c in (*TIME_COLUMNS, *TEXT_COLUMNS)
                                 if c in frame.columns])
    out = values.apply(lambda col: col.map(_number)).astype("float64")
    out.index = index
    return out.sort_index()


@dataclass
class NetztransparenzClient:
    client_id: str
    client_secret: str = field(repr=False)
    base_url: str = BASE_URL
    token_url: str = TOKEN_URL
    timeout_s: float = 60.0
    max_retries: int = 4
    backoff_s: float = 2.0
    session: requests.Session = field(default_factory=requests.Session)
    sleep: Callable[[float], None] = time.sleep
    _token: str | None = field(default=None, repr=False)
    _expires: float = 0.0

    def token(self, now: Callable[[], float] = time.time) -> str:
        """A bearer token (cached until a minute before it expires)."""
        if self._token and now() < self._expires - 60:
            return self._token
        resp = self.session.post(self.token_url, timeout=self.timeout_s, data={
            "grant_type": "client_credentials", "client_id": self.client_id,
            "client_secret": self.client_secret})
        if resp.status_code != 200:
            raise NetztransparenzError(f"token request returned HTTP {resp.status_code}: "
                                       f"{resp.text[:200]}")
        body = resp.json()
        self._token = body["access_token"]
        self._expires = now() + float(body.get("expires_in", 3600))
        return self._token

    def get_text(self, path: str, start: datetime, end: datetime) -> str:
        """GET {base}/api/v1/data/{path}/{start}/{end} (UTC), with back-off on 429 and 5xx and
        one new token on 401."""
        url = (f"{self.base_url.rstrip('/')}/api/v1/data/{path}/"
               f"{start:%Y-%m-%dT%H:%M:%S}/{end:%Y-%m-%dT%H:%M:%S}")
        renewed = False
        for attempt in range(1, self.max_retries + 1):
            resp = self.session.get(url, timeout=self.timeout_s,
                                    headers={"Authorization": f"Bearer {self.token()}"})
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 401 and not renewed:
                self._token, renewed = None, True
                continue
            if resp.status_code not in RETRYABLE:
                raise NetztransparenzError(f"{url} returned HTTP {resp.status_code}: "
                                           f"{resp.text[:200]}")
            if attempt < self.max_retries:
                self.sleep(self.backoff_s * 2 ** (attempt - 1))
        raise NetztransparenzError(f"{url} failed after {self.max_retries} attempts")

    def fetch(self, dataset: str, start: datetime, end: datetime) -> pd.DataFrame:
        """One dataset (see DATASETS) between two UTC times, parsed."""
        if dataset not in DATASETS:
            raise NetztransparenzError(f"unknown dataset {dataset!r}; known: {sorted(DATASETS)}")
        return parse_csv(self.get_text(DATASETS[dataset], start, end))


MISSING_CREDENTIALS = (
    "netztransparenz.de needs credentials: register (free) at https://api-portal.netztransparenz.de,"
    f" create a client there and put {ID_VAR}=... and {SECRET_VAR}=... into the git-ignored .env")


def month_starts(start: datetime, end: datetime) -> list[pd.Timestamp]:
    """First instant (UTC) of every calendar month from `start`'s month to `end`'s."""
    first = pd.Timestamp(start).tz_localize(None).to_period("M").to_timestamp()
    last = pd.Timestamp(end).tz_localize(None).to_period("M").to_timestamp()
    return [t.tz_localize("UTC") for t in pd.date_range(first, last, freq="MS")]


def fetch_tso(client: NetztransparenzClient, store, datasets: list[str], start: datetime,
              end: datetime, refresh: bool = False, pause_s: float = 0.5,
              today: pd.Timestamp | None = None) -> list[tuple[str, str, str]]:
    """Download each dataset month by month (UTC months) into the raw store; months already
    cached are skipped unless `refresh`, except the current month, which may still grow.
    Returns (dataset, month, action) for every month."""
    today = today or pd.Timestamp.now(tz="UTC")
    current = today.tz_convert("UTC").strftime("%Y-%m")
    done = []
    for dataset in datasets:
        for month_start in month_starts(start, end):
            month = month_start.strftime("%Y-%m")
            if store.exists(dataset, month) and not refresh and month != current:
                done.append((dataset, month, "cached"))
                continue
            month_end = month_start + pd.offsets.MonthBegin(1)
            frame = client.fetch(dataset, month_start.to_pydatetime(), month_end.to_pydatetime())
            frame = frame[(frame.index >= month_start) & (frame.index < month_end)]
            store.save(frame, dataset, month, {"source": "netztransparenz.de",
                                               "path": DATASETS[dataset]}, overwrite=True)
            done.append((dataset, month, "downloaded"))
            client.sleep(pause_s)
    return done
