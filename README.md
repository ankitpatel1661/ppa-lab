# ppa-lab: Renewable PPA Pricing & Risk Engine

What fixed price should a renewable producer offer an industrial buyer for ten
years of solar or wind output, and how much risk is left in that deal?

`ppa-lab` answers that question with public data and transparent methods. It
combines German power prices, generation and weather data, simulates them
together, and prices power purchase agreements (PPAs) with their market, shape
and volume risks.

> **Status: Day 5 of 14 (ticket PPA-5, version 0.5.0).** Done so far: the
> market-data foundation (Day 1), capture prices reconciled against the official
> German market values (Day 2), the PPA structures with their pricing maths and a
> 2024-2025 back-test (Day 3, [methodology](METHODOLOGY.md)), site generation from
> 31 years of ERA5 weather with P50/P90 volumes (Day 4), and a stochastic hourly price
> model calibrated to a forward price and validated against history (Day 5).
> See the [backlog](docs/BACKLOG.md) for what comes next.

## Day 5 results: thousands of plausible price years

An hourly model of German day-ahead prices, fitted on 2024-01 to 2026-09 (24,095 hours):
arcsinh-transformed prices = monthly level + daily shape (season x day type x hour, with
the nine nationwide holidays) + a daily factor that reverts like an Ornstein-Uhlenbeck
process + intraday patterns resampled as whole historical days.

| | |
|---|---|
| Memory of the daily factor | phi = 0.521 per day, **half-life 1.06 days** |
| Validation (history inside the 5-95% range of 200 simulated paths) | **7 of 11** statistics: mean, spread, 5/50/95/99% quantiles, weekly autocorrelation |
| Still outside | 1% quantile and negative hours (6.2% in history, 4.9% in the model), autocorrelation at 1 and 24 hours |
| 2027 at an 85 EUR/MWh forward (500 paths) | annual average 5% / 50% / 95%: 55.9 / 84.2 / 117.5 EUR/MWh; 5.7% negative hours |
| Solar capture rate, 2025 output | **0.612** with simulated prices vs **0.555** with real ones |

- **Validation changed the model twice.** A textbook hourly AR(1) forgot yesterday within
  ten hours (24-hour autocorrelation 0.38-0.54 vs 0.70) and was replaced by the two-factor
  version; a wider search of the transform's scale moved it from 80 to 120 EUR/MWh
  (5 to 7 statistics inside).
- **The gap that matters:** within a month, sunnier days have cheaper middays (correlation
  −0.30 in 2025); in the model it is 0.00. Independent prices overstate what solar earns.
  Day 6 links weather and prices.

Full report: [`reports/day05_price_model.md`](reports/day05_price_model.md).

## Day 4 results: how much the parks produce, and how much that varies

Two illustrative parks at real locations, modelled hour by hour from ERA5 reanalysis
weather (1995-2025) with pvlib and windpowerlib:

| | Solar park, Lusatia (50 MWp) | Wind park, North Frisia (30 MW, V126-3.45) |
|---|---|---|
| P50 annual energy | 55.1 GWh = 1,102 kWh/kWp | 110.0 GWh = 3,668 full-load hours |
| Year-to-year variability (CoV) | 5.0% | 5.5% |
| P90, one year / 10-year average | −6.4% / −2.0% vs mean | −7.0% / −2.2% vs mean |
| Worst / best weather year | 2001: −10.7% / 2018: +8.9% | 2003: −9.8% / 1998: +9.9% |
| Trend 1995-2025 | +2.5% per decade (brightening) | +0.1% per decade |
| Hourly correlation with the national fleet | 0.92 | 0.72-0.75 |

- **Checks instead of a tie-out:** nobody publishes these parks' output, so the models are
  checked against national generation (Day 1) and priced like Day 2: the site capture
  rates are close to the national ones (solar 2025: 0.555 vs 0.516).
