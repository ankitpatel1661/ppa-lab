"""ppa-lab dashboard: the PPA price and its risk, for your own assumptions, in English or German.

    make app            # or: .venv/bin/python -m streamlit run app/streamlit_app.py
    ...?lang=de         # opens the German version

Reads reports/results.json (committed, written by `ppa-lab memo`), so it runs without
downloading any data. All calculations are in ppa_lab.dashboard (tested); all texts in
ppa_lab.dashboard_text (English and German).
"""

from __future__ import annotations

import re
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
from ppa_lab.dashboard_text import (  # noqa: E402
    COLUMN_HELP,
    GLOSSARY,
    HEDGING_EXPLAINED,
    HELP,
    LANGS,
    METHOD,
    STRUCTURES_EXPLAINED,
    forward_text_de,
    number,
    percent,
    translator,
)
from ppa_lab.pricing.forwards import describe_forward  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPO = "https://github.com/ankitpatel1661/ppa-lab/blob/main"
PARKS = {"solar_park": "Solar park · Borrentin · 114 MWp",
         "wind_park": "Wind park · Everswinkel · 28.5 MW"}
POOLS = {"recent": "Last 12 months (base case)", "whole": "Whole 2024-2026 window"}
CLAUSE = {False: "Paid for every MWh (base case)",
          True: "Clause: we stop producing and are not paid"}
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

# --------------------------------------------------------------------------- #
# Language: from the link (?lang=de) or the switch
# --------------------------------------------------------------------------- #
with st.sidebar:
    asked = st.query_params.get("lang", "en")
    lang = st.radio("Language / Sprache", list(LANGS), format_func=LANGS.get, horizontal=True,
                    index=list(LANGS).index(asked) if asked in LANGS else 0, key="lang",
                    help=HELP["en"]["language"] + " / " + HELP["de"]["language"])
st.query_params["lang"] = lang
_ = translator(lang)
st.set_page_config(page_title=_("ppa-lab · PPA price and risk"))
H = HELP[lang]
COLS = COLUMN_HELP[lang]


def n(x: float, digits: int = 1, sign: bool = False) -> str:
    return number(x, digits, lang, sign)


def pc(x: float, digits: int = 0, sign: bool = False) -> str:
    return percent(x, digits, lang, sign)


def number_slider(text: str, low: float, high: float, step: float, value: float, key: str,
                  help: str, digits: int = 2) -> float:
    """A slider that writes its numbers the language's way ("2,18"), which st.slider cannot.
    The default stays on the scale even when it falls between the steps."""
    value = round(value, digits)
    scale = [round(low + i * step, digits) for i in range(round((high - low) / step) + 1)]
    return st.select_slider(text, sorted(set(scale) | {value}), value=value, key=key, help=help,
                            format_func=lambda v: n(v, digits))


def label(text: str) -> str:
    """A table label in the chosen language, including the composed ones."""
    if text.startswith("Build-out: "):
        return _("Build-out: {name}").format(name=_(text[len("Build-out: "):]))
    if text.endswith(" (base case)"):
        return _("{name} (base case)").format(name=_(text[:-len(" (base case)")]))
    return _(text)


def scenario_label(sc: dict) -> str:
    if lang == "en":
        return sc["label"]
    return _("{name}: solar +{pv} GW, storage +{storage} GWh a year").format(
        name=_(sc["label"].split(":")[0]), pv=f"{sc['pv_additions_gw']:g}".replace(".", ","),
        storage=f"{sc['storage_additions_gwh']:g}".replace(".", ","))


def md_table(header: tuple[str, ...], rows: list[tuple]) -> str:
    """A Markdown table from rows (keeps long table text out of single source lines)."""
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _h in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _digits(fmt: str | None) -> tuple[int, bool]:
    """Decimals and sign of a printf format ("%+.2f" -> 2, True); 0 for "localized"."""
    m = re.match(r"%(\+?)\.(\d)f", fmt or "")
    return (int(m.group(2)), m.group(1) == "+") if m else (0, False)


