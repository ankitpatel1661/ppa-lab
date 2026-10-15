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
| PPA-7 | 7 | Price a pay-as-produced PPA with profile and volume risk premia, CFaR | **Done** |
| PPA-8 | 8 | Hedge with baseload futures; minimum-variance hedge ratio; scenario P&L | **Done** |
| PPA-8b | 8b | Anchor the price level to the market forward curve | **Done** (v1.1) |
| PPA-8c | 8c | Quarterly forward curve (market winter premium); solar cannibalisation trend | **Done** (v1.2) |
| PPA-8d | later | Capture rate vs price level on 2021-2022 (gas crisis) data | To do |
| PPA-4b | 4b | Model two Encavis parks from public data: Borrentin solar (114 MWp), Everswinkel wind (28.5 MW) | **Done** (v1.3) |
| PPA-9 | 9 | Streamlit page, management memo, CI badge, public MVP | **Done** |

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

## PPA-7: Pricing and risk (Step 7)

**Story:** As a pricing analyst I want a defensible PPA price with its risk premium and the
risk we keep, so that origination can make an offer and Risk can approve it.

**Acceptance criteria**
- [x] All structures on the joint scenarios: fair price, expected and P5 revenue, CFaR95.
- [x] Buyer's premium after a baseload hedge, split into profile and volume; unhedged for comparison.
- [x] Price stack from the forward to an indicative price with stated cost assumptions.
- [x] Ten-year price with discounting, degradation and sensitivities (trend, forward, pool).
- [x] Analog-pool decision in the configuration; results in `ppa_pricing.json` for Step 9.
- [x] Report, learning-track page, notebook section, exercises.

## PPA-9: Memo, dashboard, public MVP (Step 9)

**Story:** As a manager or reviewer I want the answer on one page and the chance to change
the assumptions myself, without running the pipeline.

**Acceptance criteria**
- [x] One-page memo generated from the Step 7 results (Markdown and PDF).
- [x] Dashboard with the answer, the price stack, risk by structure and adjustable
      assumptions; logic tested without Streamlit; app smoke test.
- [x] Runs from committed results only (Streamlit Community Cloud ready).
- [x] README as a front page with the answer and a CI badge.
- [x] Learning-track page, notebook section, exercises.

Done before PPA-8 on purpose: the public MVP had to be complete before the application date.

## PPA-8: Hedging with futures (Step 8)

**Story:** As treasury I want to know how much of the unsold output to sell forward, in
which product, and whether our model's forward matches the market.

**Acceptance criteria**
- [x] German futures products on the delivery calendar: Cal base and peak, quarters, months.
- [x] Hedge payoffs and minimum-variance hedges for one or several products.
- [x] Strategies for both parks' merchant output (none, 50%, 100%, minimum-variance with Cal
      base, quarters, months) with CFaR and variance removed.
- [x] The PPA buyer's minimum-variance band against Step 7's full band.
- [x] Back-test on 2024-2025 and a market check against published quotes.
- [x] Report, `hedging.json` for the memo and the dashboard, learning page, notebook, exercises.

## PPA-8b: Anchor the price level to the market forward (done in v1.1)

**Finding (Step 8):** published Cal-27 base quotes are 104.24 EUR/MWh (31 Jul 2026, tacto.ai)
and 113.45 (28 Aug 2026, power2market), peak 119.48; the model uses the assumed 85 EUR/MWh.
At 113.45 the indicative prices would be 46.8 (solar) and 93.0 (wind) instead of 33.3 and 68.4.

**Acceptance criteria**
- [x] Decide the level: the market curve (decided 15 Oct 2026). By then Cal-27 base had risen
      to 140.21 EUR/MWh (9 Oct, tacto.ai); Cal-28 104.75 (9 Oct); Cal-29 87.58 (14 Sep,
      power2market), held flat after 2029.
- [x] `[price_model] forward_eur_mwh`, `forward_date`, `forward_source`, `[ppa.forward_curve]`;
      re-run `make prices scenarios pricing hedging memo`; README, memo, learning pages updated.
- [x] Check the capture rate's dependence on the level (arcsinh lift); sensitivity added.

## PPA-8c: Quarterly forward curve and the capture rate vs the level

**Finding (v1.1):** the market prices a steeper winter than the model (Q1-27 179.47 vs
Q2-27 114.04 EUR/MWh on 14 Sep 2026; model 141.4 vs 124.3), and the model's solar capture rate
rises with the level (0.48 at 85, 0.63 at 141), which history supports only for one step
(2025 to 2026).

**Acceptance criteria**
- [x] Calibrate quarterly levels to market quarter forwards (v1.2: Q1-Q4/27 of 14 Sep 2026,
      scaled to the Cal forward).
- [x] Solar capture-rate trend in the base case (v1.2: −1 pp a year).
- [ ] Test the capture rate vs level on more history (2021-2022 gas crisis) and decide
      between the arcsinh lift and the shape-factor view (moved to PPA-8d).

## PPA-4b: Two Encavis parks instead of illustrative ones (v1.3)

**Story:** As an applicant to Encavis I want the engine to price parks Encavis actually owns,
so that the results speak to its portfolio.

**Acceptance criteria**
- [x] Ownership confirmed from Encavis press releases: Borrentin solar park (114 MW, grid
      since December 2024, about 121 GWh a year, 10-year PPA with Allego) and Everswinkel wind
      park (28.5 MW: 4 Nordex N149 + 1 N163, acquired December 2024, about 64 GWh a year, EEG).
- [x] Sites, capacities and published yields in the configuration; layout details that are
      not published (tilt, DC/AC ratio, hub height, turbine curve stand-in) stated as assumptions.
- [x] ERA5 weather for both sites, Steps 3-9 re-run; site models checked against the
      published yields.
- [x] Framing: public data only; results are illustrative and say nothing about the parks'
      actual contracts.

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
- Hedging v2: no negative sales and position limits (`scipy.optimize.nnls`), transaction
  costs, a back-test with EEX settlement history, multi-year hedges.
- Secret scanning in CI (e.g. gitleaks) after the `.env.example` near-miss on 8 Oct 2026.
- Step 3 back-test re-run with the Step 4 site profiles instead of scaled national profiles.
- Grid curtailment (redispatch) and availability in the wind model; air-density correction.
- ENTSO-E cross-check over the full 2023-2026 range as a report (client and one-day check done).
- DuckDB views over the processed Parquet files (Step 13 in the guide).
- Pre-commit hooks (ruff) once the repository is on GitHub.
