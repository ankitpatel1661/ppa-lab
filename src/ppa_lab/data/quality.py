"""Data-quality (DQ) checks for prices and generation.

Every model result is only as good as its input. These checks encode what we
KNOW must be true about the data (physics, market rules, calendar rules) and
fail loudly when it is not. Typical bugs they catch:
- a time-zone shift (solar output at midnight),
- a missing or duplicated day around a daylight-saving change,
- a parsing error that produces impossible prices,
- an API change that silently drops a column.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from ppa_lab.config import Settings
from ppa_lab.timeutils import expected_intervals, interval_minutes, local_dates

Status = Literal["pass", "warn", "fail"]

REQUIRED_POWER_COLUMNS = ("solar_mw", "wind_onshore_mw", "wind_offshore_mw", "load_mw")


@dataclass(frozen=True)
class CheckResult:
    dataset: str
    name: str
    status: Status
    detail: str


@dataclass
class QualityReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.status != "fail" for r in self.results)

    def counts(self) -> dict[str, int]:
        return {s: sum(r.status == s for r in self.results) for s in ("pass", "warn", "fail")}

    def to_markdown(self) -> str:
        icon = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}
        lines = ["| Dataset | Check | Status | Detail |", "|---|---|---|---|"]
        for r in self.results:
            lines.append(f"| {r.dataset} | {r.name} | {icon[r.status]} | {r.detail} |")
        return "\n".join(lines)


def _basic_index_checks(df: pd.DataFrame, dataset: str) -> list[CheckResult]:
    out = []
    out.append(
        CheckResult(
            dataset, "not empty", "pass" if len(df) else "fail", f"{len(df):,} rows"
        )
    )
    tz_ok = isinstance(df.index, pd.DatetimeIndex) and str(df.index.tz) == "UTC"
    out.append(
        CheckResult(dataset, "index is UTC", "pass" if tz_ok else "fail", f"tz={df.index.tz}")
    )
    n_dup = int(df.index.duplicated().sum())
    out.append(
        CheckResult(dataset, "no duplicate timestamps", "pass" if n_dup == 0 else "fail",
                    f"{n_dup} duplicates")
    )
    mono = df.index.is_monotonic_increasing
    out.append(
        CheckResult(dataset, "sorted in time", "pass" if mono else "fail",
                    "monotonic increasing" if mono else "index not sorted")
    )
    return out


def _completeness(df: pd.DataFrame, settings: Settings, dataset: str) -> list[CheckResult]:
    """Each local delivery day must have 23/24/25 hours' worth of intervals."""
    minutes = interval_minutes(df.index)
    days = local_dates(df.index, settings.timezone)
    per_day = pd.DataFrame({"day": days, "res": minutes.to_numpy()}).groupby("day")["res"]
    counts, resolution = per_day.size(), per_day.agg(lambda s: int(s.mode().iloc[0]))

    bad = []
    for day, n in counts.items():
        res = int(resolution[day])
        if res <= 0 or 60 % res != 0:
            bad.append(f"{day} (irregular {res}-min spacing)")
            continue
        expected = expected_intervals(day, settings.timezone, res)
        if n != expected:
            bad.append(f"{day} ({n}/{expected})")
    all_days = pd.date_range(settings.start, settings.end, freq="D").date
    missing_days = sorted(set(all_days) - set(counts.index))

    results = [
        CheckResult(
            dataset,
            "complete delivery days (DST-aware)",
            "pass" if not bad else "fail",
            f"{len(counts) - len(bad)}/{len(counts)} days complete"
            + (f"; incomplete: {', '.join(bad[:5])}" if bad else ""),
        ),
        CheckResult(
            dataset,
            "covers configured range",
            "pass" if not missing_days else "fail",
            f"{settings.start} to {settings.end}"
            + (f"; {len(missing_days)} days missing, first {missing_days[0]}"
               if missing_days else ""),
        ),
    ]
    # Report resolution regimes, e.g. "60 min until 2025-09-30, 15 min from 2025-10-01".
    regimes = resolution.groupby((resolution != resolution.shift()).cumsum()).agg(
        ["first", lambda s: s.index[0], lambda s: s.index[-1]]
    )
    regimes.columns = ["res", "from", "to"]
    detail = "; ".join(f"{int(r.res)} min {r['from']} to {r['to']}" for _, r in regimes.iterrows())
    results.append(CheckResult(dataset, "resolution regimes", "pass", detail))
    return results


def check_prices(df: pd.DataFrame, settings: Settings) -> list[CheckResult]:
    ds = "prices"
    results = _basic_index_checks(df, ds)
    if not len(df):
        return results

    n_nan = int(df["price_eur_mwh"].isna().sum())
    results.append(CheckResult(ds, "no missing prices", "pass" if n_nan == 0 else "fail",
                               f"{n_nan} NaN values"))

    days = local_dates(df.index, settings.timezone)
    limits = {d: settings.price_limit_on(d) for d in sorted(set(days))}
    lo = np.array([limits[d].min_eur_mwh for d in days])
    hi = np.array([limits[d].max_eur_mwh for d in days])
    price = df["price_eur_mwh"].to_numpy()
    out_of_range = int(((price < lo) | (price > hi)).sum())
    results.append(
        CheckResult(
            ds,
            "within SDAC clearing-price limits",
            "pass" if out_of_range == 0 else "fail",
            f"{out_of_range} values outside limits; observed min {np.nanmin(price):.2f}, "
            f"max {np.nanmax(price):.2f} EUR/MWh",
        )
    )
    hits_floor = int((price <= lo).sum())
    results.append(
        CheckResult(
            ds,
            "intervals at the price floor",
            "warn" if hits_floor else "pass",
            f"{hits_floor} intervals at the harmonised minimum (real events, but worth a look)",
        )
    )
    results += _completeness(df, settings, ds)
    return results


def check_power(df: pd.DataFrame, settings: Settings) -> list[CheckResult]:
    ds = "power"
    results = _basic_index_checks(df, ds)
    if not len(df):
        return results

    missing_cols = [c for c in REQUIRED_POWER_COLUMNS if c not in df.columns]
    results.append(
        CheckResult(ds, "required columns present", "pass" if not missing_cols else "fail",
                    "missing: " + ", ".join(missing_cols) if missing_cols else
                    ", ".join(REQUIRED_POWER_COLUMNS))
    )
    for col in (c for c in REQUIRED_POWER_COLUMNS if c in df.columns):
        share = float(df[col].isna().mean())
        status: Status = "pass" if share == 0 else ("warn" if share < 0.01 else "fail")
        results.append(CheckResult(ds, f"{col} completeness", status, f"{share:.3%} missing"))

    if "solar_mw" in df.columns:
        solar = df["solar_mw"]
        results.append(
            CheckResult(ds, "solar is non-negative", "pass" if solar.min() >= -1 else "warn",
                        f"min {solar.min():.1f} MW")
        )
        # Physics check that catches time-zone bugs: no sun in Germany at 00:00-03:00.
        local_hour = df.index.tz_convert(settings.timezone).hour
        night = solar[(local_hour >= 0) & (local_hour < 3)]
        night_mean = float(night.mean()) if len(night) else 0.0
        results.append(
            CheckResult(ds, "no solar at night (00-03 local)",
                        "pass" if night_mean < 50 else "fail",
                        f"mean night-time solar {night_mean:.1f} MW")
        )
    results += _completeness(df, settings, ds)
    return results


def run_all(prices: pd.DataFrame, power: pd.DataFrame, settings: Settings) -> QualityReport:
    return QualityReport(check_prices(prices, settings) + check_power(power, settings))
