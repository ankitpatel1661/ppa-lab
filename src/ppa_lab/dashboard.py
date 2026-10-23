"""Logic behind the dashboard (app/streamlit_app.py), kept free of Streamlit so it is tested.

The dashboard reads `reports/results.json`, a committed copy of the Step 7 results written
by `ppa-lab memo`, so it runs without downloading any data. From those numbers it rebuilds
the offer for any assumptions the viewer chooses: costs, capture-rate trend, solar and
storage build-out, degradation, discount rate, tenor, a shift of the forward curve and which
historical days represent the delivery year.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ppa_lab.hedging.hedge import STRATEGIES
from ppa_lab.pricing.risk import level_shift, tenor_price

RESULTS = Path(__file__).resolve().parents[2] / "reports" / "results.json"


@dataclass(frozen=True)
class Assumptions:
    balancing: float          # EUR/MWh
    credit: float             # EUR/MWh
    drift: float              # capture-rate change per year after the first
    degradation: float        # output loss per year
    discount_rate: float
    tenor_years: int
    forward_shift: float = 0.0   # relative change of the forward, e.g. -0.1
    pool: str = "recent"         # "recent" (configured analog pool) or "whole" (whole window)
    clause: bool = False         # negative-price clause: the park curtails, unpaid (v1.8)
    buildout: str | None = None  # build-out scenario after the delivery year (v1.11)


def load_results(path: Path = RESULTS) -> dict:
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found: run `ppa-lab pricing` and `ppa-lab memo` "
                                "(or `make all`) first")
    return json.loads(Path(path).read_text())


def default_assumptions(results: dict, park: str) -> Assumptions:
    """The assumptions of the Step 7 base case."""
    a = results["parks"][park]["assumptions"]
    bo = results["parks"][park].get("buildout")
    return Assumptions(balancing=a["balancing_eur_mwh"], credit=a["credit_eur_mwh"],
                       drift=a["capture_rate_drift"], degradation=a["degradation"],
                       discount_rate=results["discount_rate"],
                       tenor_years=results["tenor_years"], buildout=bo["base"] if bo else None)


def buildout_factors(results: dict, park: str, scenario: str | None,
                     tenor_years: int) -> dict[int, float] | None:
    """Capture-rate factor per contract year under a build-out scenario (Step 7, section 8):
    the scenario's factor per year, compounded from the delivery year."""
    bo = results["parks"][park].get("buildout")
    if not scenario or not bo:
        return None
    step, start = bo["scenarios"][scenario]["factor_per_year"], results["delivery_year"]
    return {start + i: step ** i for i in range(tenor_years)}


def offer(results: dict, park: str, a: Assumptions) -> dict:
    """Price stack and year-by-year table of the pay-as-produced offer.

    Layers (EUR/MWh): forward, shape (first year), trend over the tenor (forward curve and the
    capture rate's response to it, capture-rate trend, degradation), risk premium, balancing,
    credit; indicative = forward + shape + trend - premium - balancing - credit. The forward
    shift moves the whole curve, and the capture rate with it along the model's response to
    the price level (Step 7, PPA-8d). The premium and costs per MWh are applied to every year,
    as in Step 7. With the negative-price clause all of it is per delivered MWh: the park
    stops producing at negative prices and is not paid (Step 7, v1.8). A build-out scenario
    scales each later year's capture rate (Step 7, section 8).
    """
    r = results["parks"][park]
    volumes = None
    if a.clause:
        if not r.get("negative_prices"):
            raise ValueError("these results have no negative-price clause (v1.8 and later)")
        r = {**r, **r["negative_prices"]["clause"]}
        volumes = r["volume_response"]
    stack0 = r["stack_eur_mwh"]
    if a.pool == "whole" and r.get("whole_window"):
        fair1, premium = r["whole_window"]["fair_price"], r["whole_window"]["premium"]
    else:
        fair1, premium = stack0["fair_price"], stack0["risk_premium"]
    response = r.get("level_response")
    scale = 1.0 + a.forward_shift
    forward = stack0["forward"] * scale
    fair1 = forward * (fair1 / stack0["forward"]
                       + level_shift(response, stack0["forward"], forward))
    curve = {int(y): f_y * scale for y, f_y in (results.get("forward_curve") or {}).items()}
    years = tenor_price(fair1, forward, r["energy_mwh_expected"], results["delivery_year"],
                        a.tenor_years, a.discount_rate, capture_rate_drift=a.drift,
                        degradation=a.degradation, forward_curve=curve, level_response=response,
                        volume_response=volumes,
                        capture_rate_factors=buildout_factors(results, park, a.buildout,
                                                              a.tenor_years))
    tenor_fair = years.attrs["price"]
    stack = {"forward": forward, "shape": fair1 - forward, "fair_price": fair1,
             "trend": tenor_fair - fair1, "tenor_fair_price": tenor_fair,
             "risk_premium": premium, "balancing": a.balancing, "credit": a.credit}
    stack["indicative"] = tenor_fair - premium - a.balancing - a.credit
    return {"stack": stack, "years": years}


