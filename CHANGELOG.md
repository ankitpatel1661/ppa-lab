# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
