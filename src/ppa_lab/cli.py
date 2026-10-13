"""Command-line entry point.

    ppa-lab fetch    download raw monthly files that are not cached yet
    ppa-lab build    build the processed Parquet datasets from the raw cache
    ppa-lab check    run data-quality checks (exit code 1 if any check fails)
    ppa-lab report   write the Day 1 report and charts to reports/
    ppa-lab capture  write the Day 2 capture-price report and charts to reports/
    ppa-lab ppa      write the Day 3 PPA-structures back-test and charts to reports/
    ppa-lab weather  fetch ERA5 weather per site, build park generation, write the Day 4 report
    ppa-lab prices   calibrate and validate the stochastic price model, write the Day 5 report
    ppa-lab all      fetch + build + check + report + capture + ppa + weather + prices
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from ppa_lab.config import load_settings
from ppa_lab.data.energy_charts import EnergyChartsClient
from ppa_lab.data.open_meteo import OpenMeteoClient
from ppa_lab.data.pipeline import DATASETS, build_processed, fetch
from ppa_lab.data.quality import run_all
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather

log = logging.getLogger("ppa_lab")


def _client(settings) -> EnergyChartsClient:
    ec = settings.energy_charts
    return EnergyChartsClient(base_url=ec.base_url, timeout_s=ec.timeout_s,
                              max_retries=ec.max_retries)


def _weather_client(settings) -> OpenMeteoClient:
    return OpenMeteoClient(base_url=settings.weather_base_url, max_retries=6)


def cmd_fetch(args, settings) -> int:
    store = RawStore(settings.raw_dir)
    results = fetch(settings, _client(settings), store, tuple(args.datasets), refresh=args.refresh)
    summary = Counter((r.dataset, r.action) for r in results)
    for (dataset, action), n in sorted(summary.items()):
        log.info("%-6s %-10s %3d months", dataset, action, n)
    return 0


def cmd_build(args, settings) -> int:
    build_processed(settings, RawStore(settings.raw_dir))
    return 0


def cmd_check(args, settings) -> int:
    proc = settings.processed_dir
    prices = pd.read_parquet(proc / "prices_native.parquet")
    power = pd.read_parquet(proc / "power_15min.parquet")
    report = run_all(prices, power, settings)
    for r in report.results:
        level = {"pass": logging.INFO, "warn": logging.WARNING, "fail": logging.ERROR}[r.status]
        log.log(level, "[%s] %-6s %-36s %s", r.status.upper(), r.dataset, r.name, r.detail)
    c = report.counts()
    log.info("Data quality: %d pass, %d warn, %d fail", c["pass"], c["warn"], c["fail"])
    return 0 if report.ok else 1


def cmd_report(args, settings) -> int:
    from ppa_lab.analysis.day01_report import write_day01_report  # heavy import, load lazily

    paths = write_day01_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_capture(args, settings) -> int:
    from ppa_lab.analysis.day02_report import write_day02_report  # heavy import, load lazily

    paths = write_day02_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_ppa(args, settings) -> int:
    from ppa_lab.analysis.day03_report import write_day03_report  # heavy import, load lazily

    # A delivery year needs itself and the year before (for the strikes) as complete years.
    years = tuple(
        y for y in settings.delivery_years
        if date(y - 1, 1, 1) >= settings.start and date(y, 12, 31) <= settings.end
    )
    if not years:
        log.warning("Day 3 report skipped: no delivery year with a complete previous year "
                    "in %s..%s", settings.start, settings.end)
        return 0
    paths = write_day03_report(dataclasses.replace(settings, delivery_years=years))
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_weather(args, settings) -> int:
    from ppa_lab.analysis.day04_report import write_day04_report  # heavy import, load lazily

    store = RawStore(settings.raw_dir, source="open_meteo")
    results = fetch_weather(settings, _weather_client(settings), store,
                            refresh=getattr(args, "refresh", False))
    summary = Counter((r.dataset, r.action) for r in results)
    for (dataset, action), n in sorted(summary.items()):
        log.info("%-22s %-10s %3d years", dataset, action, n)
    build_generation(settings, store)
    paths = write_day04_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_prices(args, settings) -> int:
    from ppa_lab.analysis.day05_report import write_day05_report  # heavy import, load lazily

    pm = settings.price_model
    if pm is None or not (settings.start <= pm.calibration_start
                          and pm.calibration_end <= settings.end):
        log.warning("Day 5 report skipped: the price-model calibration window is not inside "
                    "%s..%s", settings.start, settings.end)
        return 0
    paths = write_day05_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_all(args, settings) -> int:
    steps = (cmd_fetch, cmd_build, cmd_check, cmd_report, cmd_capture, cmd_ppa, cmd_weather,
             cmd_prices)
    for step in steps:
        code = step(args, settings)
        if code:
            return code
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ppa-lab", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", help="path to a TOML config (default: config/project.toml)")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_text in (
        ("fetch", cmd_fetch, "download raw data"),
        ("build", cmd_build, "build processed datasets"),
        ("check", cmd_check, "run data-quality checks"),
        ("report", cmd_report, "write the Day 1 report"),
        ("capture", cmd_capture, "write the Day 2 capture-price report"),
        ("ppa", cmd_ppa, "write the Day 3 PPA-structures back-test"),
        ("weather", cmd_weather, "ERA5 weather -> park generation -> Day 4 report"),
        ("prices", cmd_prices, "calibrate and validate the price model -> Day 5 report"),
        ("all", cmd_all, "fetch, build, check, report, capture, ppa, weather and prices"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        if name == "weather":
            p.add_argument("--refresh", action="store_true",
                           help="re-download weather years even if cached")
        if name in ("fetch", "all"):
            p.add_argument("--datasets", nargs="+", choices=DATASETS, default=list(DATASETS))
            p.add_argument("--refresh", action="store_true",
                           help="re-download months even if cached")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    settings = load_settings(Path(args.config) if args.config else None)
    return args.func(args, settings)


if __name__ == "__main__":
    sys.exit(main())