def show_table(df: pd.DataFrame, fmt: dict[str, str] | None = None,
               height: int | None = None, text_columns: tuple[str, ...] = ()) -> None:
    """A table with a tooltip on every column. In German the numbers are written out with
    German decimals (the number columns format the English way), labels translated."""
    fmt = fmt or {}
    if lang == "en":
        config = {c: (st.column_config.TextColumn(c, help=COLS.get(c), alignment="right")
                      if c in text_columns else
                      st.column_config.NumberColumn(c, help=COLS.get(c), format=fmt.get(c)))
                  for c in df.columns}
        st.dataframe(df, width="stretch", height=height or "auto", column_config=config)
        return
    out = df.copy()
    for c in out.columns:
        if c not in text_columns:
            digits, sign = _digits(fmt.get(c))
            out[c] = out[c].map(lambda v, d=digits, s=sign: "" if pd.isna(v) else n(v, d, s))
    if not pd.api.types.is_numeric_dtype(out.index):
        out.index = [label(i) for i in out.index]
    out.index.name = _(df.index.name) if df.index.name else None
    out.columns = [_(c) for c in df.columns]
    config = {_(c): st.column_config.TextColumn(_(c), help=COLS.get(c), alignment="right")
              for c in df.columns}
    st.dataframe(out, width="stretch", height=height or "auto", column_config=config)


def stack_figure(s: dict, tenor: int) -> plt.Figure:
    """The price stack: forward → fair price, first year → fair price, tenor → indicative."""
    layers = [(_("Forward\n{start}").format(start=start), s["forward"], "total", GREY),
              (_("Shape"), s["shape"], "step", None),
              (_("Fair price\n{start}").format(start=start), s["fair_price"], "total", BLUE),
              (_("Later years"), s["trend"], "step", None),
              (_("Fair price\n{tenor} years").format(tenor=tenor), s["tenor_fair_price"], "total",
               BLUE),
              (_("Risk premium"), -s["risk_premium"], "step", None),
              (_("Balancing"), -s["balancing"], "step", None),
              (_("Credit"), -s["credit"], "step", None),
              (_("Indicative\n{tenor} years").format(tenor=tenor), s["indicative"], "total", NAVY)]
    fig, ax = plt.subplots(figsize=(10, 3.9))
    level = 0.0
    for i, (_layer, value, kind, colour) in enumerate(layers):
        if kind == "total":
            ax.bar(i, value, color=colour, width=0.62)
            level, top, text = value, value, n(value)
        else:
            ax.bar(i, value, bottom=level, color=ORANGE if value < 0 else GREEN, width=0.62)
            top, level = max(level, level + value), level + value
            text = n(round(value, 1) + 0.0, 1, sign=True)          # no "-0.0"
        ax.text(i, top + 1.5, text, ha="center", fontsize=9, fontweight="bold", color=INK)
    ax.set_xticks(range(len(layers)), [name for name, *_rest in layers], fontsize=8)
    ax.set_ylabel(_("EUR/MWh"))
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
            label=_("Forward (baseload)"))
    ax.plot(x, years["fair_price_eur_mwh"], color=BLUE, lw=2.5, marker="o", ms=4,
            label=_("Fair price of the park's output"))
    for col, colour in (("forward_eur_mwh", GREY), ("fair_price_eur_mwh", BLUE)):
        ax.annotate(n(years[col].iloc[-1], 0), (x[-1], years[col].iloc[-1]), xytext=(6, -3),
                    textcoords="offset points", fontsize=9, color=colour, fontweight="bold")
    ax.set_ylabel(_("EUR/MWh"))
    ax.set_ylim(0, None)
    ax.set_xticks(x)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", color="#e2e2de")
    ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


