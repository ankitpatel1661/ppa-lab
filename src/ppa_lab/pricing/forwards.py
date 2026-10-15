"""Where the forward price comes from, in words (reports, memo and dashboard).

Kept free of heavy imports: the dashboard on Streamlit Community Cloud installs only
app/requirements.txt.
"""

from __future__ import annotations

from urllib.parse import urlparse

import pandas as pd


def describe_forward(forward: dict, curve: dict, start_year: int) -> str:
    """Where the forward comes from, in one sentence (report, memo and dashboard).

    `forward` holds `price_eur_mwh` and optionally `date`, `source` (URL), `quarters` (quarter
    -> forward) and `quarters_date`; `curve` maps later years (int or str) to their forwards.
    """
    price, date, source = forward["price_eur_mwh"], forward.get("date"), forward.get("source")
    if date:
        host = urlparse(source).netloc.removeprefix("www.") if source else ""
        text = (f"EEX German Power Cal-{str(start_year)[2:]} base {price:.2f} EUR/MWh "
                f"(quote of {date}" + (f", via {host})" if host else ")"))
    else:
        text = f"{price:.2f} EUR/MWh (an assumption, not a market quote)"
    quarters = forward.get("quarters")
    if quarters:
        text += ("; its quarters follow the market's seasonal shape (Q1-Q4 "
                 + " / ".join(f"{quarters[q]:.1f}" for q in sorted(quarters))
                 + f", quotes of {forward.get('quarters_date')})")
    if curve:
        years = sorted(int(y) for y in curve)
        points = ", ".join(f"{y}: {curve[y] if y in curve else curve[str(y)]:.2f}" for y in years)
        text += (f"; later years follow the forward curve ({points}), held flat after "
                 f"{years[-1]}")
    else:
        text += "; flat over the tenor"
    return text


def quarter_forwards(forward: float, quotes, year: int, tz: str) -> dict[int, float] | None:
    """Quarter forwards for `year`: the quotes' seasonal shape scaled to `forward`.

    F_q = forward * Q_q / (hour-weighted mean of the Q quotes), so the hour-weighted mean of
    the result is exactly `forward`. `quotes` is a `QuarterQuotes` or None (then None).
    """
    if quotes is None:
        return None
    local = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", tz=tz,
                          inclusive="left")
    hours = pd.Series(local.quarter).value_counts()
    mean = sum(hours[q] * price for q, price in quotes.quarters.items()) / hours.sum()
    return {q: float(forward * price / mean) for q, price in sorted(quotes.quarters.items())}
