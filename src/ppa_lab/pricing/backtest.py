"""Historical back-test of PPA structures for an illustrative park.

Question: a park signed a contract at the end of year Y-1, at the price that would have
been fair for Y-1 (a naive stand-in for the forward price, which we do not have), and
delivered in year Y. What did each structure earn, and how volatile were its monthly
cash flows?

The park uses the national generation profile of its technology (Day 4 replaces it with
a site model), scaled so that it produces capacity x full-load hours in every year: that
removes the growth of the national fleet but keeps the real hour-by-hour shape.
"""

from __future__ import annotations

import pandas as pd

from ppa_lab.pricing.contracts import (
    baseload,
    collar,
    fair_baseload_price,
    fair_pay_as_produced_price,
    merchant,
    pay_as_produced,
)
from ppa_lab.timeutils import interval_minutes

STRUCTURE_LABELS = {
    "merchant": "Merchant (spot)",
    "pay_as_produced": "Pay-as-produced PPA",
    "pap_negative_clause": "PaP PPA, no payment at negative prices",
    "baseload": "Baseload PPA",
    "merchant_with_floor": "Merchant + floor",
}


def park_energy(
    national_mw: pd.Series, capacity_mw: float, full_load_hours: float, tz: str, years: list[int]
) -> pd.Series:
    """Energy (MWh per interval) of a park with the national profile shape.

    Each local year in `years` is scaled to capacity_mw x full_load_hours MWh; other
    years are left out (a partial year would otherwise get a full year's energy).
    """
    energy = national_mw * interval_minutes(national_mw.index) / 60.0
    year = pd.Index(national_mw.index.tz_convert(tz).year)
    keep = year.isin(years)
    energy, year = energy[keep], year[keep]
    scale = capacity_mw * full_load_hours / energy.groupby(year).sum()
    return (energy * scale.reindex(year).to_numpy()).rename("energy_mwh")


def _structures(p: pd.Series, q: pd.Series, k_pap: float, k_base: float, band_mwh: float,
                floor: float) -> pd.DataFrame:
    """Cash flows (EUR per interval) of every structure for one set of contract terms."""
    return pd.DataFrame(
        {
            "merchant": merchant(p, q),
            "pay_as_produced": pay_as_produced(p, q, k_pap),
            "pap_negative_clause": pay_as_produced(p, q, k_pap, pay_at_negative_prices=False),
            "baseload": baseload(p, q, k_base, band_mwh),
            "merchant_with_floor": collar(p, q, floor=floor),
        }
    )


def backtest(
    prices: pd.Series, energy: pd.Series, tz: str, delivery_years: list[int], floor: float
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Cash flows of each structure in the delivery years, the strikes, and the plan.

    Strikes for year Y come from year Y-1: the pay-as-produced strike is Y-1's capture
    price, the baseload strike Y-1's base price; the band delivers year Y's expected
    energy flat. The plan is what each structure would have earned per MWh had year Y
    looked like Y-1 (same terms applied to Y-1's prices and profile): the producer's
    expectation at signing, so realised minus plan is the surprise each structure left.

    Returns (cash flows indexed like `energy`, strikes by year, plan EUR/MWh by year).
    """
    prices = prices.loc[energy.index]
    year = energy.index.tz_convert(tz).year
    available = set(year)
    hours = interval_minutes(energy.index) / 60.0
    frames, strikes, plan = [], {}, {}
    for y in delivery_years:
        if y - 1 not in available:
            raise ValueError(f"delivery year {y} needs data for {y - 1} to fix the strikes")
        prev, cur = year == y - 1, year == y
        k_pap = fair_pay_as_produced_price(prices[prev], energy[prev])
        k_base = fair_baseload_price(prices[prev])
        band_mwh = energy[cur].sum() / cur.sum()  # expected annual energy, delivered flat
        terms = (k_pap, k_base, band_mwh, floor)
        frames.append(_structures(prices[cur], energy[cur], *terms))
        plan[y] = _structures(prices[prev], energy[prev], *terms).sum() / energy[prev].sum()
        strikes[y] = {
            "pay_as_produced_strike": k_pap,
            "baseload_strike": k_base,
            "band_mw": band_mwh / float(hours[cur].mean()),
        }
    strikes_table = pd.DataFrame.from_dict(strikes, orient="index").rename_axis("year")
    plan_table = pd.DataFrame.from_dict(plan, orient="index").rename_axis("year")
    return pd.concat(frames), strikes_table, plan_table


def summarise(cash: pd.DataFrame, energy: pd.Series, tz: str, plan: pd.DataFrame) -> pd.DataFrame:
    """Per year and structure: revenue, revenue per MWh, surprise against plan, worst month.

    Index (year, structure). Columns: revenue_eur_m, revenue_eur_per_mwh,
    vs_merchant_eur_per_mwh, plan_eur_per_mwh, vs_plan_eur_per_mwh, worst_month_eur_k.
    The spread of monthly revenue within a year is NOT reported as risk: it is mostly
    seasonality, which is known in advance. The surprise against plan is the risk.
    """
    local = cash.index.tz_convert(tz)
    year = local.year
    month = pd.PeriodIndex(local.tz_localize(None), freq="M")
    annual = cash.groupby(year).sum()
    produced = energy.loc[cash.index].groupby(year).sum()
    monthly = cash.groupby(month).sum()
    rows = []
    for y in annual.index:
        months = monthly[monthly.index.year == y]
        merchant_per_mwh = annual.loc[y, "merchant"] / produced.loc[y]
        for structure in cash.columns:
            per_mwh = annual.loc[y, structure] / produced.loc[y]
            rows.append(
                {
                    "year": y,
                    "structure": structure,
                    "revenue_eur_m": annual.loc[y, structure] / 1e6,
                    "revenue_eur_per_mwh": per_mwh,
                    "vs_merchant_eur_per_mwh": per_mwh - merchant_per_mwh,
                    "plan_eur_per_mwh": plan.loc[y, structure],
                    "vs_plan_eur_per_mwh": per_mwh - plan.loc[y, structure],
                    "worst_month_eur_k": months[structure].min() / 1e3,
                }
            )
    return pd.DataFrame(rows).set_index(["year", "structure"])