def profile_figure(d: dict, colour: str) -> plt.Figure:
    """Average price and output by hour of day, in two panels (two units, no second axis)."""
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 4.4), sharex=True,
                                      gridspec_kw={"height_ratios": [3, 2]})
    hours = d["hour"]
    earned = d["capture_rate"] * d["mean_price"]
    top.plot(hours, d["price"], color=INK, lw=2.2, marker="o", ms=3.5)
    top.axhline(d["mean_price"], color=GREY, lw=1.5, ls="--",
                label=_("Average price {value}").format(value=n(d["mean_price"])))
    top.axhline(earned, color=colour, lw=2, ls="--",
                label=_("What the park earns {value}").format(value=n(earned)))
    top.legend(frameon=False, fontsize=8.5, loc="lower left", ncol=2)   # below the curve
    top.set_ylabel(_("EUR/MWh"))
    top.set_ylim(0, 1.12 * max(d["price"]))
    top.set_title(_("Average price by hour of day ({start} scenarios)").format(start=start),
                  fontsize=9, loc="left")
    bottom.bar(hours, d["output_mw"], color=colour, width=0.7)
    bottom.set_ylabel(_("Average output (MW)"), fontsize=8)
    bottom.set_xlabel(_("Hour of day"))
    bottom.set_xticks(range(0, 24, 2))
    for ax in (top, bottom):
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="y", color="#e2e2de")
        ax.set_axisbelow(True)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------- #
# Sidebar: your assumptions
# --------------------------------------------------------------------------- #
forward = results.get("forward") or {"price_eur_mwh": results.get("forward_assumption")}
curve = results.get("forward_curve") or {}
forward_text = (forward_text_de(forward, curve, start) if lang == "de" and forward.get("date")
                else describe_forward(forward, curve, start))
with st.sidebar:
    st.header(_("Your assumptions"), help=H["assumptions"])
    park = st.radio(_("Park"), list(PARKS), format_func=lambda p: _(PARKS[p]), key="park",
                    help=H["park"])
    d = default_assumptions(results, park)
    pool = st.radio(_("Which past represents the delivery year?"), list(POOLS),
                    format_func=lambda p: _(POOLS[p]), key="pool",
                    help=H["pool"].format(start=start))
    has_clause = bool(results["parks"][park].get("negative_prices"))
    clause = has_clause and st.radio(_("Negative prices"), list(CLAUSE),
                                     format_func=lambda c: _(CLAUSE[c]), key="clause",
                                     help=H["clause"])
    forward_shift = st.slider(_("Shift of the forward curve (%)"), -30, 30, 0, 5,
                              key="forward_shift",
                              help=H["forward"].format(forward_text=forward_text)) / 100
    bo = results["parks"][park].get("buildout")
    buildout = None
    if bo:
        names = list(bo["scenarios"])
        buildout = st.selectbox(
            _("Solar and storage build-out after {start}").format(start=start), names,
            index=names.index(bo["base"]), format_func=lambda k: scenario_label(bo["scenarios"][k]),
            key="buildout", help=H["buildout"])
    # The park's own defaults: one set of these per park, kept when the language changes.
    drift = number_slider(_("Capture-rate trend (pp per year)"), -3.0, 2.0, 0.5, d.drift * 100,
                          f"drift_{park}", H["drift"], digits=1) / 100
    tenor = st.slider(_("Tenor (years)"), 1, 15, d.tenor_years, key="tenor", help=H["tenor"])
    rate = number_slider(_("Discount rate (%)"), 0.0, 12.0, 0.5, d.discount_rate * 100, "rate",
                         H["rate"], digits=1) / 100
    degradation = number_slider(_("Output degradation (% per year)"), 0.0, 1.5, 0.1,
                                d.degradation * 100, f"degradation_{park}", H["degradation"],
                                digits=1) / 100
    balancing = number_slider(_("Balancing and route to market (EUR/MWh)"), 0.0, 5.0, 0.25,
                              d.balancing, f"balancing_{park}", H["balancing"])
    credit = number_slider(_("Credit and liquidity (EUR/MWh)"), 0.0, 5.0, 0.25, d.credit,
                           f"credit_{park}", H["credit"])
    st.caption(_("Defaults = the Step 7 base case (config/project.toml)."))

mine = Assumptions(balancing=balancing, credit=credit, drift=drift, degradation=degradation,
                   discount_rate=rate, tenor_years=tenor, forward_shift=forward_shift,
                   pool=pool, clause=clause, buildout=buildout)
result, base = offer(results, park, mine), offer(results, park, d)
s, b = result["stack"], base["stack"]
r = results["parks"][park]

