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
# Streamlit keeps imported modules between reruns and reloads only those next to this script.
# After a redeploy the new script would meet the old ppa_lab still in memory (v1.11 on Cloud:
# "Assumptions() got an unexpected keyword argument 'buildout'"), so import it fresh each run
# (about 1 ms).
for _name in [m for m in sys.modules if m == "ppa_lab" or m.startswith("ppa_lab.")]:
    del sys.modules[_name]
from ppa_lab.dashboard import (  # noqa: E402
    Assumptions,
    buildout_table,
    default_assumptions,
    hedging_table,
    load_results,
    offer,
    sensitivities,
    structures_table,
)
from ppa_lab.pricing.forwards import describe_forward  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/ankitpatel1661/ppa-lab/blob/main"
PARKS = {"Solar park · Borrentin · 114 MWp": "solar_park",
         "Wind park · Everswinkel · 28.5 MW": "wind_park"}
BLUE, ORANGE, GREEN, INK, NAVY, GREY = ("#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#1d2a6b",
                                        "#8a8984")

st.set_page_config(page_title="ppa-lab · PPA price and risk", page_icon="⚡", layout="wide")

try:
    results = load_results(ROOT / "reports" / "results.json")
except FileNotFoundError as err:
    st.error(str(err))
    st.stop()

start = results["delivery_year"]
n_scen = results["scenarios"]

# Explanations behind the ⓘ icons. Plain language first, then the formula or the source.
HELP = {
    "park": (
        "**Borrentin**: a 114 MWp ground-mounted solar park in Mecklenburg-Western Pomerania, "
        "about 121 GWh a year. **Everswinkel**: a 28.5 MW onshore wind park in North "
        "Rhine-Westphalia (four Nordex N149 and one N163), about 64 GWh a year, paid under the "
        "EEG. Both are modelled from public data: 31 years of ERA5 weather at the real site, "
        "calibrated to the published yearly output."),
    "pool": (
        f"Each simulated day of {start} borrows its hourly price pattern from a real day with "
        "similar weather. Older days have shallower midday dips, because there was less solar "
        "then. Since v1.7 every old day is moved forward by the measured yearly change of the "
        "daily shape, so the choice now changes the price by only a few cents. The base case "
        "uses the last 12 months."),
    "clause": (
        "**Paid for every MWh** (plain pay-as-produced): the park receives the fixed price even "
        "when the market price is negative, so it keeps producing, and the buyer sells that "
        "power at a loss. **Clause**: nothing is paid at negative prices, so the park switches "
        "off. The price is then per delivered MWh (higher), the park keeps the value of "
        "switching off, but takes back volume risk: sunny, cheap years have more negative "
        "hours."),
    "forward": (
        "The forward is today's market price for future delivery (EEX German power, Cal base). "
        "The model's first year averages it, each later year follows the forward curve. "
        "Moving it moves the whole curve, and solar's capture rate moves with it: at higher "
        "price levels midday hours are lifted, as 2023-2026 history confirms."),
    "buildout": (
        "How much solar and battery storage Germany adds each year after the first year. More "
        "solar means more power in the same sunny hours, so each solar MWh is worth less; "
        "storage moves midday power into the evening and slows that fall. The link is "
        "measured on 2023-2026 data: each point of solar share of demand lowered solar's "
        "capture rate by 5.3%."),
    "drift": (
        "An extra change of the capture rate each year, in percentage points, on top of the "
        "build-out scenario. Use it to test a view the scenarios do not cover: −1 means the "
        "capture rate falls one more point every year (0.55 → 0.54 → 0.53 …)."),
    "tenor": (
        "Contract length. The price is one fixed number for all years, so later years with "
        "lower forwards (Cal-28 104.75, Cal-29 87.58 EUR/MWh, then held flat) and lower "
        "capture rates pull it down. A shorter contract stays closer to the first year."),
    "rate": (
        "Discounts later years: a MWh in year t counts with weight (1 + r)^−(t + ½). A higher "
        "rate gives the near, more valuable years more weight, so the ten-year price moves up "
        "towards the first year's."),
    "degradation": (
        "Solar panels lose a little output every year (about 0.5%). Later years then carry less "
        "energy, so they weigh less in the ten-year price."),
    "balancing": (
        "What it costs to sell variable power: forecast errors are settled at the imbalance "
        "price (reBAP), and a direct marketer charges a fee. Measured from the TSOs' data over "
        "the last 12 months (solar 1.68, wind 1.05 EUR/MWh) plus a 0.5 fee."),
    "credit": (
        "A charge for the buyer's default risk and the capital the deal ties up over ten years. "
        "An illustrative assumption; in practice it comes from the buyer's credit rating."),
    "indicative": (
        "The price a buyer could accept: the **fair price** minus the buyer's **risk premium** "
        "minus **balancing** and **credit** costs. The bottom of the negotiation range; the fair "
        "price is the top. A model view from public data, not an offer."),
    "fair_tenor": (
        "The break-even fixed price over the whole contract, before any risk premium or cost: "
        "the yearly fair prices averaged with weights for energy and discounting. At this "
        "price neither side gains on average."),
    "fair_first": (
        f"The break-even price for {start} alone: total revenue at market prices divided by "
        f"total energy, over {n_scen} joint weather and price scenarios, "
        "E[Σ q·P] / E[Σ q]. It equals the forward times the **capture rate**, the share of the "
        "average price this park's output earns."),
    "premium": (
        "What the buyer asks for the risk it takes on: the shortfall of its value in a bad "
        "year (5% quantile) per MWh, after it has sold a baseload forward to hedge the price "
        "level. What is left is profile risk (the shape of the output against prices) and "
        "volume risk (how much the weather delivers)."),
    "cfar": (
        "Cash flow at risk: how much less than expected the park earns in a one-in-twenty "
        "year (expected revenue minus its 5% quantile), per year. A PPA fixes the price, so "
        "only volume risk is left."),
}

