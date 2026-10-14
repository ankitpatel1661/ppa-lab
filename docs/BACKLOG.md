# Backlog

The project is built in steps, one ticket per step. Each ticket has acceptance criteria
(AC): it is done only when all AC are met, tests pass and the learning-track page for
that step is written.

| Ticket | Step | Title | Status |
|---|---|---|---|
| PPA-1 | 1 | Market-data foundation: repo, API client, raw cache, DQ checks, reconciliation | **Done** |
| PPA-2 | 2 | Capture prices and capture rates for German solar and wind | **Done** |
| PPA-2b | later | Test the wind curtailment hypothesis with the TSOs' online extrapolation | To do |
| PPA-3 | 3 | PPA pricing maths written up (pay-as-produced, baseload, CfD, floors) | **Done** |
| PPA-4 | 4 | Weather-to-power: ERA5/Open-Meteo, pvlib solar park, windpowerlib wind park | **Done** |
| PPA-5 | 5 | Stochastic spot-price model (seasonality + mean reversion), calibrated | **Done** |
| PPA-6 | 6 | Joint Monte Carlo: weather years x price paths with preserved correlation | **Done** |
| PPA-7 | 7 | Price a pay-as-produced PPA with profile and volume risk premia, CFaR | To do |
| PPA-8 | 8 | Hedge with baseload futures; minimum-variance hedge ratio; scenario P&L | To do |
| PPA-9 | 9 | Streamlit page, management memo, CI badge, public MVP | To do |

## PPA-2: Capture prices and capture rates (Step 2)

**Story:** As a pricing analyst I want monthly and annual capture prices for German
solar and wind, so I can see how much of the baseload price each technology earns.

**Acceptance criteria**
- [x] Function `capture_price(prices, generation)` = volume-weighted price, with tests
      (flat profile gives capture rate 1; generation only in negative hours gives a negative capture price).
- [x] Monthly and annual capture prices and capture rates for solar, wind onshore, wind offshore, 2023 to 2026.
- [x] Reconcile the 2025 annual solar capture price with the official
      "Jahresmarktwert Solar" 4.508 ct/kWh (netztransparenz.de) and explain any difference.
      Result: 4.595 ct/kWh, inside the ±0.10 tolerance; the gap grows with negative-price
      curtailment (learning track Step 2, section 4.3).
- [x] Chart: capture rate by month and technology; short written interpretation.
- [x] Learning-track page `docs/learning_track/step02_capture_prices.md`.

## PPA-3: PPA structures and pricing maths (Step 3)

**Story:** As a pricing analyst I want the cash flows and fair prices of the standard PPA
structures in one tested library, so that every later price and risk number is built
from the same, documented building blocks.

**Acceptance criteria**
- [x] Cash flows per interval (producer view) for merchant, pay-as-produced (with a
      negative-price clause option), virtual PPA (CfD), floor / cap / collar, baseload.
- [x] Fair prices as ratios of expectations, with discounting; NumPy scenarios supported.
- [x] Invariant tests: floor never lowers value; CfD removes price risk; baseload =
      merchant + swap; break-even strike = capture price.
- [x] `METHODOLOGY.md` v0.
- [x] Back-test 2024-2025 (50 MW solar, 30 MW wind) with prior-year strikes, plan and surprise.
- [x] Learning-track page, notebook section, exercises.

## PPA-4: Weather to power (Step 4)

**Story:** As a pricing analyst I want hourly generation of our own parks over many weather
years, so that volume risk (P50/P90) and the site's shape can enter the PPA price.

**Acceptance criteria**
- [x] ERA5 weather for two real sites, 1995 to date, cached with provenance (grid point, licence).
- [x] Timestamp convention handled and verified against the sun's position (test + build check).
- [x] pvlib solar park (50 MWp) and windpowerlib wind park (30 MW) from configuration.
- [x] Annual energy per weather year, P50 / P90 (1 and 10 years), trend.
- [x] Checks against national generation: hourly correlation, monthly shares, capture rate.
- [x] Report, learning-track page, notebook section, exercises.

## PPA-5: Stochastic price model (Step 5)

**Story:** As a pricing analyst I want many plausible hourly price years that agree with the
forward price and behave like real prices, so that PPA values come with a distribution and
not just one historical outcome.

**Acceptance criteria**
- [x] Local calendar: hour, season, day type with the nine nationwide holidays (tested).
- [x] Model in arcsinh space: monthly levels, daily shape, daily AR(1) factor, intraday
      patterns resampled as whole days; saved as `price_model.json`.
- [x] Parameter recovery on synthetic prices with known parameters (including Kendall's bias).
- [x] Level calibrated to a forward price (exact with common random numbers); level volatility.
- [x] Validation against history: distribution, negative hours, autocorrelation; gaps
      documented (7 of 11 statistics inside the 5-95% range).
- [x] Report, learning-track page, notebook section, exercises.

## PPA-6: Joint weather and price scenarios (Step 6)

**Story:** As a pricing analyst I want volumes and prices simulated from the same weather, so
that the negative correlation between renewable output and price is in every PPA number.

**Acceptance criteria**
- [x] Daily weather features per site; generation as day x hour matrices; calendar mapping.
- [x] Weather-price link: daily level responds to weather anomalies; hourly patterns from
      analog days. Parameter recovery on synthetic data.
- [x] 31 weather years x 16 price paths for 2027, one level for all; independent variant.
- [x] Checks: correlation wind vs price as in history (−0.60 vs −0.58); 2025 capture rates
      inside the simulated ranges; Monte Carlo standard error (±0.8 EUR/MWh).
- [x] Report, per-scenario results for Step 7, learning-track page, notebook section, exercises.

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

- Scenarios v2: recency-weighted analog pool or a fundamental view of 2027 solar capacity;
  national and neighbour-country weather; curtailment at negative prices; wind 2024 gap.
- Price model v2: a soft floor just below zero for negative prices; block bootstrap or a
  weather link for multi-day patterns; out-of-sample and rolling-window validation; a
  monthly forward curve instead of one annual level.
- Secret scanning in CI (e.g. gitleaks) after the `.env.example` near-miss on 8 Oct 2026.
- Step 3 back-test re-run with the Step 4 site profiles instead of scaled national profiles.
- Grid curtailment (redispatch) and availability in the wind model; air-density correction.
- ENTSO-E cross-check over the full 2023-2026 range as a report (client and one-day check done).
- DuckDB views over the processed Parquet files (Step 13 in the guide).
- Pre-commit hooks (ruff) once the repository is on GitHub.
