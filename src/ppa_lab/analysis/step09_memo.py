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
from ppa_lab.analysis.step07_report import OUT_OF_SAMPLE, trend_case
from ppa_lab.config import Settings
from ppa_lab.pricing.forwards import describe_forward

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


def _signed(x: float) -> str:
    return f"{'+' if x >= 0 else '−'}{abs(x):.1f}"


def _lower(name: str) -> str:
    """'Storage boom' -> 'storage boom', 'EEG target' stays."""
    return name if name[:2].isupper() else name[:1].lower() + name[1:]


def _case(rows: list[dict], name: str) -> dict | None:
    return next((r for r in rows if r["case"] == name), None)


def _stack_table(results: dict) -> str:
    """From the first year's forward to the ten-year indicative price, both parks."""
    start, years = results["delivery_year"], results["tenor_years"]
    curve = results.get("forward_curve") or {}
    later = ("Later years: forward curve falls"
             if curve and min(curve.values()) < results["forward"]["price_eur_mwh"]
             else "Later years: forward curve")
    level = any(r.get("level_response") for r in results["parks"].values())
    trend = any(r["assumptions"]["capture_rate_drift"] for r in results["parks"].values())
    if level:
        later = later.replace("forward curve falls", "lower forwards") + " and capture rates"
    elif trend:
        later += ", capture-rate trend"
    rows = [(f"Forward {start} (average of the scenarios)", "forward", ""),
            ("Shape: output falls in cheap hours", "shape", ""),
            (f"**= Fair price {start}**", "fair_price", "**"),
            (f"{later}; degradation", "trend", ""),
            (f"**= Fair price, {years} years**", "tenor_fair_price", "**"),
            ("Buyer's risk premium after a baseload hedge", "risk_premium", "−"),
            ("Balancing and route to market (assumed)", "balancing", "−"),
            ("Credit and liquidity (assumed)", "credit", "−"),
            (f"**= Indicative price, {years} years**", "indicative", "**")]
    stacks = []
    for park in ("solar_park", "wind_park"):
        r = results["parks"][park]
        tenor_fair = r["tenor"]["fair_price"]
        stacks.append({**r["stack_eur_mwh"], "trend": tenor_fair - r["stack_eur_mwh"]["fair_price"],
                       "tenor_fair_price": tenor_fair, "indicative": r["tenor"]["indicative"]})
    lines = ["| Layer | Solar park | Wind park |", "|---|---|---|"]
    for label, key, mark in rows:
        cells = []
        for stack in stacks:
            value = f"{round(stack[key], 1) + 0.0:.1f}".replace("-", "−")
            cells.append(f"**{value}**" if mark == "**" else f"{mark}{value}")
        lines.append(f"| {label} | {cells[0]} | {cells[1]} |")
    return "\n".join(lines)


