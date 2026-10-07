# ADR 0003: Immutable raw layer + processed layer in Parquet

- **Status:** accepted
- **Date:** 2026-10-07
- **Ticket:** PPA-1

## Context

Pricing results must be reproducible and auditable: if a board memo quotes a
capture rate, we must be able to show which data produced it.

## Decision

- **Raw layer** (`data/raw/<source>/<dataset>/<YYYY-MM>.parquet`): exactly what
  the API returned, one file per month, never edited. Each file has a
  `.meta.json` manifest with request parameters, download time, row count,
  SHA-256 checksum, licence and a `complete` flag (months that were still running
  when downloaded are fetched again).
- **Processed layer** (`data/processed/*.parquet`): cleaned, de-duplicated,
  restricted to the configured range, enriched with interval length and hourly views.
- Format: Parquet (typed, compressed, fast). A SQL layer (DuckDB) follows on Day 13.

## Consequences

- Re-running the pipeline is cheap and does not hit the API again.
- Corrections are made in code (processed layer), so the evidence stays intact.
- Data files are git-ignored; they can be rebuilt with `make data build`.
