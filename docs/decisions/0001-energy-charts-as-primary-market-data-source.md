# ADR 0001: Energy-Charts as the primary market-data source

- **Status:** accepted
- **Date:** 2026-10-07
- **Ticket:** PPA-1

## Context

The pricing engine needs German day-ahead prices and generation by technology,
at the native market resolution, for several years. Candidate sources:

| Source | Content | Access | Notes |
|---|---|---|---|
| EPEX SPOT | Official auction results | Paid licence | The "golden source" in a company |
| ENTSO-E Transparency Platform | Prices, load, generation for all of Europe | Free, needs a security token | XML API; token takes days to get |
| SMARD.de (Bundesnetzagentur) | German prices and generation | Free downloads | The upstream source of Energy-Charts prices |
| Energy-Charts API (Fraunhofer ISE) | Prices (from SMARD) and generation, JSON | Free, no key, CC BY 4.0 | Rate limited (HTTP 429 with `Retry-After`) |

## Decision

Use the Energy-Charts API as the primary source for the learning project, and
add ENTSO-E later (Day 4+) as an independent second source to cross-check prices.

## Consequences

- We can start today: no key, simple JSON, licence allows public reuse with attribution.
- We depend on a free service with a rate limit. Mitigation: a monthly raw cache,
  polite pacing, retries that honour `Retry-After`.
- Every report must attribute the data: "CC BY 4.0, Bundesnetzagentur | SMARD.de,
  via Energy-Charts (Fraunhofer ISE)".
- In a company, the same interfaces would read from licensed EPEX/EEX feeds; the
  rest of the code would not change. That is why the client sits behind its own module.