# --------------------------------------------------------------------------- #
# Main page
# --------------------------------------------------------------------------- #
st.title(_("What fixed price for a renewable PPA, and how much risk is left?"))
st.caption(_("ppa-lab {version} · German day-ahead prices, 31 ERA5 weather years, {n} joint "
             "scenarios for {start} · illustrative analysis from public data, not an offer"
             ).format(version=results.get("ppa_lab_version", ""), n=n_scen, start=start))

merchant = r["structures"]["merchant"]["cfar_eur"] / 1e6
pap = r["structures"]["pay_as_produced"]["cfar_eur"] / 1e6
unit = _("EUR/MWh")
premia = r["premia_eur_mwh"]
if clause:
    neg = r["negative_prices"]
    pap = neg["cfar_clause_eur"] / 1e6
    unit = _("EUR per delivered MWh")
    premia = neg["clause"]["premia_eur_mwh"]
    st.info(_("Negative-price clause: the park stops producing at negative prices ({share} of "
              "its output in {start}, more at lower forwards) and is not paid for it, so it "
              "keeps what a plain PPA loses ({value} EUR per MWh of output in {start}). Prices "
              "are per delivered MWh; per MWh of output the indicative price is about "
              "{per_output}.").format(
        share=pc(neg["curtailment"]["share"]), start=start, value=n(neg["curtailment"]["value"]),
        per_output=n(s["indicative"] * neg["clause"]["tenor"]["delivered_share"])))
capture = s["fair_price"] / s["forward"]
for col, head, value, note, key in zip(
        st.columns(5),
        (_("Indicative price"), _("Fair price, {tenor} years").format(tenor=tenor),
         _("Fair price, {start}").format(start=start), _("Risk premium"),
         _("Cash flow at risk")),
        (n(s["indicative"]), n(s["tenor_fair_price"]), n(s["fair_price"]),
         n(s["risk_premium"]), n(pap, 2)),
        (_("{unit} over {tenor} years; {delta} vs the base case").format(
            unit=unit, tenor=tenor, delta=n(s["indicative"] - b["indicative"], sign=True)),
         _("{unit}, before the risk premium and costs").format(unit=unit),
         _("{unit}: forward {forward} × capture rate {capture}").format(
             unit=unit, forward=n(s["forward"]), capture=n(capture, 2)),
         _("EUR/MWh after a baseload hedge ({unhedged} without)").format(
             unhedged=n(premia["unhedged"])),
         _("EUR m a year with the PPA; {merchant} if merchant ({cut})").format(
             merchant=n(merchant, 2), cut=pc(pap / merchant - 1, sign=True))),
        ("indicative", "fair_tenor", "fair_first", "premium", "cfar"), strict=True):
    col.metric(head, value, help=H[key].format(start=start, n=n_scen))
    col.caption(note)

tab_price, tab_risk, tab_hedge, tab_built, tab_method = st.tabs(
    [_("From forward to offer"), _("Risk by structure"), _("Hedging"), _("How it was built"),
     _("Method and glossary")])