def memo_text(results: dict, settings: Settings) -> str:
    """The memo in Markdown (one A4 page)."""
    parks = {p.name: p for p in settings.parks}
    solar = results["parks"]["solar_park"]
    s = solar["stack_eur_mwh"]
    start, years = results["delivery_year"], results["tenor_years"]
    span = f"{start}-{start + years - 1}"
    cfar_m = solar["structures"]["merchant"]["cfar_eur"]
    cfar_p = solar["structures"]["pay_as_produced"]["cfar_eur"]
    neg = solar.get("negative_prices")
    saved = neg["curtailment"]["value"] if neg else 0.0     # a curtailing merchant keeps it
    give_away = s["risk_premium"] + s["credit"] + saved     # balancing is paid either way
    give_away_m = give_away * solar["p50_mwh"] / 1e6
    sens = solar["tenor"]["sensitivity"]
    base_ind = solar["tenor"]["indicative"]
    levers = []
    old = _case(sens, "Analog days from the whole window")
    if old is not None and abs(old["indicative"] - base_ind) >= 0.5:
        levers.append(f"- Older days represent {start} (whole 2024-2026 window instead of the "
                      f"last 12 months): **{_signed(old['indicative'] - base_ind)} EUR/MWh**")
    steeper = _case(sens, trend_case(0.01))
    trend = None if steeper is None else f"±{abs(steeper['indicative'] - base_ind):.1f}"
    bo = solar.get("buildout")
    rows = [(r["indicative"] - base_ind, r["case"].split(": ")[1])
            for r in sens if r["case"].startswith("Build-out:")] if bo else []
    if rows:
        lo, hi = min(rows)[0], max(rows)[0]
        levers.append(f"- Build-out scenarios for solar and storage after {start}: "
                      f"**{_signed(lo)} / {_signed(hi)}**"
                      + (f"; ±1 pp a year of trend on top: **{trend}**" if trend else "")
                      + " EUR/MWh")
    elif trend:
        levers.append(f"- Capture-rate trend ±1 pp per year: **{trend} EUR/MWh**")
    down, up = _case(sens, "Forward −10%"), _case(sens, "Forward +10%")
    if down is not None and up is not None:
        levers.append(f"- Forward curve −10% / +10%: **{_signed(down['indicative'] - base_ind)} "
                      f"/ {_signed(up['indicative'] - base_ind)} EUR/MWh**")
    corrected = _case(sens, OUT_OF_SAMPLE)
    error = (solar.get("level_effect") or {}).get("out_of_sample_error")
    if corrected is not None and error is not None:
        levers.append(f"- Capture rate as far off as the model was out of sample in earlier "
                      f"years ({error:+.2f}, Step 6): "
                      f"**{_signed(corrected['indicative'] - base_ind)} EUR/MWh**")
    later_rate = "with the first year's capture rate"
    if solar.get("level_response"):
        later_rate = "capture rates moving with the price level as in the model"
        e = solar.get("level_effect") or {}
        h = e.get("history")
        if h and "slope_recent" in e and h["ci_low"] <= e["slope_recent"] <= h["ci_high"]:
            later_rate += f" (and {e['history_years']} history)"
    if solar.get("buildout"):
        later_rate += ", solar's with the build-out"
    clause_line = ("Keep a negative-price clause out, or price it separately: a large share "
                   "of the solar output falls in hours with negative prices.")
    keep_line = "the premium and the credit cost"
    if neg:
        c = neg["clause"]["tenor"]
        clause_line = (
            f"Offer a negative-price clause as the alternative: we stop producing at negative "
            f"prices ({neg['curtailment']['share']:.0%} of the solar output in {start}, more "
            f"later) and are paid {c['indicative']:.1f} EUR/MWh per delivered MWh: "
            f"{c['indicative_per_potential_mwh']:.1f} per MWh of output against {base_ind:.1f} "
            f"without the clause, at a higher cash flow at risk (EUR "
            f"{neg['cfar_clause_eur'] / 1e6:.2f} m instead of {cfar_p / 1e6:.2f} m).")
        keep_line = (f"the premium, the credit cost and the {saved:.1f} EUR/MWh that stopping at "
                     "negative prices saves")
    hedge_line = ("hedge the level of any unsold volume with baseload forwards.")
    market_line = ""
    hedging = results.get("hedging")
    if hedging and "solar_park" in hedging.get("parks", {}):
        h = hedging["parks"]["solar_park"]
        best = h["strategies"]["cal_base_min_variance"]
        hedge_line = (f"for any unsold volume sell about {best['hedge_ratio']:.0%} of the average "
                      f"output as Cal base futures: it cuts the merchant cash flow at risk by "
                      f"{best['cfar_reduction']:.0%} (solar park).")
        m = h.get("market_check") or {}
        quotes = [q for q in hedging.get("market_quotes", [])
                  if q["product"] == "cal_base" and q["delivery_year"] == start]
        if m and abs(m["quote"] / m["model_forward"] - 1) > 0.05:
            market_line = (f" The latest Cal-{str(start)[2:]} base quote differs from the model's "
                           f"forward: at {m['quote']:.2f} EUR/MWh ({m['date']}) the solar "
                           f"indicative price would be {m['indicative_market']:.1f} instead of "
                           f"{m['indicative_model']:.1f} EUR/MWh.")
        elif len(quotes) > 1:
            first = min(quotes, key=lambda q: q["date"])
            lo = min(q["price_eur_mwh"] for q in quotes)
            hi = max(q["price_eur_mwh"] for q in quotes)
            market_line = (f" The Cal-{str(start)[2:]} forward moved between {lo:.0f} and "
                           f"{hi:.0f} EUR/MWh since {first['date']} (published quotes): refresh "
                           "the offer with the forward curve on the day of signing.")
    forward = results.get("forward") or {"price_eur_mwh": results.get("forward_assumption")}
    forward_text = describe_forward(forward, results.get("forward_curve") or {}, start)
    forward_limit = ("the forwards are published quotes from secondary sources, not EEX files"
                     if forward.get("date") else "the forward is an assumption")
    site = parks["solar_park"].site if "solar_park" in parks else "the solar site"
    mwp = parks["solar_park"].capacity_mw if "solar_park" in parks else 50
    return f"""# Indicative price for a {years}-year solar PPA ({site.split(',')[0]}, {mwp:g} MWp)

<p class="meta">Memo · {datetime.now(UTC):%d %b %Y} · ppa-lab {__version__} · illustrative, from
public data: not an offer, no view on actual contracts · details: Step 7 report</p>

**Bottom line.** For a {years}-year pay-as-produced PPA ({span}) the negotiation range is
**{base_ind:.1f} to {solar['tenor']['fair_price']:.1f} EUR/MWh**: from the
indicative price a buyer can accept after its risk premium and costs, up to the fair value
before risk. At the indicative price the PPA cuts our 95% cash flow at risk from
EUR {cfar_m / 1e6:.2f} m to {cfar_p / 1e6:.2f} m per year (**−{1 - cfar_p / cfar_m:.0%}**) for about
**{give_away:.1f} EUR/MWh** (EUR {give_away_m:.2f} m per year) against selling at spot.

## The price, layer by layer (EUR/MWh)

{_stack_table(results)}

## What we keep and what we give away

- **Volume** stays with us: P50 {solar['p50_mwh'] / 1e3:.1f} GWh a year, one year in ten below
  {solar['p90_1y_mwh'] / 1e3:.1f} GWh (P90, 31 weather years).
- **Price and shape** go to the buyer. Its premium is mostly profile risk for solar (how deep
  the midday dip is) and volume risk for wind; the price level it can hedge with forwards.
- Against spot sales we give away {keep_line} (balancing is paid either way).

## What would change the price

{chr(10).join(levers)}

For comparison, the risk premium and the costs together take
{s['risk_premium'] + s['balancing'] + s['credit']:.1f} EUR/MWh off the fair price.

## Recommendations

1. Quote within the range above; do not go below {base_ind:.1f} EUR/MWh.
2. {clause_line}
3. Agree the cannibalisation view with Risk before signing, and {hedge_line}

## Method and limits

{results['scenarios']} joint scenarios for {start}: 31 ERA5 weather years at the real sites,
each with simulated hourly prices that respond to that weather (calibrated on 2024-2026 German
day-ahead prices, analog days from {results['analog_pool_start']}). Fair price
= E[Σ q P] / E[Σ q]; premium = 5% shortfall of the buyer's hedged value per MWh; later years by
the forward curve, {later_rate}, discounted at {results['discount_rate']:.0%}. Forward:
{forward_text}. Limits: {forward_limit}, the costs are illustrative, grid curtailment is not
modelled, and the shape comes from one market regime
(2024-2026).{market_line}
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
    hedging = settings.processed_dir / "hedging.json"
    if hedging.exists():
        results["hedging"] = json.loads(hedging.read_text())
    published = reports / "results.json"
    published.write_text(json.dumps({**results, "ppa_lab_version": __version__}, indent=1))
    memo.write_text(memo_text(results, settings))
    pdf_path = render_pdf(memo, reports / "step09_memo.pdf") if pdf else None
    log.info("wrote %s%s and %s", memo, f", {pdf_path}" if pdf_path else "", published)
    return {"memo": memo, "pdf": pdf_path, "results": published}