- **Two traps found and fixed:** ERA5 radiation from Open-Meteo is labelled at the end of
  its hour (shifted, and verified against the sun's position on every build), and the
  first wind site sat in an ERA5 cell that is partly sea (0 m elevation, offshore-like
  3,961 full-load hours); the park now sits 16 km inland.

Full report: [`reports/day04_generation.md`](reports/day04_generation.md).

## Day 3 results: what each PPA structure would have earned

A 50 MW solar park and a 30 MW wind park (national profiles, scaled) sign each contract
at the end of the previous year at last year's fair price, and deliver in 2024 and 2025.
Revenue per MWh produced; cash flows to the producer:

| EUR/MWh | Merchant | Pay-as-produced | PaP, no pay at negative prices | Baseload | Merchant + floor 0 |
|---|---|---|---|---|---|
| Solar 2024 | 46.48 | **72.25** | 59.04 | 63.14 | 49.26 |
| Solar 2025 | 45.95 | 46.48 | 35.22 | **35.14** | 49.25 |
| Wind 2024 | 64.54 | 78.44 | 73.50 | **81.20** | 65.03 |
| Wind 2025 | **77.27** | 64.54 | 59.63 | 66.46 | 77.71 |

- **A pay-as-produced PPA removes all price surprise** (realised minus the expectation at
  signing is 0.00 in every case); whether it beats merchant is hindsight.
- **A baseload PPA hedges the price level, not the shape:** on the solar park in 2025 it
  fell 11.34 EUR/MWh short of plan, worse than merchant, and produced a negative month.
- **A negative-price clause cost solar 11.26 EUR/MWh in 2025** (24% of the energy unpaid);
  the right to curtail at negative prices was worth 3.30 EUR/MWh.

Full report: [`reports/day03_ppa_structures.md`](reports/day03_ppa_structures.md);
the maths: [`METHODOLOGY.md`](METHODOLOGY.md).

## Day 2 results: what solar and wind really earn

The capture price is the energy-weighted price a technology earns:
sum(price x energy) / sum(energy) per quarter-hour. The capture rate divides it by the
baseload price.

| Capture rate (capture price, EUR/MWh) | 2023 | 2024 | 2025 | 2026 (Jan-Sep) |
|---|---|---|---|---|
| Baseload price | 95.18 | 78.51 | 89.32 | 107.72 |
| Solar | 0.76 (72.25) | 0.59 (46.48) | 0.51 (45.95) | 0.52 (55.68) |
| Wind onshore | 0.82 (78.44) | 0.82 (64.54) | 0.87 (77.27) | 0.89 (95.37) |
| Wind offshore | 0.91 (86.56) | 0.91 (71.40) | 0.96 (85.53) | 0.94 (101.65) |
| Solar energy sold at negative prices | 8.3% | 18.3% | 24.2% | 22.8% |

- **Solar cannibalisation:** in two years solar's capture rate fell from 0.76 to 0.51.
  In 2025 German solar earned EUR 3.0 billion less than the same energy at baseload.
- **Reconciliation with the official market values** (netztransparenz.de, legally the
  same formula): solar matches within 0.03 ct/kWh in 2023-2024 and 0.09 ct/kWh in
  2025 (tolerance ±0.10, fixed in advance). The spot price matches in 43 of 44 months.
  The one exception is June 2024, caused by the SDAC partial decoupling on
  26 June 2024.
- **Open investigation:** wind capture prices are 0.16 to 0.49 ct/kWh above the official
  values in every year. The evidence points to curtailment in the measured generation
  data versus the TSOs' online extrapolation. These references are deliberately left
  outside tolerance until that is tested (backlog PPA-2b).

![Capture rate by month](reports/figures/day02_capture_rate_monthly.png)

Full report: [`reports/day02_capture_prices.md`](reports/day02_capture_prices.md).
How it was built and investigated:
[learning track, Day 2](docs/learning_track/day02_capture_prices.md).

## Day 1 results

| DE-LU day-ahead | 2023 | 2024 | 2025 | 2026 (Jan-Sep) |
|---|---|---|---|---|
| Mean price (EUR/MWh, time-weighted) | 95.18 | 78.51 | 89.32 | 107.72 |
| Hours with negative prices | 301 | 457 | 576 | 471 |
| Longest negative streak (hours) | 36 | 18 | 20 | 18 |
| Lowest / highest price (EUR/MWh) | -500.00 / 524.27 | -135.45 / 936.28 | -250.32 / 583.40 | -499.99 / 747.10 |

Reconciliation: the 2023 and 2025 mean prices match the official values exactly
(2024 differs by −0.95 EUR/MWh, fully explained by the 26 June 2024 decoupling), and the
negative-hour counts match published figures within 2 hours. Data quality: 23 checks pass,
1 warning (one real interval at the -500 EUR/MWh floor), 0 failures; all 1,369 delivery
days complete.

The full numbers, the data-quality report and four charts are in
[`reports/day01_market_data.md`](reports/day01_market_data.md).

## Quickstart

```bash
make setup     # create .venv and install the project with dev tools
make test      # 167 offline tests, about 8 seconds
make all       # download data and weather, build datasets, check quality, write all reports
```

Explore the data interactively in the playground notebook (one section per sprint day):

```bash
make notebook       # opens notebooks/ppa_lab_playground.ipynb in JupyterLab
```

Every dataset and column is described in the [data dictionary](docs/data_dictionary.md).

Or step by step with the command-line tool:

```bash
.venv/bin/ppa-lab fetch     # download monthly raw files (cached, rate-limit aware)
.venv/bin/ppa-lab build     # build processed Parquet datasets
.venv/bin/ppa-lab check     # data-quality checks; exit code 1 on failure
.venv/bin/ppa-lab report    # reports/day01_market_data.md + figures
.venv/bin/ppa-lab capture   # reports/day02_capture_prices.md + figures
.venv/bin/ppa-lab ppa       # reports/day03_ppa_structures.md + figures
.venv/bin/ppa-lab weather   # ERA5 weather -> park generation -> reports/day04_generation.md
.venv/bin/ppa-lab prices    # price model: fit, validate, simulate -> reports/day05_price_model.md
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
  analysis/capture.py        capture prices and rates, official market-value comparison
  analysis/day02_report.py   Day 2 report and charts
  analysis/plotting.py       shared chart style
  analysis/day03_report.py   Day 3 report and charts
  pricing/contracts.py       cash flows of every PPA structure, fair prices, discounting
  pricing/backtest.py        historical back-test: parks, prior-year strikes, plan and surprise
  data/http.py               shared JSON client: timeouts, retries, Retry-After
  data/open_meteo.py         ERA5 weather client; end-of-hour -> interval-beginning conversion
  data/weather_pipeline.py   weather per site and year (raw cache) -> park generation
  weather/pv.py, wind.py     pvlib solar park, windpowerlib wind park
  weather/yields.py          annual energy per weather year, P50/P90
  analysis/generation.py     trend and checks against national data
  analysis/day04_report.py   Day 4 report and charts
  prices/calendar.py         local hour, season, day type, German holidays (Easter computed)
  prices/model.py            arcsinh price model: fit, simulate, calibrate the level to a forward
  prices/validation.py       simulated vs historical statistics
  analysis/day05_report.py   Day 5 report and charts
  cli.py                     `ppa-lab` command
tests/                       offline tests with real API fixtures
notebooks/                   ppa_lab_playground.ipynb: interactive, one section per day
data/reference/              small published reference data (official market values)
exercises/                   hands-on exercises with automatic checks
METHODOLOGY.md               the pricing maths, conventions, assumptions and limitations
docs/decisions/              architecture decision records (ADRs)
docs/learning_track/         day-by-day explanations of what was built and why
reports/                     generated reports and figures
scripts/build_docs.py        learning-track Markdown -> PDF (`make docs`)
```

## Data sources and licence

- Day-ahead prices and generation: **CC BY 4.0, Bundesnetzagentur | SMARD.de, via
  [Energy-Charts](https://energy-charts.info) (Fraunhofer ISE)**.
- Weather: **ERA5 reanalysis** (ECMWF / Copernicus Climate Change Service) via the
  [Open-Meteo](https://open-meteo.com) archive API, CC BY 4.0 (contains modified Copernicus
  Climate Change Service information).
- Official market values (Marktwerte): the German TSOs, published on
  [netztransparenz.de](https://www.netztransparenz.de), stored in
  `data/reference/` for reconciliation.
- Code: MIT licence (see `LICENSE`). The licence does not cover downloaded data.

## Methodology notes

- Timestamps are stored in UTC at the start of each delivery interval
  ([ADR 0002](docs/decisions/0002-utc-storage-native-resolution.md)).
- Day-ahead prices are hourly until 30 Sep 2025 and quarter-hourly from 1 Oct 2025;
  averages are time-weighted across both.
- "Negative hours" means hours whose average price is below zero; two alternative
  definitions are reported because publishers differ.