def sensitivities(results: dict, park: str, a: Assumptions) -> pd.DataFrame:
    """The indicative price when one assumption moves, the others as in `a`: what moves the
    price most. Rows: forward ±10%, capture-rate trend ±1 pp a year, discount rate ±2 pp,
    balancing and credit ±1 EUR/MWh together, and the extreme build-out scenarios."""
    base = offer(results, park, a)["stack"]["indicative"]
    cases = [
        ("Forward curve −10%", {"forward_shift": a.forward_shift - 0.10}),
        ("Forward curve +10%", {"forward_shift": a.forward_shift + 0.10}),
        ("Capture-rate trend −1 pp a year", {"drift": a.drift - 0.01}),
        ("Capture-rate trend +1 pp a year", {"drift": a.drift + 0.01}),
        ("Discount rate +2 pp", {"discount_rate": a.discount_rate + 0.02}),
        ("Discount rate −2 pp", {"discount_rate": max(a.discount_rate - 0.02, 0.0)}),
        ("Balancing and credit +1 EUR/MWh", {"balancing": a.balancing + 0.5,
                                             "credit": a.credit + 0.5}),
    ]
    bo = results["parks"][park].get("buildout")
    if bo and a.buildout:
        for name, sc in bo["scenarios"].items():
            if name != a.buildout:
                cases.append((f"Build-out: {sc['label'].split(':')[0]}", {"buildout": name}))
    rows = []
    for label, change in cases:
        value = offer(results, park, Assumptions(**{**a.__dict__, **change}))["stack"]["indicative"]
        rows.append((label, value, value - base))
    out = pd.DataFrame(rows, columns=["Change", "Indicative (EUR/MWh)", "vs yours (EUR/MWh)"])
    return out.set_index("Change").round(2)


def buildout_table(results: dict, park: str, a: Assumptions) -> pd.DataFrame | None:
    """The fair and indicative price under each solar and storage build-out scenario, the other
    assumptions as in `a`. None for a park without build-out scenarios (wind)."""
    bo = results["parks"][park].get("buildout")
    if not bo:
        return None
    rows = []
    for name, sc in bo["scenarios"].items():
        s = offer(results, park, Assumptions(**{**a.__dict__, "buildout": name}))["stack"]
        rows.append((sc["label"].split(":")[0] + (" (base case)" if name == bo["base"] else ""),
                     sc["pv_additions_gw"], sc["storage_additions_gwh"],
                     100 * (1 - sc["factor_per_year"]), s["tenor_fair_price"], s["indicative"]))
    return pd.DataFrame(rows, columns=[
        "Scenario", "Solar added (GW a year)", "Storage added (GWh a year)",
        "Capture-rate fall (% a year)", "Fair price (EUR/MWh)", "Indicative (EUR/MWh)",
    ]).set_index("Scenario").round(2)


STRUCTURE_LABELS = {
    "merchant": "Merchant, curtailing at negative prices",
    "merchant_no_curtailment": "Merchant, producing at negative prices",
    "pay_as_produced": "Pay-as-produced PPA",
    "pay_as_produced_clause": "Pay-as-produced, negative-price clause",
    "pay_as_produced_deemed": "Pay-as-produced, buyer curtails, deemed output paid",
    "merchant_floor": "Merchant + floor at 0 (premium paid)",
    "baseload": "Baseload PPA",
}


def structures_table(results: dict, park: str) -> pd.DataFrame:
    """The producer's revenue risk by structure (Step 7), in EUR m."""
    t = pd.DataFrame(results["parks"][park]["structures"]).T
    out = pd.DataFrame({
        "Strike (EUR/MWh)": t["fair_price_eur_mwh"],
        "Expected revenue (EUR m)": t["expected_revenue_eur"] / 1e6,
        "P5 revenue (EUR m)": t["p05_revenue_eur"] / 1e6,
        "Cash flow at risk 95% (EUR m)": t["cfar_eur"] / 1e6,
    })
    if "energy_share" in t:
        out.insert(1, "Output sold or paid (%)", 100 * t["energy_share"])
    out.index = [STRUCTURE_LABELS.get(k, k) for k in out.index]
    return out.astype(float).round(2)


def hedging_table(results: dict, park: str) -> pd.DataFrame | None:
    """Merchant risk by hedge (Step 8), or None when the results have no hedging section."""
    hedging = results.get("hedging", {}).get("parks", {}).get(park)
    if hedging is None:
        return None
    t = pd.DataFrame(hedging["strategies"]).T
    t.index = [STRATEGIES.get(key, key) for key in t.index]
    return pd.DataFrame({
        "MW sold": t["hedge_mw"].astype(float),
        "Hedge ratio (%)": 100 * t["hedge_ratio"].astype(float),
        "CFaR95 (EUR m)": t["cfar_eur"].astype(float) / 1e6,
        "CFaR cut (%)": 100 * t["cfar_reduction"].astype(float),
        "Variance removed (%)": 100 * t["effectiveness"].astype(float),
    }).round(2)
