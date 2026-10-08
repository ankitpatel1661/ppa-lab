# Backlog

Tickets follow the 14-day sprint in the Encavis preparation guide (Section 4.2).
Each ticket has acceptance criteria (AC): it is done only when all AC are met,
tests pass and the learning-track page for that day is written.

| Ticket | Day | Title | Status |
|---|---|---|---|
| PPA-1 | 1 | Market-data foundation: repo, API client, raw cache, DQ checks, reconciliation | **Done** |
| PPA-2 | 2 | Capture prices and capture rates for German solar and wind | **Done** |
| PPA-2b | later | Test the wind curtailment hypothesis with the TSOs' online extrapolation | To do |
| PPA-3 | 3 | PPA pricing maths written up (pay-as-produced, baseload, CfD, floors) | To do |
| PPA-4 | 4 | Weather-to-power: ERA5/Open-Meteo, pvlib solar park, windpowerlib wind park | To do |
| PPA-5 | 5 | Stochastic spot-price model (seasonality + mean reversion), calibrated | To do |
| PPA-6 | 6 | Joint Monte Carlo: weather years x price paths with preserved correlation | To do |
| PPA-7 | 7 | Price a pay-as-produced PPA with profile and volume risk premia, CFaR | To do |
| PPA-8 | 8 | Hedge with baseload futures; minimum-variance hedge ratio; scenario P&L | To do |
| PPA-9 | 9 | Streamlit page, management memo, CI badge, public MVP | To do |

## PPA-2: Capture prices and capture rates (Day 2)

**Story:** As a pricing analyst I want monthly and annual capture prices for German
solar and wind, so I can see how much of the baseload price each technology earns.

**Acceptance criteria**
- [x] Function `capture_price(prices, generation)` = volume-weighted price, with tests
      (flat profile gives capture rate 1; generation only in negative hours gives a negative capture price).
- [x] Monthly and annual capture prices and capture rates for solar, wind onshore, wind offshore, 2023 to 2026.
- [x] Reconcile the 2025 annual solar capture price with the official
      "Jahresmarktwert Solar" 4.508 ct/kWh (netztransparenz.de) and explain any difference.
      Result: 4.595 ct/kWh, inside the ±0.10 tolerance; the gap grows with negative-price
      curtailment (learning track Day 2, section 4.3).
- [x] Chart: capture rate by month and technology; short written interpretation.
- [x] Learning-track page `docs/learning_track/day02_capture_prices.md`.

## PPA-2b: Wind capture prices vs official market values (open investigation)

**Finding (8 Oct 2026):** our wind capture prices are above the official
Jahresmarktwerte in every year (onshore +0.16 to +0.29, offshore +0.36 to +0.49 ct/kWh)
and in 43 of 44 months. Spot prices match, so the volumes differ.

**Hypothesis:** Energy-Charts generation is measured feed-in after curtailment
(redispatch and negative prices); the official values use the TSOs' online
extrapolation, which keeps more energy in cheap hours.

**Acceptance criteria**
- [ ] Download the TSOs' online extrapolation (netztransparenz.de API, free registration)
      for wind onshore and offshore, at least 3 months including April 2026.
- [ ] Recompute the monthly capture prices with it and compare with the official values.
- [ ] If the gap vanishes: add a `note` to the wind references; otherwise record the
      next hypothesis.

## Open questions

- **ENTSO-E auction sequence 2 for DE-LU:** a second day-ahead series with different prices
  (1 Oct 2025: daily mean 146.40 vs 116.57 EUR/MWh for the SDAC auction). EXAA is a
  candidate but unconfirmed; check against EXAA published results before using it.

## Later ideas (not scheduled)

- Secret scanning in CI (e.g. gitleaks) after the `.env.example` near-miss on 8 Oct 2026.
- ENTSO-E cross-check over the full 2023-2026 range as a report (client and one-day check done).
- DuckDB views over the processed Parquet files (Day 13 in the guide).
- Pre-commit hooks (ruff) once the repository is on GitHub.
