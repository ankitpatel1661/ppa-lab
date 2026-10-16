"""Command-line entry point.

    ppa-lab fetch    download raw monthly files that are not cached yet
    ppa-lab build    build the processed Parquet datasets from the raw cache
    ppa-lab check    run data-quality checks (exit code 1 if any check fails)
    ppa-lab report   write the Step 1 report and charts to reports/
    ppa-lab capture  write the Step 2 capture-price report and charts to reports/
    ppa-lab ppa      write the Step 3 PPA-structures back-test and charts to reports/
    ppa-lab weather  fetch ERA5 weather per site, build park generation, write the Step 4 report
    ppa-lab tso      download reBAP and the TSOs' online extrapolations from netztransparenz.de
                     (needs a free API client; see src/ppa_lab/data/netztransparenz.py)
    ppa-lab forecasts  download day-ahead wind and solar forecasts from ENTSO-E (needs the token)
    ppa-lab balancing  official market values and balancing costs from the TSO data, Step 2b report
    ppa-lab prices   calibrate and validate the stochastic price model, write the Step 5 report
    ppa-lab scenarios  joint weather x price scenarios for the delivery year, Step 6 report
    ppa-lab pricing  price the parks' PPAs: structures, risk premia, price stack, Step 7 report
    ppa-lab hedging  hedging the parks' output with power futures, Step 8 report
    ppa-lab memo     one-page management memo + reports/results.json for the dashboard (Step 9)
    ppa-lab all      fetch + build + check + report + capture + balancing + ppa + weather + prices
                     + scenarios + pricing + hedging + memo (tso and forecasts need credentials:
                     run them separately)
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ppa_lab.config import load_settings
from ppa_lab.data.energy_charts import EnergyChartsClient
from ppa_lab.data.netztransparenz import (
    DATASETS as TSO_DATASETS,
)
from ppa_lab.data.netztransparenz import (
    MISSING_CREDENTIALS,
    NetztransparenzClient,
    fetch_tso,
    load_credentials,
)
from ppa_lab.data.open_meteo import OpenMeteoClient
from ppa_lab.data.pipeline import DATASETS, build_processed, fetch
from ppa_lab.data.quality import run_all
from ppa_lab.data.store import RawStore
from ppa_lab.data.weather_pipeline import build_generation, fetch_weather

log = logging.getLogger("ppa_lab")
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


def cmd_tso(args, settings) -> int:
    credentials = load_credentials(PROJECT_ROOT / ".env")
    if credentials is None:
        log.error(MISSING_CREDENTIALS)
        return 2
    client = NetztransparenzClient(*credentials)
    store = RawStore(settings.raw_dir, source="netztransparenz")
    end = min(settings.end, date.today())
    start = datetime(settings.start.year, settings.start.month, settings.start.day)
    results = fetch_tso(client, store, list(args.datasets), start,
                        datetime(end.year, end.month, end.day), refresh=args.refresh)
    summary = Counter((d, a) for d, _, a in results)
    for (dataset, action), n in sorted(summary.items()):
        log.info("%-22s %-10s %3d months", dataset, action, n)
    return 0


def cmd_forecasts(args, settings) -> int:
    from ppa_lab.data.entsoe import EntsoeClient, fetch_forecasts, load_api_key
    key = load_api_key(PROJECT_ROOT / ".env")
    if key is None:
        log.error("ENTSO-E needs a token: ENTSOE_API_KEY in the environment or the .env file")
        return 2
    store = RawStore(settings.raw_dir, source="entsoe")
    end = min(settings.end, date.today())
    results = fetch_forecasts(EntsoeClient(key), store, pd.Timestamp(settings.start),
                              pd.Timestamp(end), refresh=args.refresh)
    summary = Counter(a for _, a in results)
    for action, n in sorted(summary.items()):
        log.info("wind_solar_forecast %-10s %3d months", action, n)
    return 0


def cmd_balancing(args, settings) -> int:
    from ppa_lab.analysis.step02b_report import write_step02b_report
    out = write_step02b_report(settings)
    log.info("Report written to %s", out["report"])
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
    from ppa_lab.analysis.step01_report import write_step01_report  # heavy import, load lazily

    paths = write_step01_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_capture(args, settings) -> int:
    from ppa_lab.analysis.step02_report import write_step02_report  # heavy import, load lazily

    paths = write_step02_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_ppa(args, settings) -> int:
    from ppa_lab.analysis.step03_report import write_step03_report  # heavy import, load lazily

    # A delivery year needs itself and the year before (for the strikes) as complete years.
    years = tuple(
        y for y in settings.delivery_years
        if date(y - 1, 1, 1) >= settings.start and date(y, 12, 31) <= settings.end
    )
    if not years:
        log.warning("Step 3 report skipped: no delivery year with a complete previous year "
                    "in %s..%s", settings.start, settings.end)
        return 0
    paths = write_step03_report(dataclasses.replace(settings, delivery_years=years))
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_weather(args, settings) -> int:
    from ppa_lab.analysis.step04_report import write_step04_report  # heavy import, load lazily

    store = RawStore(settings.raw_dir, source="open_meteo")
    results = fetch_weather(settings, _weather_client(settings), store,
                            refresh=getattr(args, "refresh", False))
    summary = Counter((r.dataset, r.action) for r in results)
    for (dataset, action), n in sorted(summary.items()):
        log.info("%-22s %-10s %3d years", dataset, action, n)
    build_generation(settings, store)
    paths = write_step04_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_prices(args, settings) -> int:
    from ppa_lab.analysis.step05_report import write_step05_report  # heavy import, load lazily

    pm = settings.price_model
    if pm is None or not (settings.start <= pm.calibration_start
                          and pm.calibration_end <= settings.end):
        log.warning("Step 5 report skipped: the price-model calibration window is not inside "
                    "%s..%s", settings.start, settings.end)
        return 0
    paths = write_step05_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_scenarios(args, settings) -> int:
    from ppa_lab.analysis.step06_report import write_step06_report  # heavy import, load lazily

    pm = settings.price_model
    if settings.scenarios is None or pm is None or not (
            settings.start <= pm.calibration_start and pm.calibration_end <= settings.end):
        log.warning("Step 6 report skipped: scenarios need the price model's calibration "
                    "window inside %s..%s", settings.start, settings.end)
        return 0
    paths = write_step06_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_pricing(args, settings) -> int:
    from ppa_lab.analysis.step07_report import write_step07_report  # heavy import, load lazily

    pm = settings.price_model
    if settings.ppa is None or settings.scenarios is None or pm is None or not (
            settings.start <= pm.calibration_start and pm.calibration_end <= settings.end):
        log.warning("Step 7 report skipped: pricing needs the scenarios and the price model's "
                    "calibration window inside %s..%s", settings.start, settings.end)
        return 0
    paths = write_step07_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


def cmd_hedging(args, settings) -> int:
    from ppa_lab.analysis.step08_report import write_step08_report  # heavy import, load lazily

    pm = settings.price_model
    if settings.hedging is None or settings.ppa is None or pm is None or not (
            settings.start <= pm.calibration_start and pm.calibration_end <= settings.end):
        log.warning("Step 8 report skipped: hedging needs the scenarios and the price model's "
                    "calibration window inside %s..%s", settings.start, settings.end)
        return 0
    paths = write_step08_report(settings)
    log.info("Report written to %s", paths["report"])
    return 0


MEMO_PDF = True  # render the memo to PDF when Chrome is available (tests switch it off)


def cmd_memo(args, settings) -> int:
    from ppa_lab.analysis.step09_memo import write_step09_memo

    paths = write_step09_memo(settings, pdf=MEMO_PDF)
    log.info("Memo written to %s", paths["memo"])
    return 0


def cmd_all(args, settings) -> int:
    steps = (cmd_fetch, cmd_build, cmd_check, cmd_report, cmd_capture, cmd_balancing, cmd_ppa,
             cmd_weather,
             cmd_prices, cmd_scenarios, cmd_pricing, cmd_hedging, cmd_memo)
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
        ("report", cmd_report, "write the Step 1 report"),
        ("capture", cmd_capture, "write the Step 2 capture-price report"),
        ("ppa", cmd_ppa, "write the Step 3 PPA-structures back-test"),
        ("weather", cmd_weather, "ERA5 weather -> park generation -> Step 4 report"),
        ("tso", cmd_tso, "reBAP and online extrapolations from netztransparenz.de"),
        ("forecasts", cmd_forecasts, "day-ahead wind and solar forecasts from ENTSO-E"),
        ("balancing", cmd_balancing, "market values and balancing costs -> Step 2b report"),
        ("prices", cmd_prices, "calibrate and validate the price model -> Step 5 report"),
        ("scenarios", cmd_scenarios, "joint weather x price scenarios -> Step 6 report"),
        ("pricing", cmd_pricing, "price the PPAs with their risk premia -> Step 7 report"),
        ("hedging", cmd_hedging, "hedging with power futures -> Step 8 report"),
        ("memo", cmd_memo, "one-page memo and the dashboard's results file -> Step 9"),
        ("all", cmd_all, "the whole pipeline, Steps 1 to 9"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.set_defaults(func=func)
        if name == "weather":
            p.add_argument("--refresh", action="store_true",
                           help="re-download weather years even if cached")
        if name == "forecasts":
            p.add_argument("--refresh", action="store_true",
                           help="re-download months even if cached")
        if name == "tso":
            p.add_argument("--datasets", nargs="+", choices=TSO_DATASETS,
                           default=list(TSO_DATASETS))
            p.add_argument("--refresh", action="store_true",
                           help="re-download months even if cached")
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
