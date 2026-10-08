"""Typed access to config/project.toml.

Every assumption (market, dates, limits, data sources, reference values) lives in
the TOML file. This module turns it into immutable dataclasses so the rest of the
code gets autocompletion, type checking and a single source of truth.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
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

    def price_limit_on(self, day: date) -> PriceLimit:
        """Return the clearing-price limits in force on a given delivery day."""
        applicable = [lim for lim in self.price_limits if lim.effective_from <= day]
        if not applicable:
            raise ValueError(f"No price limit configured for delivery day {day}")
        return max(applicable, key=lambda lim: lim.effective_from)


def load_settings(path: Path | None = None, root: Path | None = None) -> Settings:
    """Load and validate the project configuration."""
    path = path or DEFAULT_CONFIG
    root = root or PROJECT_ROOT
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    market = raw["market"]
    ec = raw["sources"]["energy_charts"]
    paths = raw["paths"]

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
    )
    _validate(settings)
    return settings


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
