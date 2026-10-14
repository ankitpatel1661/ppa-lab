"""Typed access to config/project.toml.

Every assumption (market, dates, limits, data sources, reference values) lives in
the TOML file. This module turns it into immutable dataclasses so the rest of the
code gets autocompletion, type checking and a single source of truth.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "project.toml"


@dataclass(frozen=True)
class PriceLimit:
    """Harmonised day-ahead clearing-price limits in force from a delivery day on."""

    effective_from: date
    min_eur_mwh: float
    max_eur_mwh: float


@dataclass(frozen=True)
class Reference:
    """A published number we reconcile our own calculation against."""

    metric: str
    year: int
    value: float
    tolerance: float
    source: str
    # Known cause of a difference beyond tolerance, found and documented by us.
    note: str = ""


@dataclass(frozen=True)
class Park:
    """An illustrative park for the PPA back-tests (national profile shape, scaled)."""

    name: str
    technology: str  # a key of ppa_lab.analysis.capture.TECHNOLOGIES
    capacity_mw: float
    full_load_hours: float  # MWh per MW and year (Step 3 national-profile back-test)
    site: str = ""
    latitude: float | None = None
    longitude: float | None = None
    # Technology-specific model parameters (pvlib / windpowerlib), e.g. tilt_deg.
    model: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PriceModelSettings:
    """Calibration window and simulation settings of the stochastic price model (Step 5)."""

    calibration_start: date
    calibration_end: date
    scale_eur_mwh: float
    n_paths: int
    seed: int
    delivery_year: int
    forward_eur_mwh: float
    level_volatility: float


@dataclass(frozen=True)
class ScenarioSettings:
    """Joint weather x price scenarios for the price model's delivery year (Step 6)."""

    weather_last_year: int           # weather years: weather.first_year .. this year
    paths_per_weather_year: int
    analog_window_days: int          # analog days within +-window of the same date
    analog_k: int                    # draw among the k nearest analog days
    validation_exclusion_days: int   # in-sample check: analogs at least this far away
    seed: int


@dataclass(frozen=True)
class PpaParkSettings:
    """Cost and trend assumptions of one park's PPA (Step 7)."""

    balancing_eur_mwh: float         # balancing and route-to-market costs
    credit_eur_mwh: float            # credit and liquidity
    capture_rate_drift: float        # change of the capture rate per year after the first
    degradation: float               # annual loss of output (share)


@dataclass(frozen=True)
class PpaSettings:
    """Pricing of a multi-year pay-as-produced PPA on the joint scenarios (Step 7)."""

    start_year: int
    tenor_years: int
    discount_rate: float
    risk_quantile: float
    analog_pool_start: date          # historical days that represent the delivery year
    parks: dict[str, PpaParkSettings]


@dataclass(frozen=True)
class MarketQuote:
    """A published forward price (Step 8 market check)."""

    product: str              # cal_base or cal_peak
    delivery_year: int
    price_eur_mwh: float
    date: date                # trading day of the quote
    source: str               # URL


@dataclass(frozen=True)
class HedgingSettings:
    """Hedging with futures (Step 8)."""

    backtest_years: tuple[int, ...]
    market_quotes: tuple[MarketQuote, ...] = ()


@dataclass(frozen=True)
class EnergyChartsSettings:
    base_url: str
    timeout_s: float
    max_retries: int
    pause_s: float
    license: str


@dataclass(frozen=True)
class Settings:
    timezone: str
    bidding_zone: str
    country: str
    start: date
    end: date
    price_limits: tuple[PriceLimit, ...]
    energy_charts: EnergyChartsSettings
    raw_dir: Path
    processed_dir: Path
    reports_dir: Path
    reference_dir: Path
    references: tuple[Reference, ...]
    parks: tuple[Park, ...] = ()
    delivery_years: tuple[int, ...] = ()
    floor_eur_mwh: float = 0.0
    weather_first_year: int = 1995
    weather_base_url: str = "https://archive-api.open-meteo.com/v1"
    weather_pause_s: float = 4.0
    weather_license: str = ""
    price_model: PriceModelSettings | None = None
    scenarios: ScenarioSettings | None = None
    ppa: PpaSettings | None = None
    hedging: HedgingSettings | None = None

    def price_limit_on(self, day: date) -> PriceLimit:
        """Return the clearing-price limits in force on a given delivery day."""
        applicable = [lim for lim in self.price_limits if lim.effective_from <= day]
        if not applicable:
            raise ValueError(f"No price limit configured for delivery day {day}")
        return max(applicable, key=lambda lim: lim.effective_from)


def _ppa(raw: dict) -> PpaSettings:
    parks = {name: PpaParkSettings(**values) for name, values in raw.get("parks", {}).items()}
    return PpaSettings(**{k: v for k, v in raw.items() if k != "parks"}, parks=parks)


def _hedging(raw: dict) -> HedgingSettings:
    quotes = tuple(MarketQuote(**q) for q in raw.get("market_quotes", []))
    return HedgingSettings(backtest_years=tuple(raw["backtest_years"]), market_quotes=quotes)


