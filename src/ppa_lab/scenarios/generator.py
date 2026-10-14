"""Scenario generator: weather years x price paths for one delivery year (Step 6).

Scenario s = (weather year Y, price path n). Its volumes are the parks' output in weather
year Y, placed on the delivery calendar date by date; its prices are simulated FOR that
weather (`linked=True`, the weather-price link) or independently of it (`linked=False`,
the Step 5 model, kept for comparison). One annual level is calibrated so that the average
price over all scenarios equals the forward; level uncertainty is added per scenario.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ppa_lab.prices.model import (
    PriceModel,
    inverse,
    random_streams,
    seasonal_mean,
    simulate_residuals,
    solve_level,
)
from ppa_lab.scenarios.link import WeatherLink, linked_residuals
from ppa_lab.scenarios.weather import place_on_delivery_hours, weather_days_for


@dataclass
class Scenarios:
    index: pd.DatetimeIndex                 # delivery hours, UTC, interval beginning
    weather_years: np.ndarray               # weather year of each scenario, shape (S,)
    prices: np.ndarray                      # EUR/MWh, shape (S, hours)
    generation: dict[str, np.ndarray]       # park -> MWh per hour, one row per weather year
    year_row: np.ndarray                    # row of each scenario in the generation matrices
    level: float                            # calibrated annual level (transformed units)
    linked: bool                            # prices conditioned on the weather?

    def volume(self, park: str) -> np.ndarray:
        """MWh per hour for every scenario, shape (S, hours)."""
        return self.generation[park][self.year_row]


def delivery_hours(year: int, tz: str) -> pd.DatetimeIndex:
    """Every local hour of a calendar year as a UTC index (8,760 or 8,784 hours)."""
    idx = pd.date_range(f"{year}-01-01", f"{year + 1}-01-01", freq="h", tz=tz, inclusive="left")
    return idx.tz_convert("UTC").rename("ts_utc")


def _year_seeds(seed: int, n: int) -> list[int]:
    return [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(seed).spawn(n)]


def build_scenarios(model: PriceModel, link: WeatherLink, generation: dict[str, pd.DataFrame],
                    features: pd.DataFrame, tz: str, delivery_year: int,
                    weather_years: list[int], paths_per_year: int, forward: float,
                    level_volatility: float = 0.0, seed: int = 0,
                    linked: bool = True) -> Scenarios:
    """Simulate `paths_per_year` price paths for each weather year (see module docstring).

    generation: park -> local day x 24 hours (MW, = MWh per hour); features: daily weather.
    """
    index = delivery_hours(delivery_year, tz)
    local = index.tz_convert(tz)
    codes, days = pd.factorize(local.normalize().tz_localize(None))
    days, hours = pd.DatetimeIndex(days), local.hour.to_numpy()

    residuals, volumes = [], {park: [] for park in generation}
    for year, year_seed in zip(weather_years, _year_seeds(seed, len(weather_years)), strict=True):
        wdays = weather_days_for(days, year)
        for park, matrix in generation.items():
            volumes[park].append(place_on_delivery_hours(matrix, wdays, codes, hours))
        if linked:
            weather = features.reindex(wdays).set_axis(days)
            residuals.append(linked_residuals(model, link, index, tz, weather, paths_per_year,
                                              year_seed))
        else:
            residuals.append(simulate_residuals(model, index, tz, paths_per_year, year_seed))
    x = np.vstack(residuals)

    mu0 = seasonal_mean(model, index, tz, annual_level=0.0)
    level = solve_level(mu0, x, model.scale, forward)
    shift = 0.0
    if level_volatility:
        shift = level_volatility * random_streams(seed)[1].standard_normal((x.shape[0], 1))
    n_years = len(weather_years)
    return Scenarios(
        index=index,
        weather_years=np.repeat(np.asarray(weather_years), paths_per_year),
        prices=inverse(mu0[None, :] + level + x + shift, model.scale),
        generation={park: np.vstack(rows) for park, rows in volumes.items()},
        year_row=np.repeat(np.arange(n_years), paths_per_year),
        level=level, linked=linked,
    )


def scenario_table(scenarios: Scenarios, parks: list[str]) -> pd.DataFrame:
    """One row per scenario: weather year, baseload price and, per park, energy, merchant
    revenue, capture price and capture rate (Step 2 definitions)."""
    p = scenarios.prices
    out = {"weather_year": scenarios.weather_years, "base_price": p.mean(axis=1)}
    for park in parks:
        q = scenarios.volume(park)
        mwh = q.sum(axis=1)
        revenue = (p * q).sum(axis=1)
        out[f"{park}_mwh"] = mwh
        out[f"{park}_revenue_eur"] = revenue
        out[f"{park}_capture_price"] = revenue / mwh
        out[f"{park}_capture_rate"] = revenue / mwh / out["base_price"]
    return pd.DataFrame(out).rename_axis("scenario")


def fair_price(table: pd.DataFrame, park: str) -> float:
    """Break-even pay-as-produced price over all scenarios: E[sum q P] / E[sum q] (Step 3)."""
    return float(table[f"{park}_revenue_eur"].sum() / table[f"{park}_mwh"].sum())