with tab_price:
    eeg = r.get("eeg")
    if eeg:
        st.info(_("This park is paid under the EEG: spot plus a monthly put on the onshore market "
                  "value at its award value ({award} EUR/MWh, assumed; the award is not "
                  "published). Over {years} years that pays about {net} EUR/MWh after the "
                  "marketing fee, against {ppa} for the PPA at the base case: the PPA here is a "
                  "what-if (Step 7 report, section 6).").format(
            award=n(eeg["award_eur_mwh"], 0), years=results["tenor_years"],
            net=n(eeg["tenor"]["net"]), ppa=n(eeg["ppa"]["indicative"])))
    st.subheader(_("The price, layer by layer"), help=H["layers"])
    st.pyplot(stack_figure(s, tenor))
    later = (_("The forward curve, the capture rate at each year's price level")
             + (_(", the build-out scenario") if buildout else "")
             + _(", degradation and discounting"))
    st.markdown(md_table((_("Layer"), _("EUR/MWh"), _("What it means")), [
        (_("Forward {start}").format(start=start), n(s["forward"]),
         _("The market price of a flat block of power in {start}").format(start=start)),
        (_("Shape"), n(s["shape"], sign=True),
         _("The park produces more when power is cheap: its capture rate is {capture}").format(
             capture=n(capture, 2))),
        ("**" + _("Fair price {start}").format(start=start) + "**", f"**{n(s['fair_price'])}**",
         _("Break-even price for {start}: what the output is worth at market prices").format(
             start=start)),
        (_("Later years"), n(s["trend"], sign=True), later),
        ("**" + _("Fair price, {tenor} years").format(tenor=tenor) + "**",
         f"**{n(s['tenor_fair_price'])}**",
         _("One fixed price that is fair over the whole contract")),
        (_("Risk premium"), n(-s["risk_premium"]),
         _("The buyer's charge for profile and volume risk it cannot hedge")),
        (_("Balancing, credit"), n(-(s["balancing"] + s["credit"])),
         _("Forecast errors at the imbalance price, marketing fee; credit and capital")),
        ("**" + _("Indicative price") + "**", f"**{n(s['indicative'])}**",
         _("What a buyer could accept: the bottom of the negotiation range")),
    ]))

    prof = r.get("daily_profile")
    if prof:
        st.subheader(_("Why the capture rate is {capture}").format(
            capture=n(prof["capture_rate"], 2)), help=H["capture"].format(start=start))
        st.pyplot(profile_figure(prof, ORANGE if park == "solar_park" else BLUE))
        daily, seasonal = prof["capture_daily_shape"], prof["capture_seasonal_shape"]
        cols = st.columns(4)
        cols[0].metric(_("Daily shape"), n(daily - 1, 2, sign=True), help=H["daily_shape"])
        cols[1].metric(_("Seasons"), n(seasonal - daily, 2, sign=True), help=H["seasons"])
        cols[2].metric(_("Weather"), n(prof["capture_rate"] - seasonal, 2, sign=True),
                       help=H["weather"])
        cols[3].metric(_("Capture rate"), n(prof["capture_rate"], 2),
                       help=H["capture_total"].format(start=start))

    st.subheader(_("Year by year"), help=H["years"])
    st.pyplot(years_figure(result["years"]))
    years = result["years"].rename(columns={
        "forward_eur_mwh": "Forward (EUR/MWh)", "capture_rate": "Capture rate",
        "fair_price_eur_mwh": "Fair price (EUR/MWh)", "energy_mwh": "Energy (MWh)",
        "discount_factor": "Discount factor"})
    years.index.name = "Year"
    years["Energy (MWh)"] = years["Energy (MWh)"].round(0)
    years = years[["Forward (EUR/MWh)", "Capture rate", "Fair price (EUR/MWh)", "Energy (MWh)",
                   "Discount factor"]]
    show_table(years, {"Forward (EUR/MWh)": "%.1f", "Capture rate": "%.3f",
                       "Fair price (EUR/MWh)": "%.1f", "Energy (MWh)": "localized",
                       "Discount factor": "%.3f"})
    st.subheader(_("What moves the price"), help=H["moves"])
    sens = sensitivities(results, park, mine)
    show_table(sens, {"Indicative (EUR/MWh)": "%.2f", "vs yours (EUR/MWh)": "%+.2f"},
               height=36 * (len(sens) + 1) + 4)
    bt = buildout_table(results, park, mine)
    if bt is not None:
        st.subheader(_("Solar and storage build-out"), help=H["buildout"])
        show_table(bt, {"Solar added (GW a year)": "%.1f", "Storage added (GWh a year)": "%.1f",
                        "Capture-rate fall (% a year)": "%.1f", "Fair price (EUR/MWh)": "%.2f",
                        "Indicative (EUR/MWh)": "%.2f"}, height=36 * (len(bt) + 1) + 4)
        st.caption(_("Storage decides solar's later years: only a storage boom keeps the capture "
                     "rate close to flat."))
    else:
        st.subheader(_("Volume"), help=H["volume"])
        v1, v2 = st.columns(2)
        v1.metric(_("P50 energy (GWh a year)"), n(r["p50_mwh"] / 1e3), help=H["p50"])
        v2.metric(_("P90, one year (GWh)"), n(r["p90_1y_mwh"] / 1e3), help=H["p90"])
    st.caption(_("Expected energy P50 {p50} GWh a year; one year in ten below {p90} GWh (P90). "
                 "Premium and costs per MWh of the first year apply to every year.").format(
        p50=n(r["p50_mwh"] / 1e3), p90=n(r["p90_1y_mwh"] / 1e3)))