def load_settings(path: Path | None = None, root: Path | None = None) -> Settings:
    """Load and validate the project configuration."""
    path = path or DEFAULT_CONFIG
    root = root or PROJECT_ROOT
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    market = raw["market"]
    ec = raw["sources"]["energy_charts"]
    paths = raw["paths"]
    pricing = raw.get("pricing", {})
    weather = raw.get("weather", {})

    settings = Settings(
        timezone=raw["project"]["timezone"],
        bidding_zone=market["bidding_zone"],
        country=market["country"],
        start=market["start"],
        end=market["end"],
        price_limits=tuple(
            PriceLimit(
                effective_from=lim["effective_from"],
                min_eur_mwh=float(lim["min_eur_mwh"]),
                max_eur_mwh=float(lim["max_eur_mwh"]),
            )
            for lim in market["price_limits"]
        ),
        energy_charts=EnergyChartsSettings(
            base_url=ec["base_url"],
            timeout_s=float(ec["timeout_s"]),
            max_retries=int(ec["max_retries"]),
            pause_s=float(ec["pause_s"]),
            license=ec["license"],
        ),
        raw_dir=root / paths["raw"],
        processed_dir=root / paths["processed"],
        reports_dir=root / paths["reports"],
        reference_dir=root / paths["reference"],
        references=tuple(Reference(**ref) for ref in raw.get("reconciliation", [])),
        parks=tuple(_park(name, park) for name, park in pricing.get("parks", {}).items()),
        delivery_years=tuple(pricing.get("delivery_years", ())),
        floor_eur_mwh=float(pricing.get("floor_eur_mwh", 0.0)),
        weather_first_year=int(weather.get("first_year", 1995)),
        weather_base_url=weather.get("base_url", "https://archive-api.open-meteo.com/v1"),
        weather_pause_s=float(weather.get("pause_s", 4.0)),
        weather_license=weather.get("license", ""),
        price_model=PriceModelSettings(**raw["price_model"]) if "price_model" in raw else None,
        scenarios=ScenarioSettings(**raw["scenarios"]) if "scenarios" in raw else None,
        ppa=_ppa(raw["ppa"]) if "ppa" in raw else None,
        hedging=_hedging(raw["hedging"]) if "hedging" in raw else None,
    )
    _validate(settings)
    return settings


PARK_FIELDS = ("technology", "capacity_mw", "full_load_hours", "site", "latitude", "longitude")


def _park(name: str, table: dict) -> Park:
    """Known keys become Park fields; the rest are model parameters."""
    known = {k: v for k, v in table.items() if k in PARK_FIELDS}
    model = {k: v for k, v in table.items() if k not in PARK_FIELDS}
    return Park(name=name, **known, model=model)


def _validate(s: Settings) -> None:
    if not isinstance(s.start, date) or not isinstance(s.end, date):
        raise TypeError("market.start and market.end must be TOML dates, e.g. 2025-01-01")
    if s.start > s.end:
        raise ValueError(f"market.start ({s.start}) is after market.end ({s.end})")
    if not s.price_limits:
        raise ValueError("At least one [[market.price_limits]] entry is required")
    for lim in s.price_limits:
        if lim.min_eur_mwh >= lim.max_eur_mwh:
            raise ValueError(f"Invalid price limit {lim}")
    pm = s.price_model
    if pm is not None:
        if not (s.start <= pm.calibration_start < pm.calibration_end <= s.end):
            raise ValueError("price_model calibration window must lie inside market.start..end")
        if pm.delivery_year <= pm.calibration_end.year:
            raise ValueError("price_model.delivery_year must come after the calibration window")
    sc = s.scenarios
    if sc is not None:
        if pm is None:
            raise ValueError("[scenarios] needs [price_model]")
        if sc.weather_last_year < s.weather_first_year:
            raise ValueError("scenarios.weather_last_year must not be before weather.first_year")
    ppa = s.ppa
    if ppa is not None:
        if pm is None or sc is None:
            raise ValueError("[ppa] needs [price_model] and [scenarios]")
        if ppa.start_year != pm.delivery_year:
            raise ValueError("ppa.start_year must equal price_model.delivery_year (the scenarios' "
                             "year)")
        if not pm.calibration_start <= ppa.analog_pool_start <= pm.calibration_end:
            raise ValueError("ppa.analog_pool_start must lie inside the calibration window")
        unknown = set(ppa.parks) - {p.name for p in s.parks}
        if unknown:
            raise ValueError(f"[ppa.parks] names unknown parks: {sorted(unknown)}")
    hg = s.hedging
    if hg is not None:
        for y in hg.backtest_years:
            if y - 1 < s.start.year or y > s.end.year:
                raise ValueError(f"hedging backtest year {y} needs {y - 1} and {y} inside "
                                 f"{s.start}..{s.end}")
        known = {"cal_base", "cal_peak"}
        if any(q.product not in known for q in hg.market_quotes):
            raise ValueError(f"hedging.market_quotes products must be one of {sorted(known)}")
    if s.weather_first_year > s.start.year:
        raise ValueError("weather.first_year must not be after market.start")
    for y in s.delivery_years:
        # Strikes for delivery year Y are fixed from year Y-1: both must be complete years.
        if date(y - 1, 1, 1) < s.start or date(y, 12, 31) > s.end:
            raise ValueError(
                f"delivery year {y} needs {y - 1} (for the strikes) and {y} inside "
                f"{s.start}..{s.end}"
            )