COLUMN_HELP = {
    "Forward (EUR/MWh)": "The market's price for that year: the Cal forward, held flat after the "
                         "last quoted year.",
    "Capture rate": "The share of the average price the park's output earns that year.",
    "Fair price (EUR/MWh)": "Forward × capture rate: the break-even price for that year alone.",
    "Energy (MWh)": "Expected output (P50), lower each year by degradation.",
    "Discount factor": "Weight of that year's money today: (1 + r)^−(t + ½).",
    "Strike (EUR/MWh)": "Each structure's own fair price: the strike at which it earns the same "
                        "as the market on average. Merchant has none: it sells at spot.",
    "Output paid (%)": "Share of the possible output that is produced and paid; below 100% "
                       "where the park stops at negative prices.",
    "Expected (EUR m)": "Average yearly revenue over the scenarios.",
    "Bad year, P5 (EUR m)": "Revenue in a one-in-twenty bad year (5% quantile).",
    "CFaR 95% (EUR m)": "Cash flow at risk: expected revenue minus the bad-year revenue, the risk "
                        "left with the producer. Smaller is safer.",
    "MW sold": "Futures sold, as a year-average MW.",
    "Hedge ratio (%)": "MW sold divided by the park's average output.",
    "CFaR95 (EUR m)": "Cash flow at risk with this hedge.",
    "CFaR cut (%)": "How much smaller the cash flow at risk is than without a hedge.",
    "Variance removed (%)": "Share of the revenue variance the hedge removes (hedge "
                            "effectiveness).",
    "Indicative (EUR/MWh)": "Fair price minus risk premium and costs, with that one change.",
    "vs yours (EUR/MWh)": "Difference to the indicative price with your settings.",
    "Solar added (GW a year)": "New solar capacity in Germany each year after the first year.",
    "Storage added (GWh a year)": "New battery storage each year.",
    "Capture-rate fall (% a year)": "How fast solar's capture rate falls under the scenario.",
}


