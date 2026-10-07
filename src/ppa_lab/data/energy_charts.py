"""Client for the public Energy-Charts API (Fraunhofer ISE).

Endpoints used (no API key needed, data licensed CC BY 4.0):
  /price?bzn=DE-LU&start=YYYY-MM-DD&end=YYYY-MM-DD
      Day-ahead auction prices in EUR/MWh (source: Bundesnetzagentur | SMARD.de).
      Hourly until 30 Sep 2025, quarter-hourly from 1 Oct 2025.
  /public_power?country=de&start=...&end=...
      Net public generation by technology, load and residual load in MW (15 min).

`start` and `end` are local delivery days and BOTH are inclusive.

Design: network code (EnergyChartsClient) is kept separate from parsing code
(parse_* functions). The parsers are pure functions, so they can be tested with
saved payloads, without any network access.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import pandas as pd
import requests

from ppa_lab.timeutils import from_unix_seconds

log = logging.getLogger(__name__)

# 429 = rate limited, 5xx = server-side trouble: worth retrying.
# Any other 4xx means our request is wrong, so retrying would not help.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class EnergyChartsError(RuntimeError):
    """Raised when the API cannot be reached or returns something unexpected."""


# --------------------------------------------------------------------------- #
# Parsing (pure functions)
# --------------------------------------------------------------------------- #
def snake_case(name: str) -> str:
    """'Fossil brown coal / lignite' -> 'fossil_brown_coal_lignite'."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def parse_price_payload(payload: dict[str, Any]) -> pd.DataFrame:
    """Turn a /price response into a DataFrame indexed by UTC interval start."""
    missing = {"unix_seconds", "price", "unit"} - payload.keys()
    if missing:
        raise EnergyChartsError(f"Price payload is missing keys: {sorted(missing)}")
    if payload.get("deprecated"):
        log.warning("Energy-Charts marks this endpoint as deprecated; check the API docs.")

    seconds, prices = payload["unix_seconds"], payload["price"]
    if len(seconds) != len(prices):
        raise EnergyChartsError(
            f"Length mismatch: {len(seconds)} timestamps vs {len(prices)} prices"
        )
    unit = str(payload["unit"]).replace(" ", "")
    if unit != "EUR/MWh":
        raise EnergyChartsError(f"Unexpected price unit {payload['unit']!r}; expected 'EUR / MWh'")

    return pd.DataFrame(
        {"price_eur_mwh": pd.Series(prices, dtype="float64").to_numpy()},
        index=from_unix_seconds(seconds),
    )


def parse_public_power_payload(payload: dict[str, Any]) -> pd.DataFrame:
    """Turn a /public_power response into a wide DataFrame (one column per series).

    Columns get a unit suffix: '_mw' for power, '_pct' for the renewable shares.
    """
    missing = {"unix_seconds", "production_types"} - payload.keys()
    if missing:
        raise EnergyChartsError(f"Public-power payload is missing keys: {sorted(missing)}")

    seconds = payload["unix_seconds"]
    columns: dict[str, Any] = {}
    for series in payload["production_types"]:
        name, data = series["name"], series["data"]
        if len(data) != len(seconds):
            raise EnergyChartsError(
                f"Series {name!r} has {len(data)} values for {len(seconds)} timestamps"
            )
        suffix = "_pct" if "share" in name.lower() else "_mw"
        columns[snake_case(name) + suffix] = pd.Series(data, dtype="float64").to_numpy()
    return pd.DataFrame(columns, index=from_unix_seconds(seconds))


# --------------------------------------------------------------------------- #
# Network client
# --------------------------------------------------------------------------- #
def _retry_after_seconds(headers: Any) -> float | None:
    """Parse a numeric 'Retry-After' header (seconds); None if absent or not a number."""
    value = headers.get("Retry-After") if headers is not None else None
    try:
        return max(0.0, float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None



@dataclass
class EnergyChartsClient:
    base_url: str = "https://api.energy-charts.info"
    timeout_s: float = 60.0
    max_retries: int = 4
    backoff_s: float = 1.0
    user_agent: str = "ppa-lab/0.1 (learning project; github.com/ankitpatel1661/ppa-lab)"
    session: requests.Session = field(default_factory=requests.Session)
    sleep: Callable[[float], None] = time.sleep  # injectable, so tests don't really wait

    def get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        """GET an endpoint with timeouts and exponential back-off on transient errors."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            retry_after: float | None = None
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout_s,
                    headers={"User-Agent": self.user_agent},
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code not in RETRYABLE_STATUS:
                    raise EnergyChartsError(
                        f"{url} {params} returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                last_error = EnergyChartsError(f"HTTP {resp.status_code}")
                retry_after = _retry_after_seconds(resp.headers)

            if attempt < self.max_retries:
                # If the server tells us how long to wait (rate limit), obey it;
                # otherwise back off exponentially: 1 s, 2 s, 4 s, ...
                wait = (
                    retry_after + 1.0
                    if retry_after is not None
                    else self.backoff_s * 2 ** (attempt - 1)
                )
                log.warning(
                    "Attempt %d/%d for %s failed (%s); retrying in %.1fs",
                    attempt, self.max_retries, url, last_error, wait,
                )
                self.sleep(wait)
        raise EnergyChartsError(
            f"Giving up on {url} {params} after {self.max_retries} attempts"
        ) from last_error

    def day_ahead_prices(self, bidding_zone: str, start: date, end: date) -> pd.DataFrame:
        payload = self.get_json(
            "price", {"bzn": bidding_zone, "start": start.isoformat(), "end": end.isoformat()}
        )
        return parse_price_payload(payload)

    def public_power(self, country: str, start: date, end: date) -> pd.DataFrame:
        payload = self.get_json(
            "public_power", {"country": country, "start": start.isoformat(), "end": end.isoformat()}
        )
        return parse_public_power_payload(payload)