with tab_risk:
    st.subheader(_("What each structure leaves with the producer ({start}, fair strikes)").format(
        start=start), help=H["structures"])
    table = structures_table(results, park).rename(columns={
        "Cash flow at risk 95% (EUR m)": "CFaR 95% (EUR m)", "Expected revenue (EUR m)":
        "Expected (EUR m)", "P5 revenue (EUR m)": "Bad year, P5 (EUR m)",
        "Output sold or paid (%)": "Output paid (%)"})
    table = table[[c for c in ("Strike (EUR/MWh)", "CFaR 95% (EUR m)", "Expected (EUR m)",
                               "Bad year, P5 (EUR m)", "Output paid (%)") if c in table]]
    table["Strike (EUR/MWh)"] = table["Strike (EUR/MWh)"].map(
        lambda v: _("spot") if pd.isna(v) else n(v, 2))
    show_table(table, {"CFaR 95% (EUR m)": "%.2f", "Expected (EUR m)": "%.2f",
                       "Bad year, P5 (EUR m)": "%.2f", "Output paid (%)": "%.0f"},
               text_columns=("Strike (EUR/MWh)",))
    with st.expander(_("What each structure means")):
        st.markdown(STRUCTURES_EXPLAINED[lang])
    p = r["premia_eur_mwh"]
    st.subheader(_("The buyer's risk premium"), help=H["premium"])
    cols = st.columns(4)
    cols[0].metric(_("Without a hedge (EUR/MWh)"), n(p["unhedged"]), help=H["unhedged"])
    cols[1].metric(_("After a baseload hedge (EUR/MWh)"), n(p["joint"]), help=H["hedged"])
    cols[2].metric(_("of which profile (EUR/MWh)"), n(p["profile"]), help=H["profile"])
    cols[3].metric(_("of which volume (EUR/MWh)"), n(p["volume"]), help=H["volume_risk"])
    st.markdown(_("The buyer of a pay-as-produced PPA asks for **{joint} EUR/MWh** after selling "
                  "a baseload forward; without the hedge it would be {unhedged}, but most of "
                  "that is the price level, which the buyer can hedge almost for free. {tech}'s "
                  "remaining risk is mostly **{kind}**.").format(
        joint=n(p["joint"]), unhedged=n(p["unhedged"]),
        tech=_("Solar" if park == "solar_park" else "Wind"),
        kind=_("profile" if p["profile"] >= p["volume"] else "volume")))
    neg = r.get("negative_prices")
    if neg:
        st.subheader(_("Negative prices"), help=H["clause"])
        cols = st.columns(3)
        cols[0].metric(_("Output at negative prices, {start}").format(start=start),
                       pc(neg["curtailment"]["share"], 1), help=H["neg_share"])
        cols[1].metric(_("Value of stopping (EUR per MWh of output)"),
                       n(neg["curtailment"]["value"], 2), help=H["neg_value"])
        cols[2].metric(_("Clause, 10 years (EUR per delivered MWh)"),
                       n(neg["clause"]["tenor"]["indicative"]), help=H["neg_clause"])

