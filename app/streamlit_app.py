"""ppa-lab dashboard: the PPA price and its risk, for your own assumptions.

    make app            # or: .venv/bin/python -m streamlit run app/streamlit_app.py

Reads reports/results.json (committed, written by `ppa-lab memo`), so it runs without
downloading any data. All calculations are in ppa_lab.dashboard (tested).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# Import ppa_lab from src/ when the package is not installed (Streamlit Community Cloud
# installs only app/requirements.txt).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppa_lab.dashboard import (  # noqa: E402
    Assumptions,
    default_assumptions,
    hedging_table,
    load_results,
    offer,
    structures_table,
)
from ppa_lab.pricing.forwards import describe_forward  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/ankitpatel1661/ppa-lab/blob/main"
PARKS = {"Solar park · Borrentin · 114 MWp": "solar_park",
         "Wind park · Everswinkel · 28.5 MW": "wind_park"}
BLUE, ORANGE, GREEN, INK = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b"

st.set_page_config(page_title="ppa-lab · PPA price and risk", page_icon="⚡", layout="wide")

try:
    results = load_results(ROOT / "reports" / "results.json")
except FileNotFoundError as err:
    st.error(str(err))
    st.stop()


def stack_figure(s: dict) -> plt.Figure:
    layers = [("Forward\nfirst year", s["forward"], "total"), ("Shape", s["shape"], "step"),
              ("Later years:\ncurve, trend", s["trend"], "step"),
              ("Risk premium", -s["risk_premium"], "step"),
              ("Balancing,\nroute to market", -s["balancing"], "step"),
              ("Credit,\nliquidity", -s["credit"], "step"),
              ("Indicative\nprice", s["indicative"], "total")]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    level = 0.0
    for i, (_, value, kind) in enumerate(layers):
        if kind == "total":
            ax.bar(i, value, color=BLUE, width=0.6)
            level, top, text = value, value, f"{value:.1f}"
        else:
            ax.bar(i, value, bottom=level, color=ORANGE if value < 0 else GREEN, width=0.6)
            top, level = max(level, level + value), level + value
            text = f"{round(value, 1) + 0.0:+.1f}"          # no "-0.0"
        ax.text(i, top + 1.2, text, ha="center", fontsize=9, fontweight="bold", color=INK)
    ax.set_xticks(range(len(layers)), [name for name, _, _ in layers], fontsize=8)
    ax.set_ylabel("EUR/MWh")
    ax.set_ylim(0, 1.18 * max(s["forward"], s["indicative"]))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e2e2de")
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Sidebar: your assumptions
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Your assumptions")
    park = PARKS[st.radio("Park", list(PARKS))]
    d = default_assumptions(results, park)
    pool = st.radio("Which past represents the delivery year?",
                    ["Last 12 months (base case)", "Whole 2024-2026 window"],
                    help="Midday solar dips deepen as capacity grows; since v1.7 old days are "
                         "moved forward by that trend, so the choice matters little.")
    has_clause = bool(results["parks"][park].get("negative_prices"))
    clause = has_clause and st.radio(
        "Negative prices", ["Paid for every MWh (base case)",
                            "Clause: we stop producing and are not paid"],
        help="Under a plain PPA the park is paid the strike for every MWh, so it keeps "
             "producing at negative prices. With the clause it curtails: prices are per "
             "delivered MWh.").startswith("Clause")
    forward_text = describe_forward(results.get("forward") or {
        "price_eur_mwh": results.get("forward_assumption")}, results.get("forward_curve") or {},
        results["delivery_year"])
    forward_shift = st.slider("Shift of the forward curve (%)", -30, 30, 0, 5,
                              help=f"Base case: {forward_text}. The capture rate moves with "
                                   "the level, along the price model's response.") / 100
    drift = st.slider("Capture-rate trend (pp per year)", -3.0, 2.0, d.drift * 100, 0.5) / 100
    tenor = st.slider("Tenor (years)", 1, 15, d.tenor_years)
    rate = st.slider("Discount rate (%)", 0.0, 12.0, d.discount_rate * 100, 0.5) / 100
    degradation = st.slider("Output degradation (% per year)", 0.0, 1.5,
                            round(d.degradation * 100, 2), 0.1) / 100
    balancing = st.slider("Balancing and route to market (EUR/MWh)", 0.0, 5.0, d.balancing, 0.25)
    credit = st.slider("Credit and liquidity (EUR/MWh)", 0.0, 5.0, d.credit, 0.25)
    st.caption("Defaults = the Step 7 base case (config/project.toml).")

mine = Assumptions(balancing=balancing, credit=credit, drift=drift, degradation=degradation,
                   discount_rate=rate, tenor_years=tenor, forward_shift=forward_shift,
                   pool="recent" if pool.startswith("Last") else "whole", clause=clause)
result, base = offer(results, park, mine), offer(results, park, d)
s, b = result["stack"], base["stack"]
r = results["parks"][park]
start = results["delivery_year"]

# --------------------------------------------------------------------------- #
# Main page
# --------------------------------------------------------------------------- #
st.title("What fixed price for a renewable PPA, and how much risk is left?")
st.caption(f"ppa-lab {results.get('ppa_lab_version', '')} · German day-ahead prices, 31 ERA5 "
           f"weather years, {results['scenarios']} joint scenarios for {start} · illustrative "
           "analysis from public data, not an offer")

merchant = r["structures"]["merchant"]["cfar_eur"] / 1e6
pap = r["structures"]["pay_as_produced"]["cfar_eur"] / 1e6
unit = "EUR/MWh"
premia = r["premia_eur_mwh"]
if clause:
    neg = r["negative_prices"]
    pap = neg["cfar_clause_eur"] / 1e6
    unit = "EUR per delivered MWh"
    premia = neg["clause"]["premia_eur_mwh"]
    st.info(f"Negative-price clause: the park stops producing at negative prices "
            f"({neg['curtailment']['share']:.0%} of its output in {start}, more at lower "
            f"forwards) and is not paid for it, so it keeps what a plain PPA loses "
            f"({neg['curtailment']['value']:.1f} EUR per MWh of output in {start}). "
            f"Prices are per delivered MWh; per MWh of output the indicative price is about "
            f"{s['indicative'] * neg['clause']['tenor']['delivered_share']:.1f}.")
for col, label, value, note in zip(
        st.columns(4),
        (f"Indicative price, {tenor} years ({unit})", f"Fair price before risk ({unit})",
         "Buyer's risk premium, hedged (EUR/MWh)", "Producer's CFaR95 with the PPA (EUR m)"),
        (f"{s['indicative']:.1f}", f"{s['tenor_fair_price']:.1f}", f"{s['risk_premium']:.1f}",
         f"{pap:.2f}"),
        (f"{s['indicative'] - b['indicative']:+.1f} vs the base case",
         f"capture rate {s['fair_price'] / s['forward']:.2f} in {start}",
         f"{premia['unhedged']:.1f} without a baseload hedge",
         f"{merchant:.2f} if merchant (−{1 - pap / merchant:.0%} with the PPA)"), strict=True):
    col.metric(label, value)
    col.caption(note)

tab_price, tab_risk, tab_hedge, tab_built, tab_method = st.tabs(
    ["From forward to offer", "Risk by structure", "Hedging", "How it was built",
     "Method and limits"])

with tab_price:
    eeg = r.get("eeg")
    if eeg:
        st.info(
            f"This park is paid under the EEG: spot plus a monthly put on the onshore market "
            f"value at its award value ({eeg['award_eur_mwh']:g} EUR/MWh, assumed; the award is "
            f"not published). Over {results['tenor_years']} years that pays about "
            f"{eeg['tenor']['net']:.1f} EUR/MWh after the marketing fee, against "
            f"{eeg['ppa']['indicative']:.1f} for the PPA at the base case: the PPA here is a "
            "what-if (Step 7 report, section 6).")
    st.pyplot(stack_figure(s))
    years = result["years"].rename(columns={
        "forward_eur_mwh": "Forward (EUR/MWh)", "capture_rate": "Capture rate",
        "fair_price_eur_mwh": "Fair price (EUR/MWh)", "energy_mwh": "Energy (MWh)",
        "discount_factor": "Discount factor"})
    st.dataframe(years.style.format({"Forward (EUR/MWh)": "{:.1f}", "Capture rate": "{:.3f}",
                                     "Fair price (EUR/MWh)": "{:.1f}", "Energy (MWh)": "{:,.0f}",
                                     "Discount factor": "{:.3f}"}), width="stretch")
    st.caption(f"Expected energy P50 {r['p50_mwh'] / 1e3:.1f} GWh a year; one year in ten below "
               f"{r['p90_1y_mwh'] / 1e3:.1f} GWh (P90). Premium and costs per MWh of the first "
               "year apply to every year.")

with tab_risk:
    st.subheader(f"What each structure leaves with the producer ({start}, fair strikes)")
    st.dataframe(structures_table(results, park), width="stretch")
    p = r["premia_eur_mwh"]
    st.markdown(
        f"The buyer of a pay-as-produced PPA asks for **{p['joint']:.1f} EUR/MWh** after selling "
        f"a baseload forward ({p['profile']:.1f} profile, {p['volume']:.1f} volume); without the "
        f"hedge it would be {p['unhedged']:.1f}, but that is the price level, which the buyer can "
        "hedge almost for free.")

with tab_hedge:
    hedges = hedging_table(results, park)
    if hedges is None:
        st.info("No hedging results yet: run `ppa-lab hedging` and `ppa-lab memo` (Step 8).")
    else:
        h = results["hedging"]["parks"][park]
        st.subheader(f"If the park sold at spot: merchant risk by futures hedge ({start})")
        st.dataframe(hedges, width="stretch")
        st.caption("MW sold: futures sold, as a year-average MW. Hedge ratio = MW sold / the "
                   "park's average output. CFaR95 = expected revenue minus its 5% quantile.")
        best = h["strategies"]["cal_base_min_variance"]
        st.markdown(
            f"Selling **{best['hedge_ratio']:.0%} of the average output** as Cal base futures "
            f"cuts the merchant cash flow at risk by **{best['cfar_reduction']:.0%}**. The PPA "
            f"buyer's premium falls from {h['buyer']['premium_full_band']:.1f} to "
            f"{h['buyer']['premium_min_variance']:.1f} EUR/MWh with the minimum-variance hedge "
            f"({h['buyer']['min_variance_ratio']:.0%} of the average output).")
        m = h.get("market_check") or {}
        if m and abs(m["quote"] / m["model_forward"] - 1) > 0.05:
            st.warning(
                f"Market check: the latest Cal base quote, {m['quote']:.2f} EUR/MWh "
                f"({m['date']}), differs from the model's forward ({m['model_forward']:.1f}). At "
                f"the quote the indicative price is {m['indicative_market']:.1f} EUR/MWh.")
        quotes = [q for q in results["hedging"].get("market_quotes", [])
                  if q["product"] == "cal_base" and q["delivery_year"] == start]
        if quotes:
            st.caption("Published Cal-" + str(start)[2:] + " base quotes (EUR/MWh): " + ", ".join(
                f"{q['price_eur_mwh']:.2f} ({q['date']})"
                for q in sorted(quotes, key=lambda q: q["date"])) + ".")

with tab_built:
    steps = pd.DataFrame([
        (1, "Market data", "Prices and generation since 2021, checked and reconciled",
         "step01_market_data.md"),
        (2, "Capture prices", "What solar and wind earn vs the official market values",
         "step02_capture_prices.md"),
        (3, "PPA structures", "Cash flows and fair prices; back-test 2024-2025",
         "step03_ppa_structures.md"),
        (4, "Weather to power", "31 ERA5 weather years at two real sites; P50/P90",
         "step04_generation.md"),
        (5, "Price model", "Hourly prices: seasonality, daily mean reversion, analog days",
         "step05_price_model.md"),
        (6, "Joint scenarios", "Prices simulated for each weather year",
         "step06_joint_scenarios.md"),
        (7, "Pricing and risk", "Structures, premia, price stack, ten-year price",
         "step07_ppa_pricing.md"),
        (8, "Hedging", "Futures hedges, hedge ratio, buyer's hedge, market check",
         "step08_hedging.md"),
    ], columns=["Step", "What", "Result", "Report"])
    steps["Report"] = steps["Report"].map(lambda f: f"{REPO}/reports/{f}")
    st.dataframe(steps, hide_index=True, width="stretch",
                 column_config={"Report": st.column_config.LinkColumn("Report")})
    figures = ROOT / "reports" / "figures"
    left, right = st.columns(2)
    left.image(str(figures / "step06_capture_rates.png"),
               caption="Capture rates per scenario: prices linked to the weather vs not")
    right.image(str(figures / "step07_price_stack.png"), caption="Price stack, both parks")

with tab_method:
    st.markdown(f"""
- **Fair price** = E[Σ q P] / E[Σ q] over {results['scenarios']} joint scenarios: 31 weather
  years (ERA5, pvlib, windpowerlib) × simulated hourly prices that respond to that weather.
- **Risk premium** = 5% shortfall of the buyer's value per expected MWh, after selling a baseload
  forward for the expected average output.
- **Tenor price**: energy- and discount-weighted average of yearly fair prices.
- **Forward**: {forward_text}.
- **Limits**: forwards are published quotes from secondary sources (not EEX files), balancing and
  credit costs are illustrative, the price shape is calibrated on 2024-2026 (one market regime),
  the parks produce their potential output.

Code, tests and methodology: [github.com/ankitpatel1661/ppa-lab](https://github.com/ankitpatel1661/ppa-lab)
· [METHODOLOGY.md]({REPO}/METHODOLOGY.md) · [one-page memo]({REPO}/reports/step09_memo.md)
""")
