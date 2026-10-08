# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- ENTSO-E Transparency Platform client (`ppa_lab.data.entsoe`): token from `.env` (never
  printed or included in errors), curve type A03 forward-fill, selection of the auction
  sequence (default 1 = SDAC).
- `scripts/check_entsoe_token.py`: verifies the token and reconciles ENTSO-E with
  Energy-Charts. Result: identical prices to the cent on 1 Jun 2025 (24 hourly) and
  1 Oct 2025 (96 quarter-hourly).
- Real ENTSO-E response saved as a test fixture (contains no token).

### Fixed
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