with tab_hedge:
    hedges = hedging_table(results, park)
    if hedges is None:
        st.info(_("No hedging results yet: run `ppa-lab hedging` and `ppa-lab memo` (Step 8)."))
    else:
        h = results["hedging"]["parks"][park]
        st.subheader(_("If the park sold at spot: merchant risk by futures hedge ({start})").format(
            start=start), help=H["hedge"])
        show_table(hedges, {"MW sold": "%.1f", "Hedge ratio (%)": "%.0f", "CFaR95 (EUR m)": "%.2f",
                            "CFaR cut (%)": "%.0f", "Variance removed (%)": "%.0f"})
        st.caption(_("MW sold: futures sold, as a year-average MW. Hedge ratio = MW sold / the "
                     "park's average output. CFaR95 = expected revenue minus its 5% quantile."))
        best = h["strategies"]["cal_base_min_variance"]
        st.markdown(_("Selling **{ratio} of the average output** as Cal base futures cuts the "
                      "merchant cash flow at risk by **{cut}**. The PPA buyer's premium falls "
                      "from {full} to {best} EUR/MWh with the minimum-variance hedge "
                      "({buyer_ratio} of the average output).").format(
            ratio=pc(best["hedge_ratio"]), cut=pc(best["cfar_reduction"]),
            full=n(h["buyer"]["premium_full_band"]), best=n(h["buyer"]["premium_min_variance"]),
            buyer_ratio=pc(h["buyer"]["min_variance_ratio"])))
        with st.expander(_("Why not hedge 100%, and why not months?")):
            st.markdown(HEDGING_EXPLAINED[lang])
        m = h.get("market_check") or {}
        if m and abs(m["quote"] / m["model_forward"] - 1) > 0.05:
            st.warning(_("Market check: the latest Cal base quote, {quote} EUR/MWh ({date}), "
                         "differs from the model's forward ({model}). At the quote the indicative "
                         "price is {indicative} EUR/MWh.").format(
                quote=n(m["quote"], 2), date=m["date"], model=n(m["model_forward"]),
                indicative=n(m["indicative_market"])))
        quotes = [q for q in results["hedging"].get("market_quotes", [])
                  if q["product"] == "cal_base" and q["delivery_year"] == start]
        if quotes:
            st.caption(_("Published Cal-{yy} base quotes (EUR/MWh): {quotes}.").format(
                yy=str(start)[2:], quotes=", ".join(
                    f"{n(q['price_eur_mwh'], 2)} ({q['date']})"
                    for q in sorted(quotes, key=lambda q: q["date"]))))

with tab_built:
    report = _("Report")
    steps = pd.DataFrame([
        ("1", _("Market data"), _("Prices and generation since 2021, checked and reconciled"),
         "step01_market_data.md"),
        ("2", _("Capture prices"), _("What solar and wind earn vs the official market values"),
         "step02_capture_prices.md"),
        ("2b", _("TSO data"), _("Official market values reproduced; balancing cost from reBAP"),
         "step02b_tso_data.md"),
        ("3", _("PPA structures"), _("Cash flows and fair prices; back-test 2024-2025"),
         "step03_ppa_structures.md"),
        ("4", _("Weather to power"), _("31 ERA5 weather years at two real sites; P50/P90"),
         "step04_generation.md"),
        ("5", _("Price model"),
         _("Hourly prices: seasonality, daily mean reversion, analog days"),
         "step05_price_model.md"),
        ("6", _("Joint scenarios"), _("Prices simulated for each weather year"),
         "step06_joint_scenarios.md"),
        ("7", _("Pricing and risk"), _("Structures, premia, price stack, ten-year price"),
         "step07_ppa_pricing.md"),
        ("8", _("Hedging"), _("Futures hedges, hedge ratio, buyer's hedge, market check"),
         "step08_hedging.md"),
    ], columns=[_("Step"), _("What"), _("Result"), report])
    steps[report] = steps[report].map(lambda f: f"{REPO}/reports/{f}")
    st.subheader(_("Nine steps from raw data to a price"), help=H["steps"])
    st.dataframe(steps, hide_index=True, width="stretch",
                 column_config={report: st.column_config.LinkColumn(report)})
    figures = ROOT / "reports" / "figures"
    left, right = st.columns(2)
    left.image(str(figures / "step06_capture_rates.png"),
               caption=_("Capture rates per scenario: prices linked to the weather vs not"))
    right.image(str(figures / "step07_price_stack.png"), caption=_("Price stack, both parks"))

with tab_method:
    st.markdown(METHOD[lang].format(n=n_scen, forward_text=forward_text, repo=REPO))
    with st.expander(_("Glossary"), expanded=True):
        st.markdown(md_table((_("Term"), _("Meaning")),
                             [(f"**{term}**", text) for term, text in GLOSSARY[lang]]))
