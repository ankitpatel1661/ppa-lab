"""Risk on joint scenarios (Step 7): premia, cash flow at risk, structures, tenor price.

Arrays are (scenarios, hours): prices P in EUR/MWh and volumes q in MWh per hour, all
scenarios equally likely (METHODOLOGY sections 5 and 10).

Two views of the same contract:
- the PRODUCER sells its output; its risk is the spread of its annual revenue (CFaR);
- the BUYER of a pay-as-produced PPA takes every MWh at the strike K and is worth
  sum_t q_t (P_t - K) per scenario. It sells a baseload forward against the expected
  average volume, so the price LEVEL is hedged; what is left is profile and volume risk,
  and the premium it asks for is the 5% shortfall of that value per expected MWh.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ppa_lab.pricing.contracts import (
    baseload,
    fair_pay_as_produced_price,
    merchant,
    pay_as_produced,
)

QUANTILE = 0.05


def cash_flow_at_risk(cash: np.ndarray, quantile: float = QUANTILE) -> float:
    """Expected cash flow minus its `quantile` (CFaR95 for 0.05)."""
    cash = np.asarray(cash, dtype="float64")
    return float(cash.mean() - np.quantile(cash, quantile))


def premium(values: np.ndarray, energy: np.ndarray, quantile: float = QUANTILE) -> float:
    """(E[value] - quantile of value) / E[energy]: the shortfall per expected MWh."""
    return cash_flow_at_risk(values, quantile) / float(np.mean(energy))


def buyer_value(prices: np.ndarray, volumes: np.ndarray, strike: float,
                forward: float | None = None, band_mw: float | None = None) -> np.ndarray:
    """Value of a pay-as-produced PPA to its buyer, per scenario: sum_t q (P - K).

    With `forward` and `band_mw` the buyer has also sold a baseload band of `band_mw` MW at
    `forward` EUR/MWh: + band * sum_t (forward - P).
    """
    value = (volumes * (prices - strike)).sum(axis=1)
    if forward is not None and band_mw is not None:
        value = value + band_mw * (forward - prices).sum(axis=1)
    return value


def risk_premia(prices: np.ndarray, volumes: np.ndarray,
                quantile: float = QUANTILE) -> dict[str, float]:
    """Fair pay-as-produced price and the buyer's premia, EUR/MWh.

    - unhedged: the buyer's 5% shortfall without any hedge (includes the price level);
    - joint: after selling a baseload band at the average price (profile + volume risk);
    - profile: the same with the EXPECTED hourly volume in every scenario (shape only);
    - volume: joint - profile, i.e. what varying volumes, and their link to prices, add.
    """
    energy = volumes.sum(axis=1)
    hours = prices.shape[1]
    forward = float(prices.mean())                  # the model's average price (forward)
    band = float(energy.mean()) / hours
    k = fair_pay_as_produced_price(prices, volumes)
    expected_profile = np.broadcast_to(volumes.mean(axis=0), prices.shape)
    k_profile = fair_pay_as_produced_price(prices, expected_profile)
    joint = premium(buyer_value(prices, volumes, k, forward, band), energy, quantile)
    profile = premium(buyer_value(prices, expected_profile, k_profile, forward, band),
                      energy, quantile)
    return {
        "fair_price": k,
        "unhedged": premium(buyer_value(prices, volumes, k), energy, quantile),
        "joint": joint,
        "profile": profile,
        "volume": joint - profile,
    }


def curtail(prices: np.ndarray, volumes: np.ndarray, below: float | None) -> np.ndarray:
    """The output a park sells when it stops producing at prices below `below` (EUR/MWh):
    q_t 1[P_t >= below]. None: it always produces."""
    if below is None:
        return volumes
    return volumes * (prices >= below)


def structure_revenues(prices: np.ndarray, volumes: np.ndarray,
                       curtail_below: float | None = 0.0
                       ) -> dict[str, tuple[float | None, np.ndarray]]:
    """The producer's annual revenue per scenario under each structure, with its strike.

    Every structure is struck at its own fair price. A park that sells at spot, or is not
    paid at negative prices, stops producing below `curtail_below` (0: at negative prices;
    None: it always produces, as until v1.7): its output is q^c = `curtail`(q).

    - merchant: spot sale of q^c; merchant_no_curtailment: of q (for comparison)
    - pay_as_produced: K q, K = E[sum q P] / E[sum q]; paid for every MWh, the park produces
    - pay_as_produced_clause: nothing paid at negative prices, the park curtails:
      K_c q^c with K_c = E[sum q^c P] / E[sum q^c]
    - pay_as_produced_deemed: the buyer may curtail and pays the curtailed output as if
      produced: K_d q with K_d = E[sum q^c P] / E[sum q]
    - baseload: band B at the base price, the rest (q^c - B) at spot
    """
    sold = curtail(prices, volumes, curtail_below)
    energy = volumes.sum(axis=1)
    base = float(prices.mean())
    band = float(energy.mean()) / prices.shape[1]
    k = fair_pay_as_produced_price(prices, volumes)
    out = {"merchant": (None, merchant(prices, sold).sum(axis=1))}
    if curtail_below is not None:
        out["merchant_no_curtailment"] = (None, merchant(prices, volumes).sum(axis=1))
    out["pay_as_produced"] = (k, pay_as_produced(prices, volumes, k).sum(axis=1))
    if curtail_below is not None:
        k_c = fair_pay_as_produced_price(prices, sold)
        k_d = float((prices * sold).sum() / volumes.sum())
        out["pay_as_produced_clause"] = (k_c, pay_as_produced(prices, sold, k_c).sum(axis=1))
        out["pay_as_produced_deemed"] = (k_d, pay_as_produced(prices, volumes, k_d).sum(axis=1))
    out["baseload"] = (base, baseload(prices, sold, base, band).sum(axis=1))
    return out


def structure_table(prices: np.ndarray, volumes: np.ndarray, curtail_below: float | None = 0.0,
                    quantile: float = QUANTILE) -> pd.DataFrame:
    """Per structure (producer view): strike, share of the potential output sold or paid,
    expected and P5 revenue and CFaR."""
    potential = float(volumes.sum(axis=1).mean())
    sold = float(curtail(prices, volumes, curtail_below).sum(axis=1).mean())
    rows = {}
    for name, (strike, cash) in structure_revenues(prices, volumes, curtail_below).items():
        expected = float(cash.mean())
        paid_in_full = name in ("pay_as_produced", "pay_as_produced_deemed",
                                "merchant_no_curtailment")
        rows[name] = {
            "fair_price_eur_mwh": np.nan if strike is None else strike,
            "energy_share": 1.0 if paid_in_full else sold / potential,
            "expected_revenue_eur": expected,
            "p05_revenue_eur": float(np.quantile(cash, quantile)),
            "cfar_eur": cash_flow_at_risk(cash, quantile),
            "cfar_share": cash_flow_at_risk(cash, quantile) / expected,
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("structure")


def curtailment_value(prices: np.ndarray, volumes: np.ndarray, below: float = 0.0) -> dict:
    """What stopping below `below` is worth, per MWh of potential output: the share of the
    output it removes, the output-weighted mean price of those hours and the avoided loss
    E[sum q (below - P)+ 1[P < below]] / E[sum q] (EUR/MWh)."""
    removed = volumes * (prices < below)
    return {"share": float(removed.sum() / volumes.sum()),
            "mean_price": float((removed * prices).sum() / removed.sum()) if removed.any()
            else float("nan"),
            "value": float((removed * (below - prices)).sum() / volumes.sum())}


def _shape_capture(prices: np.ndarray, volumes: np.ndarray, keys: np.ndarray) -> float:
    """Capture rate if prices and volumes were their averages within each group of hours
    (`keys`, one per hour): Σ_k n_k q̄_k P̄_k / (Σ_k n_k q̄_k · P̄)."""
    revenue = energy = 0.0
    for k in np.unique(keys):
        cols = keys == k
        n, q, p = cols.sum(), volumes[:, cols].mean(), prices[:, cols].mean()
        revenue, energy = revenue + n * q * p, energy + n * q
    return float(revenue / energy / prices.mean())


def daily_profile(prices: np.ndarray, volumes: np.ndarray, index: pd.DatetimeIndex,
                  tz: str) -> dict:
    """Why the capture rate is what it is: average price and output by local hour of day over
    all scenarios, and the capture rate split into what the average shape explains and the
    rest.

    `prices`, `volumes`: shape (scenarios, hours); `index`: the hours (UTC). Returns hour,
    price (EUR/MWh) and output (MW) by hour of day; the time-average price; the capture rate;
    the capture rate from the daily shape alone (hour-of-day averages) and from the daily and
    seasonal shape (month x hour averages). The difference between the last and the capture
    rate is the weather: within a month and hour, windier or sunnier days are cheaper days.
    """
    local = index.tz_convert(tz)
    hour, month = local.hour.to_numpy(), local.month.to_numpy()
    mean = float(prices.mean())
    return {
        "hour": list(range(24)),
        "price": [float(prices[:, hour == h].mean()) for h in range(24)],
        "output_mw": [float(volumes[:, hour == h].mean()) for h in range(24)],
        "mean_price": mean,
        "capture_rate": float((prices * volumes).sum() / volumes.sum() / mean),
        "capture_daily_shape": _shape_capture(prices, volumes, hour),
        "capture_seasonal_shape": _shape_capture(prices, volumes, month * 24 + hour),
    }


def level_shift(response: dict | None, level_from: float, level_to: float) -> float:
    """Change of the capture rate when the price level moves from `level_from` to `level_to`.

    `response` = {"level": [...], "capture_rate": [...]}: the capture rate at each price level
    (EUR/MWh, increasing), interpolated linearly in ln(level) and flat beyond the ends. The
    price model's own response is measured by rebuilding the scenarios at each level (Step 7,
    PPA-8d). None: no change.
    """
    if not response:
        return 0.0
    return capture_rate_at(response, level_to) - capture_rate_at(response, level_from)


def capture_rate_at(response: dict, level: float) -> float:
    """The capture rate of a level response (see `level_shift`) at one price level."""
    return float(np.interp(np.log(level), np.log(response["level"]), response["capture_rate"]))


def tenor_price(fair_price: float, forward: float, energy_mwh: float, start_year: int,
                years: int, discount_rate: float, capture_rate_drift: float = 0.0,
                degradation: float = 0.0,
                forward_curve: dict[int, float] | None = None,
                level_response: dict | None = None,
                volume_response: dict | None = None,
                capture_rate_factors: dict[int, float] | None = None) -> pd.DataFrame:
    """One price for a multi-year pay-as-produced PPA from the first year's fair price.

    Year y: forward F_y = `forward` in the first year, then `forward_curve` where it gives the
    year; a year after the last quoted one keeps that quote (flat). Capture rate
    c_y = (c_0 + g(F_y) - g(F_0)) m_y + drift * (y - start) with c_0 = fair_price / forward, g
    the capture rate at a price level (`level_response`, see `level_shift`; none: g constant)
    and m_y the build-out factor of year y (`capture_rate_factors`; none: 1),
    fair price F_y c_y, energy E_y = energy * (1 - degradation)^(y - start) * v(F_y) / v(F_0)
    with v the share of the output delivered at a price level (`volume_response`
    {"level", "share"}, for a contract under which the park curtails; none: v constant),
    discount factor (1 + r)^-(y - start + 0.5) at mid-year. The tenor price is
    sum D E K / sum D E. Returned per year, with the tenor price in `.attrs["price"]`.
    """
    forward_curve = forward_curve or {}
    c0 = fair_price / forward
    rows = []
    f_y = forward
    for i in range(years):
        y = start_year + i
        f_y = forward_curve.get(y, f_y)
        factor = (capture_rate_factors or {}).get(y, 1.0)
        rate = ((c0 + level_shift(level_response, forward, f_y)) * factor
                + capture_rate_drift * i)
        delivered = 1.0
        if volume_response:
            delivered = (np.interp(np.log(f_y), np.log(volume_response["level"]),
                                   volume_response["share"])
                         / np.interp(np.log(forward), np.log(volume_response["level"]),
                                     volume_response["share"]))
        rows.append({
            "year": y, "forward_eur_mwh": f_y, "capture_rate": rate,
            "energy_mwh": energy_mwh * (1.0 - degradation) ** i * delivered,
            "discount_factor": (1.0 + discount_rate) ** -(i + 0.5),
        })
    table = pd.DataFrame(rows).set_index("year")
    table["fair_price_eur_mwh"] = table["forward_eur_mwh"] * table["capture_rate"]
    weights = table["discount_factor"] * table["energy_mwh"]
    table.attrs["price"] = float((weights * table["fair_price_eur_mwh"]).sum() / weights.sum())
    return table
