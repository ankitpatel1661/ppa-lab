# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.0] (Day 5, ticket PPA-5)

### Added
- Price calendar (`ppa_lab.prices.calendar`): local hour, season and day type with the nine
  nationwide German holidays (Easter computed).
- Stochastic hourly price model (`ppa_lab.prices.model`): arcsinh transform, monthly levels
  and daily shape (back-fitted), a daily AR(1) factor with seasonal shocks, intraday patterns
  resampled as whole historical days; `calibrate_level` to a forward price by bisection with
  common random numbers; optional level volatility; JSON save/load.
- Validation against history (`ppa_lab.prices.validation`): quantiles, negative share and
  autocorrelation with a 5-95% range across paths.
- Day 5 report (`ppa-lab prices`, `make prices`, part of `make all`) with three charts and
  `data/processed/price_model.json` for Day 6; `[price_model]` settings.
- Day 5 learning-track page, notebook section (5.1-5.7, "My solutions"), exercises;
  METHODOLOGY v0.2 (price model); data dictionary entries.

### Changed
- The arcsinh scale is 120 EUR/MWh, not 80: the first search (30-80) ended at its edge; over
  30-300 the validation meets 7 of 11 statistics from 120 on (80: 5). Level volatility 0.12
  (was 0.15) so that it keeps its meaning in EUR/MWh.

### Fixed
- METHODOLOGY section 7: four LaTeX commands (`\tfrac`, `\alpha`, `\frac`, `\right`) had
  been written as control characters in 0.4.0 and did not render.

### Found
- A single hourly AR(1) (version 1) forgets yesterday within about ten hours: 24-hour
  autocorrelation 0.38-0.54 vs 0.70 in history. Replaced by the two-factor model.
- Monthly demeaning biases the daily AR(1) estimate down by about (1 + 3 phi) / 30 (Kendall);
  correcting it did not improve validation, so the estimate is used as is.
- Real negative prices cluster just below zero (4.6% of hours between -10 and 0 EUR/MWh);
  the model has 1.5% there and too many deep ones.
- Prices independent of weather overstate the solar capture rate: 0.612 simulated vs 0.555
  real (2025 output); within a month, sunnier days have cheaper middays (correlation -0.30).

## [0.4.0] (Day 4, ticket PPA-4)

### Added
- ERA5 weather through the Open-Meteo archive API (`ppa_lab.data.open_meteo`): pure
  parser, conversion from end-of-hour radiation labels to interval-beginning hours, and a
  sun-position check of the timestamps (`radiation_timing_offset`).
- Weather pipeline (`ppa_lab.data.weather_pipeline`): one raw file per site and year with
  manifest (ERA5 grid point, licence, completeness), processed weather and generation.
- Site models: pvlib solar park (`ppa_lab.weather.pv`) and windpowerlib wind park with
  hourly shear (`ppa_lab.weather.wind`); P50/P90 and trends (`ppa_lab.weather.yields`,
  `ppa_lab.analysis.generation`).
- Day 4 report (`ppa-lab weather`, `make weather`, part of `make all`) with two charts.
- Sites and model specs in `[pricing.parks.*]`, `[weather]` settings; pvlib and
  windpowerlib as dependencies.
- Day 4 learning-track page, notebook section (4.1-4.6, "My solutions"), exercises;
  METHODOLOGY v0.1 (volume section); data dictionary entries.

### Changed
- Retry and back-off logic moved from the Energy-Charts client into a shared
  `JsonApiClient` (`ppa_lab.data.http`).

### Found
- Open-Meteo labels radiation at the end of its hour; without the shift solar output
  would sit one hour late against prices.
- The first wind site (54.50 N, 9.00 E) was an ERA5 cell with 0 m elevation (partly sea):
  3,961 full-load hours. Moved 0.25° inland (30 m): 3,668.

## [0.3.0] - 2026-10-08 (Day 3, ticket PPA-3)

### Added
- `ppa_lab.pricing.contracts`: cash flows per interval to the producer for merchant,
  pay-as-produced (with and without a negative-price clause), virtual PPA (CfD),
  floor / cap / collar and baseload PPAs; fair pay-as-produced and baseload prices
  (ratio of expectations, with discounting); works on pandas Series and NumPy scenarios.
