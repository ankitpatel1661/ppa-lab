"""Step 9: the one-page management memo and the results file for the dashboard.

Every number comes from data/processed/ppa_pricing.json (Step 7), so the memo, the README
and the dashboard cannot drift apart from the code.

Output:
    reports/step09_memo.md   (+ step09_memo.pdf when Google Chrome is available)
    reports/results.json     committed copy of the Step 7 results; the dashboard reads it
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ppa_lab import __version__
from ppa_lab.config import Settings

log = logging.getLogger(__name__)

CHROME_CANDIDATES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                     "google-chrome", "chromium", "chromium-browser"]
MEMO_CSS = """
@page { size: A4; margin: 14mm 15mm; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 9.6pt;
       line-height: 1.38; color: #1d1d1f; }
h1 { color: #005391; font-size: 16pt; margin: 0 0 1mm; }
h2 { color: #005391; font-size: 11pt; margin: 3.5mm 0 1mm; border-bottom: 1px solid #d9d9d6; }
p { margin: 1.2mm 0; }
ul, ol { margin: 1mm 0; padding-left: 5mm; } li { margin: 0.6mm 0; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 1.5mm 0; }
th { background: #e8f0f7; text-align: left; }
th, td { border: 1px solid #d9d9d6; padding: 2px 5px; }
td:nth-child(n+2), th:nth-child(n+2) { text-align: right; }
.meta { color: #6b6b66; font-size: 8.5pt; }
"""


def _case(rows: list[dict], name: str) -> dict | None:
    return next((r for r in rows if r["case"] == name), None)


def _stack_table(s: dict, w: dict, forward: float) -> str:
    rows = [(f"Forward (assumed {forward:.0f}; average of the scenarios)", "forward", ""),
            ("Shape: output falls in cheap hours", "shape", ""),
            ("**= Fair price**", "fair_price", "**"),
            ("Buyer's risk premium after a baseload hedge", "risk_premium", "−"),
            ("Balancing and route to market (assumed)", "balancing", "−"),
            ("Credit and liquidity (assumed)", "credit", "−"),
            ("**= Indicative price**", "indicative", "**")]
    lines = ["| Layer | Solar park | Wind park |", "|---|---|---|"]
    for label, key, mark in rows:
        cells = []
        for stack in (s, w):
            value = f"{stack[key]:.1f}".replace("-", "−")
            cells.append(f"**{value}**" if mark == "**" else f"{mark}{value}")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")
    return "\n".join(lines)


def memo_text(results: dict, settings: Settings) -> str:
    """The memo in Markdown (one A4 page)."""
    parks = {p.name: p for p in settings.parks}
    solar, wind = results["parks"]["solar_park"], results["parks"]["wind_park"]
    s, w = solar["stack_eur_mwh"], wind["stack_eur_mwh"]
    start, years = results["delivery_year"], results["tenor_years"]
    span = f"{start}-{start + years - 1}"
    cfar_m = solar["structures"]["merchant"]["cfar_eur"]
    cfar_p = solar["structures"]["pay_as_produced"]["cfar_eur"]
    give_away = s["risk_premium"] + s["credit"]             # balancing is paid either way
    give_away_m = give_away * solar["p50_mwh"] / 1e6
    sens = solar["tenor"]["sensitivity"]
    base_ind = solar["tenor"]["indicative"]
    levers = []
    for name, label, sign in (("Analog days from the whole window",
                               "Older days represent 2027 (whole 2024-2026 window instead of "
                               "the last 12 months)", "+"),
                              ("Capture rate +1 pp per year", "Capture-rate trend ±1 pp per year",
                               "±"),
                              ("Forward +10%", "Forward ±10%", "±")):
        row = _case(sens, name)
        if row is not None:
            levers.append(f"- {label}: **{sign}{abs(row['indicative'] - base_ind):.1f} "
                          "EUR/MWh**")
    structures = solar["structures"]
    clause = structures.get("pay_as_produced_clause")
    negative = "a large share"
    if clause is not None:
        plain = structures["pay_as_produced"]["expected_revenue_eur"]
        paid = clause["expected_revenue_eur"] / plain
        negative = f"{1 - paid:.0%}"
    site = parks["solar_park"].site if "solar_park" in parks else "the solar site"
    mwp = parks["solar_park"].capacity_mw if "solar_park" in parks else 50
    return f"""# Indicative price for a {years}-year solar PPA ({site.split(',')[0]}, {mwp:g} MWp)

<p class="meta">Memo · {datetime.now(UTC):%d %b %Y} · ppa-lab {__version__} · illustrative analysis
from public data, not an offer · details: reports/step07_ppa_pricing.md</p>

**Bottom line.** For a {years}-year pay-as-produced PPA ({span}) the negotiation range is
**{base_ind:.1f} to {solar['tenor']['fair_price']:.1f} EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR {cfar_m / 1e6:.2f} m to {cfar_p / 1e6:.2f} m per year (**−{1 - cfar_p / cfar_m:.0%}**) for about
**{give_away:.1f} EUR/MWh** (EUR {give_away_m:.2f} m per year) against selling at spot.

## The price, layer by layer (EUR/MWh, {start})

{_stack_table(s, w, results['forward_assumption'])}

## What we keep and what we give away

- **Volume** stays with us: P50 {solar['p50_mwh'] / 1e3:.1f} GWh a year, one year in ten below
  {solar['p90_1y_mwh'] / 1e3:.1f} GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away the premium and the credit cost (balancing is paid either way).

## What would change the price

{chr(10).join(levers)}

The view on solar cannibalisation (which past represents {start}, and the trend) matters
more than the risk premium and the costs together.

## Recommendations

1. Quote within the range above; do not go below {base_ind:.1f} EUR/MWh.
2. Keep a negative-price clause out, or price it separately: {negative} of the solar output
   falls in hours with negative prices and would be unpaid.
3. Agree the cannibalisation view with Risk before signing, and hedge the level of any unsold
   volume with baseload forwards (next step of the project: market forwards and hedge ratio).

## Method and limits

{results['scenarios']} joint scenarios for {start}: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from {results['analog_pool_start']}). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
a flat forward and capture rate, discounted at {results['discount_rate']:.0%}. Limits: the
forward is an assumption, the costs are illustrative, the parks produce their potential output
(no curtailment), and one market regime is in the data. Wind park for comparison: fair
{w['fair_price']:.1f}, indicative {w['indicative']:.1f} EUR/MWh.
"""


def render_pdf(md_path: Path, pdf_path: Path) -> Path | None:
    """Markdown -> HTML -> PDF with headless Chrome; None if Chrome or `markdown` is missing."""
    chrome = next((c for c in CHROME_CANDIDATES if Path(c).exists() or shutil.which(c)), None)
    try:
        import markdown
    except ImportError:
        return None
    if chrome is None:
        return None
    body = markdown.markdown(md_path.read_text(encoding="utf-8"), extensions=["extra"])
    html = (f"<!doctype html><html><head><meta charset='utf-8'><style>{MEMO_CSS}</style>"
            f"</head><body>{body}</body></html>")
    with tempfile.TemporaryDirectory() as tmp:
        html_path = Path(tmp) / "memo.html"
        html_path.write_text(html, encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                       check=True, capture_output=True, timeout=120)
    return pdf_path


def write_step09_memo(settings: Settings, pdf: bool = True) -> dict[str, Path | None]:
    reports = settings.reports_dir
    reports.mkdir(parents=True, exist_ok=True)
    memo = reports / "step09_memo.md"
    source = settings.processed_dir / "ppa_pricing.json"
    if not source.exists():
        memo.write_text("# Management memo\n\nNo pricing results found: run `ppa-lab pricing` "
                        "first (Step 7).\n")
        return {"memo": memo, "pdf": None, "results": None}
    results = json.loads(source.read_text())
    published = reports / "results.json"
    published.write_text(json.dumps({**results, "ppa_lab_version": __version__}, indent=1))
    memo.write_text(memo_text(results, settings))
    pdf_path = render_pdf(memo, reports / "step09_memo.pdf") if pdf else None
    log.info("wrote %s%s and %s", memo, f", {pdf_path}" if pdf_path else "", published)
    return {"memo": memo, "pdf": pdf_path, "results": published}
