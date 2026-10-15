"""Where the forward price comes from, in words (reports, memo and dashboard).

Kept free of heavy imports: the dashboard on Streamlit Community Cloud installs only
app/requirements.txt.
"""

from __future__ import annotations

from urllib.parse import urlparse


def describe_forward(forward: dict, curve: dict, start_year: int) -> str:
    """Where the forward comes from, in one sentence (report, memo and dashboard).

    `forward` holds `price_eur_mwh` and optionally `date` and `source` (URL); `curve` maps later
    years (int or str) to their forwards.
    """
    price, date, source = forward["price_eur_mwh"], forward.get("date"), forward.get("source")
    if date:
        host = urlparse(source).netloc.removeprefix("www.") if source else ""
        text = (f"EEX German Power Cal-{str(start_year)[2:]} base {price:.2f} EUR/MWh "
                f"(quote of {date}" + (f", via {host})" if host else ")"))
    else:
        text = f"{price:.2f} EUR/MWh (an assumption, not a market quote)"
    if curve:
        years = sorted(int(y) for y in curve)
        points = ", ".join(f"{y}: {curve[y] if y in curve else curve[str(y)]:.2f}" for y in years)
        text += (f"; later years follow the forward curve ({points}), held flat after "
                 f"{years[-1]}")
    else:
        text += "; flat over the tenor"
    return text