def md_table(header: tuple[str, ...], rows: list[tuple], align: str = "") -> str:
    """A Markdown table from rows (keeps long table text out of single source lines)."""
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(align or "---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


GLOSSARY = [
    ("**PPA**", "Power purchase agreement: a long-term contract to buy a park's power at a fixed "
                "price"),
    ("**Pay-as-produced**", "The buyer pays the fixed price for every MWh the park produces"),
    ("**Baseload**", "A flat block of power, the same MW in every hour of the year"),
    ("**Forward, Cal base**", "Today's market price for a year of baseload power delivered in "
                              "the future (EEX)"),
    ("**Capture price**", "What a technology earns per MWh: revenue divided by energy"),
    ("**Capture rate**", "Capture price divided by the average price; below 1 when output falls "
                         "in cheap hours"),
    ("**Fair price**", "The fixed price at which neither side gains on average"),
    ("**Indicative price**", "Fair price minus the buyer's risk premium and costs"),
    ("**Risk premium**", "What the buyer charges for risk it cannot hedge, per MWh"),
    ("**Profile risk**", "Risk from the shape of the output against the shape of prices"),
    ("**Volume risk**", "Risk from how much the weather delivers"),
    ("**Cash flow at risk (CFaR95)**", "Expected revenue minus the revenue of a one-in-twenty "
                                       "bad year"),
    ("**P50 / P90**", "Energy exceeded in 50% / 90% of years"),
    ("**Negative prices**", "Hours when producers pay to deliver: too much power, too little "
                            "demand"),
    ("**Build-out scenario**", "An assumption on how much solar and storage Germany adds each "
                               "year"),
    ("**EEG market premium**", "The subsidy: market value topped up to the award value each "
                               "month, a strip of puts"),
    ("**reBAP**", "The German imbalance price, at which forecast errors are settled"),
]


def column_config(df: pd.DataFrame, fmt: dict[str, str] | None = None) -> dict:
    """Tooltips (and number formats) for the columns of a table."""
    fmt = fmt or {}
    return {c: st.column_config.NumberColumn(c, help=COLUMN_HELP.get(c), format=fmt.get(c))
            for c in df.columns if c in COLUMN_HELP}


def stack_figure(s: dict, tenor: int) -> plt.Figure:
    """The price stack: forward → fair price, first year → fair price, tenor → indicative."""
    layers = [(f"Forward\n{start}", s["forward"], "total", GREY),
              ("Shape", s["shape"], "step", None),
              (f"Fair price\n{start}", s["fair_price"], "total", BLUE),
              ("Later years", s["trend"], "step", None),
              (f"Fair price\n{tenor} years", s["tenor_fair_price"], "total", BLUE),
              ("Risk premium", -s["risk_premium"], "step", None),
              ("Balancing", -s["balancing"], "step", None),
              ("Credit", -s["credit"], "step", None),
              (f"Indicative\n{tenor} years", s["indicative"], "total", NAVY)]
    fig, ax = plt.subplots(figsize=(10, 3.9))
    level = 0.0
    for i, (_, value, kind, colour) in enumerate(layers):
        if kind == "total":
            ax.bar(i, value, color=colour, width=0.62)
            level, top, text = value, value, f"{value:.1f}"
        else:
            ax.bar(i, value, bottom=level, color=ORANGE if value < 0 else GREEN, width=0.62)
            top, level = max(level, level + value), level + value
            text = f"{round(value, 1) + 0.0:+.1f}"          # no "-0.0"
        ax.text(i, top + 1.5, text, ha="center", fontsize=9, fontweight="bold", color=INK)
    ax.set_xticks(range(len(layers)), [name for name, *_ in layers], fontsize=8)
    ax.set_ylabel("EUR/MWh")
    ax.set_ylim(0, 1.16 * max(s["forward"], s["fair_price"]))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e2e2de")
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def years_figure(years: pd.DataFrame) -> plt.Figure:
    """Forward and fair price per contract year: the gap is the capture rate."""
    fig, ax = plt.subplots(figsize=(10, 2.9))
    x = years.index.astype(int)
    ax.plot(x, years["forward_eur_mwh"], color=GREY, lw=2, marker="o", ms=4,
            label="Forward (baseload)")
    ax.plot(x, years["fair_price_eur_mwh"], color=BLUE, lw=2.5, marker="o", ms=4,
            label="Fair price of the park's output")
    for col, colour in (("forward_eur_mwh", GREY), ("fair_price_eur_mwh", BLUE)):
        ax.annotate(f"{years[col].iloc[-1]:.0f}", (x[-1], years[col].iloc[-1]),
                    xytext=(6, -3), textcoords="offset points", fontsize=9, color=colour,
                    fontweight="bold")
    ax.set_ylabel("EUR/MWh")
    ax.set_ylim(0, None)
    ax.set_xticks(x)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
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
    st.header("Your assumptions", help="Every number on the page follows these settings. The "
              "defaults are the base case of the analysis (Step 7 report).")
    park = PARKS[st.radio("Park", list(PARKS), help=HELP["park"])]
    d = default_assumptions(results, park)
    pool = st.radio("Which past represents the delivery year?",
                    ["Last 12 months (base case)", "Whole 2024-2026 window"], help=HELP["pool"])
    has_clause = bool(results["parks"][park].get("negative_prices"))
    clause = has_clause and st.radio(
        "Negative prices", ["Paid for every MWh (base case)",
                            "Clause: we stop producing and are not paid"],
        help=HELP["clause"]).startswith("Clause")
    forward_text = describe_forward(results.get("forward") or {
        "price_eur_mwh": results.get("forward_assumption")}, results.get("forward_curve") or {},
        start)
    forward_shift = st.slider("Shift of the forward curve (%)", -30, 30, 0, 5,
                              help=HELP["forward"] + f"\n\nBase case: {forward_text}.") / 100
    bo = results["parks"][park].get("buildout")
    buildout = None
    if bo:
        names = list(bo["scenarios"])
        buildout = st.selectbox(
            f"Solar and storage build-out after {start}", names,
            index=names.index(bo["base"]), format_func=lambda n: bo["scenarios"][n]["label"],
            help=HELP["buildout"])
    drift = st.slider("Capture-rate trend (pp per year)", -3.0, 2.0, d.drift * 100, 0.5,
                      help=HELP["drift"]) / 100
    tenor = st.slider("Tenor (years)", 1, 15, d.tenor_years, help=HELP["tenor"])
    rate = st.slider("Discount rate (%)", 0.0, 12.0, d.discount_rate * 100, 0.5,
                     help=HELP["rate"]) / 100
    degradation = st.slider("Output degradation (% per year)", 0.0, 1.5,
                            round(d.degradation * 100, 2), 0.1, help=HELP["degradation"]) / 100
    balancing = st.slider("Balancing and route to market (EUR/MWh)", 0.0, 5.0, d.balancing, 0.25,
                          help=HELP["balancing"])
    credit = st.slider("Credit and liquidity (EUR/MWh)", 0.0, 5.0, d.credit, 0.25,
                       help=HELP["credit"])
    st.caption("Defaults = the Step 7 base case (config/project.toml).")

mine = Assumptions(balancing=balancing, credit=credit, drift=drift, degradation=degradation,
                   discount_rate=rate, tenor_years=tenor, forward_shift=forward_shift,
                   pool="recent" if pool.startswith("Last") else "whole", clause=clause,
                   buildout=buildout)
result, base = offer(results, park, mine), offer(results, park, d)
s, b = result["stack"], base["stack"]
r = results["parks"][park]

# --------------------------------------------------------------------------- #
# Main page
# --------------------------------------------------------------------------- #
st.title("What fixed price for a renewable PPA, and how much risk is left?")
st.caption(f"ppa-lab {results.get('ppa_lab_version', '')} · German day-ahead prices, 31 ERA5 "
           f"weather years, {n_scen} joint scenarios for {start} · illustrative "
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
capture = s["fair_price"] / s["forward"]
for col, label, value, note, key in zip(
        st.columns(5),
        ("Indicative price", f"Fair price, {tenor} years", f"Fair price, {start}",
         "Risk premium", "Cash flow at risk"),
        (f"{s['indicative']:.1f}", f"{s['tenor_fair_price']:.1f}", f"{s['fair_price']:.1f}",
         f"{s['risk_premium']:.1f}", f"{pap:.2f}"),
        (f"{unit} over {tenor} years; {s['indicative'] - b['indicative']:+.1f} vs the base case",
         f"{unit}, before the risk premium and costs",
         f"{unit}: forward {s['forward']:.1f} × capture rate {capture:.2f}",
         f"EUR/MWh after a baseload hedge ({premia['unhedged']:.1f} without)",
         f"EUR m a year with the PPA; {merchant:.2f} if merchant (−{1 - pap / merchant:.0%})"),
        ("indicative", "fair_tenor", "fair_first", "premium", "cfar"), strict=True):
    col.metric(label, value, help=HELP[key])
    col.caption(note)

tab_price, tab_risk, tab_hedge, tab_built, tab_method = st.tabs(
    ["From forward to offer", "Risk by structure", "Hedging", "How it was built",
     "Method and glossary"])

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
    st.subheader("The price, layer by layer", help=(
        "Read left to right. Grey: the market's baseload forward. Blue: the fair price, first "
        "for the first year, then for the whole contract. Orange steps take value away, green "
        "steps add it. Navy: the indicative price, what is left after the buyer's risk premium "
        "and costs."))
    st.pyplot(stack_figure(s, tenor))
    later = ("The forward curve, the capture rate at each year's price level"
             + (", the build-out scenario" if buildout else "") + ", degradation and discounting")
    st.markdown(md_table(("Layer", "EUR/MWh", "What it means"), [
        (f"Forward {start}", f"{s['forward']:.1f}",
         f"The market price of a flat block of power in {start}"),
        ("Shape", f"{s['shape']:+.1f}".replace("-", "−"),
         f"The park produces more when power is cheap: its capture rate is {capture:.2f}"),
        (f"**Fair price {start}**", f"**{s['fair_price']:.1f}**",
         f"Break-even price for {start}: what the output is worth at market prices"),
        ("Later years", f"{s['trend']:+.1f}".replace("-", "−"), later),
        (f"**Fair price, {tenor} years**", f"**{s['tenor_fair_price']:.1f}**",
         "One fixed price that is fair over the whole contract"),
        ("Risk premium", f"−{s['risk_premium']:.1f}",
         "The buyer's charge for profile and volume risk it cannot hedge"),
        ("Balancing, credit", f"−{s['balancing'] + s['credit']:.1f}",
         "Forecast errors at the imbalance price, marketing fee; credit and capital"),
        ("**Indicative price**", f"**{s['indicative']:.1f}**",
         "What a buyer could accept: the bottom of the negotiation range"),
    ]))
    st.subheader("Year by year", help=(
        "Each contract year has its own forward and capture rate. The ten-year fair price is "
        "their average weighted by energy and discounting; hover over a column title for its "
        "meaning."))
    st.pyplot(years_figure(result["years"]))
    years = result["years"].rename(columns={
        "forward_eur_mwh": "Forward (EUR/MWh)", "capture_rate": "Capture rate",
        "fair_price_eur_mwh": "Fair price (EUR/MWh)", "energy_mwh": "Energy (MWh)",
        "discount_factor": "Discount factor"})
    years.index.name = "Year"
    years["Energy (MWh)"] = years["Energy (MWh)"].round(0)
    years = years[["Forward (EUR/MWh)", "Capture rate", "Fair price (EUR/MWh)", "Energy (MWh)",
                   "Discount factor"]]
    st.dataframe(years, width="stretch", column_config=column_config(years, {
        "Forward (EUR/MWh)": "%.1f", "Capture rate": "%.3f", "Fair price (EUR/MWh)": "%.1f",
        "Energy (MWh)": "localized", "Discount factor": "%.3f"}))
    st.subheader("What moves the price", help=(
        "Each row changes one assumption from your current settings and shows the new "
        "indicative price. The biggest numbers are the assumptions worth arguing about."))
    sens = sensitivities(results, park, mine)
    st.dataframe(sens, width="stretch", height=36 * (len(sens) + 1) + 4,
                 column_config=column_config(sens, {"Indicative (EUR/MWh)": "%.2f",
                                                    "vs yours (EUR/MWh)": "%+.2f"}))
    bt = buildout_table(results, park, mine)
    if bt is not None:
        st.subheader("Solar and storage build-out", help=HELP["buildout"])
        st.dataframe(bt, width="stretch", height=36 * (len(bt) + 1) + 4,
                     column_config=column_config(bt, {
                         "Solar added (GW a year)": "%.1f", "Storage added (GWh a year)": "%.1f",
                         "Capture-rate fall (% a year)": "%.1f", "Fair price (EUR/MWh)": "%.2f",
                         "Indicative (EUR/MWh)": "%.2f"}))
        st.caption("Storage decides solar's later years: only a storage boom keeps the "
                   "capture rate close to flat.")
    else:
        st.subheader("Volume", help="Annual energy over 31 weather years (1995-2025).")
        v1, v2 = st.columns(2)
        v1.metric("P50 energy (GWh a year)", f"{r['p50_mwh'] / 1e3:.1f}", help=(
            "The median weather year: exceeded in half of all years."))
        v2.metric("P90, one year (GWh)", f"{r['p90_1y_mwh'] / 1e3:.1f}", help=(
            "Exceeded in 9 years out of 10: the volume lenders size debt on."))
    st.caption(f"Expected energy P50 {r['p50_mwh'] / 1e3:.1f} GWh a year; one year in ten below "
               f"{r['p90_1y_mwh'] / 1e3:.1f} GWh (P90). Premium and costs per MWh of the first "
               "year apply to every year.")

with tab_risk:
    st.subheader(f"What each structure leaves with the producer ({start}, fair strikes)", help=(
        "Every structure is priced at its own fair strike, so on average they earn about the "
        "same. What differs is the spread: the cash flow at risk. Hover over a column title "
        "for its meaning."))
    table = structures_table(results, park).rename(columns={
        "Cash flow at risk 95% (EUR m)": "CFaR 95% (EUR m)", "Expected revenue (EUR m)":
        "Expected (EUR m)", "P5 revenue (EUR m)": "Bad year, P5 (EUR m)",
        "Output sold or paid (%)": "Output paid (%)"})
    table = table[[c for c in ("Strike (EUR/MWh)", "CFaR 95% (EUR m)", "Expected (EUR m)",
                               "Bad year, P5 (EUR m)", "Output paid (%)") if c in table]]
    table["Strike (EUR/MWh)"] = table["Strike (EUR/MWh)"].map(
        lambda v: "spot" if pd.isna(v) else f"{v:.2f}")
    config = column_config(table, {"CFaR 95% (EUR m)": "%.2f", "Expected (EUR m)": "%.2f",
                                   "Bad year, P5 (EUR m)": "%.2f", "Output paid (%)": "%.0f"})
    config["Strike (EUR/MWh)"] = st.column_config.TextColumn(
        "Strike (EUR/MWh)", help=COLUMN_HELP["Strike (EUR/MWh)"])
    st.dataframe(table, width="stretch", column_config=config)
    with st.expander("What each structure means"):
        st.markdown("""
- **Merchant**: the park sells every MWh at the day-ahead price. It carries the price level, the
  shape and the volume. Selling at spot it stops at negative prices (that is free).
- **Pay-as-produced PPA**: the buyer pays a fixed price for whatever the park produces. The buyer
  takes the price level and the shape; the volume is shared (the park earns less in a dull year).
- **Negative-price clause**: as pay-as-produced, but nothing is paid at negative prices, so the
  park stops producing. Higher price per delivered MWh, more volume risk for the park.
- **Buyer curtails, deemed output paid**: the buyer may switch the park off at negative prices
  but pays the lost output as if produced. The park keeps its income and the buyer the saving.
- **Baseload PPA**: the park delivers a flat band. The buyer takes the price level; the park must
  buy the shape back when it produces less than the band (at night, in winter).
""")
    p = r["premia_eur_mwh"]
    st.subheader("The buyer's risk premium", help=HELP["premium"])
    cols = st.columns(4)
    for col, label, value, tip in zip(cols, (
            "Without a hedge", "After a baseload hedge", "of which profile", "of which volume"),
            (p["unhedged"], p["joint"], p["profile"], p["volume"]), (
            "The buyer's risk if it does nothing: mostly the price level.",
            "After selling a baseload forward for the expected output: the risk it cannot hedge.",
            "From the shape of the output against prices (how deep the midday dip is).",
            "From how much the weather delivers, and the fact that windy and sunny years are "
            "cheap years."), strict=True):
        col.metric(f"{label} (EUR/MWh)", f"{value:.1f}", help=tip)
    st.markdown(
        f"The buyer of a pay-as-produced PPA asks for **{p['joint']:.1f} EUR/MWh** after selling "
        f"a baseload forward; without the hedge it would be {p['unhedged']:.1f}, but most of "
        "that is the price level, which the buyer can hedge almost for free. "
        f"{'Solar' if park == 'solar_park' else 'Wind'}'s remaining risk is mostly "
        f"**{'profile' if p['profile'] >= p['volume'] else 'volume'}**.")
    neg = r.get("negative_prices")
    if neg:
        st.subheader("Negative prices", help=HELP["clause"])
        cols = st.columns(3)
        cols[0].metric(f"Output at negative prices, {start}", f"{neg['curtailment']['share']:.1%}",
                       help="Share of the park's output that falls in hours with negative "
                            "day-ahead prices.")
        cols[1].metric("Value of stopping (EUR per MWh of output)",
                       f"{neg['curtailment']['value']:.2f}",
                       help="What a park that sells at spot saves by switching off at negative "
                            "prices; a plain PPA gives it away.")
        cols[2].metric("Clause, 10 years (EUR per delivered MWh)",
                       f"{neg['clause']['tenor']['indicative']:.1f}",
                       help="The indicative price with a negative-price clause, per MWh actually "
                            "delivered and paid.")

with tab_hedge:
    hedges = hedging_table(results, park)
    if hedges is None:
        st.info("No hedging results yet: run `ppa-lab hedging` and `ppa-lab memo` (Step 8).")
    else:
        h = results["hedging"]["parks"][park]
        st.subheader(f"If the park sold at spot: merchant risk by futures hedge ({start})", help=(
            "Selling futures fixes the price of part of the output in advance. Selling a product "
            "at its forward pays, per MW, the sum over its hours of (forward − spot): it gains "
            "when spot is low, exactly when the park earns little."))
        st.dataframe(hedges, width="stretch", column_config=column_config(hedges))
        st.caption("MW sold: futures sold, as a year-average MW. Hedge ratio = MW sold / the "
                   "park's average output. CFaR95 = expected revenue minus its 5% quantile.")
        best = h["strategies"]["cal_base_min_variance"]
        st.markdown(
            f"Selling **{best['hedge_ratio']:.0%} of the average output** as Cal base futures "
            f"cuts the merchant cash flow at risk by **{best['cfar_reduction']:.0%}**. The PPA "
            f"buyer's premium falls from {h['buyer']['premium_full_band']:.1f} to "
            f"{h['buyer']['premium_min_variance']:.1f} EUR/MWh with the minimum-variance hedge "
            f"({h['buyer']['min_variance_ratio']:.0%} of the average output).")
        with st.expander("Why not hedge 100%, and why not months?"):
            st.markdown("""
- **Below 100% for solar**: the park produces in cheap hours, so its revenue rises less than a
  flat band when prices rise. A full band over-hedges: in an expensive year the hedge loses more
  than the park gains. The minimum-variance amount balances the two.
- **Months add little**: the monthly amounts are estimated from 496 scenarios and mostly fit
  noise, some even come out negative. One Cal base contract does most of the work.
- **One year's P&L says nothing**: a hedge sold at a fair price wins in some years and loses in
  others. It is judged by the risk it removes, not by last year's result.
""")
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
        ("2b", "TSO data", "Official market values reproduced; balancing cost from reBAP",
         "step02b_tso_data.md"),
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
    steps["Step"] = steps["Step"].astype(str)                 # "2b" among the numbers
    steps["Report"] = steps["Report"].map(lambda f: f"{REPO}/reports/{f}")
    st.subheader("Nine steps from raw data to a price", help=(
        "Each step has a report with its numbers and checks, and a learning page in the "
        "repository. Click a report link to open it on GitHub."))
    st.dataframe(steps, hide_index=True, width="stretch",
                 column_config={"Report": st.column_config.LinkColumn("Report")})
    figures = ROOT / "reports" / "figures"
    left, right = st.columns(2)
    left.image(str(figures / "step06_capture_rates.png"),
               caption="Capture rates per scenario: prices linked to the weather vs not")
    right.image(str(figures / "step07_price_stack.png"), caption="Price stack, both parks")

with tab_method:
    st.markdown(f"""
- **Fair price** = E[Σ q P] / E[Σ q] over {n_scen} joint scenarios: 31 weather
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
    with st.expander("Glossary", expanded=True):
        st.markdown(md_table(("Term", "Meaning"), GLOSSARY))
