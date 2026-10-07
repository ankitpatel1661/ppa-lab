# ppa-lab: Renewable PPA Pricing & Risk Engine

What fixed price should a renewable producer offer an industrial buyer for ten
years of solar or wind output, and how much risk is left in that deal?

`ppa-lab` answers that question with public data and transparent methods. It
combines German power prices, generation and weather data, simulates them
together, and prices power purchase agreements (PPAs) with their market, shape
and volume risks.

> **Status: Day 1 of 14 (ticket PPA-1, version 0.1.0).** The market-data
> foundation is done: real German day-ahead prices and generation since 2023,
> data-quality checks and a reconciliation against published figures.
> See the [backlog](docs/BACKLOG.md) for what comes next.

## Day 1 results

| DE-LU day-ahead | 2023 | 2024 | 2025 | 2026 (Jan-Sep) |
|---|---|---|---|---|
| Mean price (EUR/MWh, time-weighted) | 95.18 | 78.51 | 89.32 | 107.72 |
| Hours with negative prices | 301 | 457 | 576 | 471 |
| Longest negative streak (hours) | 36 | 18 | 20 | 18 |
| Lowest / highest price (EUR/MWh) | -500.00 / 524.27 | -135.45 / 936.28 | -250.32 / 583.40 | -499.99 / 747.10 |

Reconciliation: the 2025 mean price matches the published 8.932 ct/kWh exactly, and the
negative-hour counts match published figures within 2 hours. Data quality: 23 checks pass,
1 warning (one real interval at the -500 EUR/MWh floor), 0 failures; all 1,369 delivery
days complete.

The full numbers, the data-quality report and four charts are in
[`reports/day01_market_data.md`](reports/day01_market_data.md).

## Quickstart

```bash
make setup     # create .venv and install the project with dev tools
make test      # 52 offline tests, about 1 second
make all       # download data, build datasets, check quality, write the report
```

Or step by step with the command-line tool:

```bash
.venv/bin/ppa-lab fetch     # download monthly raw files (cached, rate-limit aware)
.venv/bin/ppa-lab build     # build processed Parquet datasets
.venv/bin/ppa-lab check     # data-quality checks; exit code 1 on failure
.venv/bin/ppa-lab report    # reports/day01_market_data.md + figures
```

The first download takes 10 to 15 minutes because the free API is rate limited;
later runs use the local cache and finish in seconds.

## Project structure

```
config/project.toml          every assumption in one place (market, dates, limits, references)
src/ppa_lab/
  config.py                  typed settings
  timeutils.py               UTC, daylight saving, mixed 60/15-minute resolution
  data/energy_charts.py      API client (timeouts, retries, Retry-After) + pure parsers
  data/store.py              raw cache: monthly Parquet + manifest (checksum, licence)
  data/pipeline.py           fetch months, build processed datasets
  data/quality.py            data-quality checks (DST-aware completeness, price limits, physics)
  analysis/reconcile.py      annual statistics and tie-out against published figures
  analysis/day01_report.py   Day 1 report and charts
  cli.py                     `ppa-lab` command
tests/                       offline tests with real API fixtures
docs/decisions/              architecture decision records (ADRs)
docs/learning_track/         day-by-day explanations of what was built and why
reports/                     generated reports and figures
scripts/build_docs.py        learning-track Markdown -> PDF (`make docs`)
```

## Data sources and licence

- Day-ahead prices and generation: **CC BY 4.0, Bundesnetzagentur | SMARD.de, via
  [Energy-Charts](https://energy-charts.info) (Fraunhofer ISE)**.
- Code: MIT licence (see `LICENSE`). The licence does not cover downloaded data.

## Methodology notes

- Timestamps are stored in UTC at the start of each delivery interval
  ([ADR 0002](docs/decisions/0002-utc-storage-native-resolution.md)).
- Day-ahead prices are hourly until 30 Sep 2025 and quarter-hourly from 1 Oct 2025;
  averages are time-weighted across both.
- "Negative hours" means hours whose average price is below zero; two alternative
  definitions are reported because publishers differ.
