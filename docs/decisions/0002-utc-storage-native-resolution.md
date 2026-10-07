# ADR 0002: Store timestamps in UTC at native resolution

- **Status:** accepted
- **Date:** 2026-10-07
- **Ticket:** PPA-1

## Context

- Power is delivered in local time (Europe/Berlin), which has a 23-hour day in
  March and a 25-hour day in October.
- The day-ahead market switched from hourly to 15-minute products on
  1 October 2025, so one price series contains two resolutions.
- pandas 3 infers a datetime unit (s/ms/us/ns) from the input, and Parquet cannot
  store second-precision timestamps.

## Decision

1. Every stored timestamp is UTC, marks the start of its delivery interval, and
   uses one fixed unit (nanoseconds, `timeutils.TIME_UNIT`).
2. Data is stored at the source's native resolution; hourly views are derived
   (`to_hourly`), never stored instead of the original.
3. Conversion to Europe/Berlin happens only for grouping (delivery day, month,
   year) and for display.

## Consequences

- No ambiguous or missing timestamps around daylight-saving changes.
- Completeness checks must be DST-aware (`expected_intervals`).
- Any statistic over mixed resolutions must be time-weighted
  (`interval_minutes`), not a simple mean of rows.