- `ppa_lab.pricing.backtest`: illustrative parks from national profiles, strikes fixed
  from the previous year, plan (same terms on the previous year) and surprise.
- Day 3 report (`ppa-lab ppa`, `make ppa`, part of `make all`; skipped with a warning when
  the data range has no complete previous year) with two charts.
- `[pricing]` configuration (parks, delivery years, floor), validated on load.
- `METHODOLOGY.md` version 0: the pricing maths, conventions, assumptions, limitations.
- Day 3 learning-track page, notebook section (3.1-3.6 and "My solutions"), exercises.

### Changed
- Data dictionary: contract cash flows and back-test tables.

### Found
- Monthly revenue spread within a year measures seasonality, not risk (a PaP PPA looked
  riskier than merchant); replaced by the surprise against plan.

## [0.2.0] - 2026-10-08 (Day 2, ticket PPA-2)

### Added
- Capture prices and capture rates (`ppa_lab.analysis.capture`): the legal quarter-hour
  formula, hourly prices mapped onto the 15-minute generation grid without filling gaps,
  monthly and annual tables per technology with energy and share at negative prices.
- Official monthly market values 2023-01 to 2026-08 (`data/reference/`) and a monthly
  comparison; 15 new reconciliation references (annual market values 2023-2025 for solar,
  wind onshore and offshore; 2023/2024 spot; Vermarktungsmenge).
- `Reference.note` and the status "explained difference": a documented cause for a
  difference beyond tolerance (known-breaks register).
- Day 2 report (`ppa-lab capture`, `make capture`, part of `make all`) with three charts.
- Day 2 exercises with automatic checks; learning-track page and PDF.
- `notebooks/ppa_lab_playground.ipynb`: living playground notebook (Day 1 and Day 2
  sections, play cells, open ideas, and a "My solutions" block per day that imports the
  exercise files, runs their checks and extends the results); `make notebook`,
  `make notebook-run`; optional dependency group `notebook`.
- `docs/data_dictionary.md`: every dataset, column, unit and sign convention.
- ENTSO-E Transparency Platform client (`ppa_lab.data.entsoe`): token from `.env` (never
  printed or included in errors), curve type A03 forward-fill, selection of the auction
  sequence (default 1 = SDAC).
- `scripts/check_entsoe_token.py`: verifies the token and reconciles ENTSO-E with
  Energy-Charts. Result: identical prices to the cent on 1 Jun 2025 (24 hourly) and
  1 Oct 2025 (96 quarter-hourly).
- Real ENTSO-E response saved as a test fixture (contains no token).

### Changed
- Chart style moved to `ppa_lab.analysis.plotting`, shared by both reports.
- The Day 1 report only shows the references it computes and lists documented causes.

### Found
- 2024 spot difference (−0.95 EUR/MWh) is the SDAC partial decoupling of 26 June 2024.
- Wind capture prices are systematically above the official values (open, PPA-2b).

### Fixed
- Day 2 report crashed on real data (`Period` with an f-string date format); covered
  by a new test.
- ENTSO-E returns two day-ahead series for DE-LU (`classificationSequence` 1 and 2);
  merging them doubled the rows. The client now keeps sequence 1 by default.

## [0.1.0] - 2026-10-07 (Day 1, ticket PPA-1)

### Added
- Project skeleton: `src/` layout, `pyproject.toml`, Makefile, CI workflow, MIT licence.
- `config/project.toml` with market, date range, SDAC price limits (floor -500 to
  -600 EUR/MWh from delivery day 29 May 2026) and reconciliation references.
- Energy-Charts API client with timeouts, exponential back-off and `Retry-After`
  handling for HTTP 429; pure parsers for prices and generation.
- Raw monthly Parquet cache with manifests (parameters, checksum, licence, completeness).
- Processed datasets: native-resolution prices, hourly prices, 15-minute and hourly generation.
- DST-aware data-quality checks, including a night-time solar check that catches time-zone bugs.
- Annual statistics, reconciliation against published figures, Day 1 report with four charts.
- 52 offline tests using real API fixtures (94% coverage); one opt-in live contract test.
- `make docs`: learning-track pages rendered to PDF with headless Chrome.

### Fixed during development
- pandas 3 infers datetime units: interval lengths are now computed from time
  differences, and all indexes are normalised to nanoseconds.
- The API returns HTTP 429 with `Retry-After`; the client now waits as instructed.
