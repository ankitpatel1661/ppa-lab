"""A small, polite JSON-over-HTTP client shared by the public data sources.

Timeouts on every request, exponential back-off on transient errors (connection
problems, HTTP 429 and 5xx) and obedience to a server's `Retry-After` header. Each
data source subclasses it with its own base URL and error type.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

import requests

log = logging.getLogger(__name__)

# 429 = rate limited, 5xx = server-side trouble: worth retrying.
# Any other 4xx means our request is wrong, so retrying would not help.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class ApiError(RuntimeError):
    """Raised when an API cannot be reached or returns something unexpected."""


def _retry_after_seconds(headers: Any) -> float | None:
    """Parse a numeric 'Retry-After' header (seconds); None if absent or not a number."""
    value = headers.get("Retry-After") if headers is not None else None
    try:
        return max(0.0, float(value)) if value is not None else None
    except (TypeError, ValueError):
        return None


@dataclass
class JsonApiClient:
    base_url: str = ""
    timeout_s: float = 60.0
    max_retries: int = 4
    backoff_s: float = 1.0
    user_agent: str = "ppa-lab/0.1 (learning project; github.com/ankitpatel1661/ppa-lab)"
    session: requests.Session = field(default_factory=requests.Session)
    sleep: Callable[[float], None] = time.sleep  # injectable, so tests don't really wait
    error_class: ClassVar[type[ApiError]] = ApiError

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
                    raise self.error_class(
                        f"{url} {params} returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                last_error = self.error_class(f"HTTP {resp.status_code}")
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
        raise self.error_class(
            f"Giving up on {url} {params} after {self.max_retries} attempts"
        ) from last_error
