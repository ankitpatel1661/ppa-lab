# Backlog

Tickets follow the 14-day sprint in the Encavis preparation guide (Section 4.2).
Each ticket has acceptance criteria (AC): it is done only when all AC are met,
tests pass and the learning-track page for that day is written.

| Ticket | Day | Title | Status |
|---|---|---|---|
| PPA-1 | 1 | Market-data foundation: repo, API client, raw cache, DQ checks, reconciliation | **Done** |
| PPA-2 | 2 | Capture prices and capture rates for German solar and wind | To do |
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
- [ ] Function `capture_price(prices, generation)` = volume-weighted price, with tests
      (flat profile gives capture rate 1; generation only in negative hours gives a negative capture price).
- [ ] Monthly and annual capture prices and capture rates for solar, wind onshore, wind offshore, 2023 to 2026.
- [ ] Reconcile the 2025 annual solar capture price with the official
      "Jahresmarktwert Solar" 4.508 ct/kWh (netztransparenz.de) and explain any difference.
- [ ] Chart: capture rate by month and technology; short written interpretation.
- [ ] Learning-track page `docs/learning_track/day02_*.md`.

## Later ideas (not scheduled)

- ENTSO-E client as a second price source; automatic cross-check report.
- DuckDB views over the processed Parquet files (Day 13 in the guide).
- Pre-commit hooks (ruff) once the repository is on GitHub.
