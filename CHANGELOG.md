# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.10.0] (tickets PPA-2b and PPA-6c: the TSOs' own data)

### Added
- `data/netztransparenz.py` and `ppa-lab tso`: the TSOs' WebAPI (OAuth 2.0 client credentials,
  endpoints from its public OpenAPI description): reBAP and the online extrapolation of onshore
  wind, offshore wind and solar, 2021-2026. The forecast endpoints (`prognose`) are "N.A."
  throughout and `hochrechnung` covers only the TSO-marketed EEG volumes: not used.
- ENTSO-E day-ahead wind and solar forecasts for DE-LU (A69) and `ppa-lab forecasts`.
- `analysis/balancing.py`, `ppa-lab balancing`: Step 2b report and `balancing.json`.

### Changed
- `[ppa.parks.*] balancing_eur_mwh`: measured imbalance cost of the national portfolio over
  Oct 2025 - Sep 2026 plus a 0.5 EUR/MWh marketing fee: solar 2.18 (was 1.5), wind 1.55
  (was 2.0, the preparation guide's illustrative values).
- The wind reconciliation references and the onshore shares at non-negative prices carry their
  explanation: Step 2 has no reference outside tolerance any more.

### Findings
- PPA-2b: with the TSOs' online extrapolation our prices reproduce the official annual market
  values of onshore wind, offshore wind and solar for 2021-2025 to 0.00 EUR/MWh, except 2024
  (June 2024 only, the day-ahead decoupling). The extrapolation counts 7-9% more onshore energy
  than the measured feed-in, mostly curtailed output in cheap hours.
- Imbalance cost of the national portfolio (day-ahead forecast errors at reBAP): onshore
  1.0-3.5, solar 1.4-5.5 EUR/MWh in 2021-2026, following the reBAP spread (mean 193 EUR/MWh in
  2022, 49 in 2026) more than the forecast error (onshore about 9%, solar about 7%).
- Borrentin: indicative 27.4 EUR/MWh (28.1); with the clause 52.2 per delivered MWh (36.3 per
  MWh of output). Everswinkel: PPA 78.6 (78.1), EEG 93.8 (93.4).

## [1.9.0] (ticket PPA-7c: Everswinkel's EEG premium as a strip of puts)

### Added
- `pricing/eeg.py`: the EEG market premium max(AW − MW, 0) per MWh as a strip of monthly (or
  annual) puts on the technology's market value, paid on the output delivered at prices >= 0;
  MW proxied by the park's own capture price times the historical ratio of the official
  value to it (`basis_ratio`: 0.968, 44 months from 2023, sd 0.042).
- `[eeg]` configuration: Everswinkel's award value is not published; 77 EUR/MWh assumed (a
  2022 tender at 5.76-5.87 ct/kWh times a site factor of about 1.3), range 60-95.
- Step 7 section 6: per year and over the tenor, merchant revenue plus premium against the PPA;
  revenue risk at the 2027 and the lowest quoted forward; by award value and with the annual
  market value. The level grid stores the premium and risk per level.
- Dashboard: an EEG note for the wind park.

### Findings
- The put is worth 0.49 EUR/MWh at the 2027 forward, 4.11 at 2028's and 8.88 at the Cal-29
  level: 7.23 over ten years. Under the EEG the park earns 93.4 EUR/MWh after the marketing fee
  against 78.1 for a PPA at the indicative price (86.6 fair); the EEG pays more for every award
  value from 60 (88.4) to 95 (102.4). An annual market value would be worth 5.14 instead of 7.23.
- At the Cal-29 level the EEG's 5% quantile (73.4 EUR/MWh) beats the PPA's (69.4): the put
  floors the price and the EEG keeps the upside; its CFaR95 is 0.99 m against the PPA's 0.58 m.

## [1.8.0] (ticket PPA-7b: curtailment at negative prices)

### Changed
- A park that sells at spot, or is not paid at negative prices, stops producing below
  `[ppa] curtail_below_eur_mwh` (0): its output is q 1[P >= 0] (`curtail`,
  `curtailment_value` in `pricing/risk.py`). Under a plain pay-as-produced PPA it is paid for
  every MWh and keeps producing.
- Step 7 structures, each at its own fair strike: merchant curtailing (and, for comparison,
  producing), plain pay-as-produced, the negative-price clause (curtailed, unpaid; strike
  E[sum q^c P] / E[sum q^c], until v1.8 the plain strike), deemed output (the buyer curtails
  and pays the output as if produced), baseload. The merchant + floor at 0 is gone: a park
  that curtails owns that floor for free. New column: share of the output sold or paid.
- The clause is priced over the tenor (premium, stack, tenor price) on the delivered output,
  along its capture rate and delivered share at each year's forward (`volume_response` in
  `tenor_price`; the level grid stores both).
- New Step 7 section 5 with the 2027 numbers, the three ways to share the value, and the
  parks' output at negative prices in 2021-2026.
- Step 8 hedges the output a merchant park sells (curtailing). Memo: the give-away against
  spot includes the value of curtailing; recommendation 2 prices the clause. Dashboard:
  "Negative prices" switch (plain PPA or clause, per delivered MWh); readable structure names.
- Notebook 7.2b: play with the curtailment threshold.

### Findings
- 2027: 17.5% of the solar output (wind 4.4%) falls in hours with negative prices, at an
  average of −17.7 EUR/MWh; curtailing saves 3.1 EUR/MWh of output (wind 0.7). In history the
  solar park's share rose from 1.6% (2022) to 23.6% (2025), worth 4.9 EUR/MWh in 2026.
- Clause: 2027 fair price 97.8 per delivered MWh; buyer's premium 14.6 (plain 10.5); ten-year
  indicative 52.9 per delivered MWh, 36.8 per MWh of output (69.5% delivered) against 28.1 for
  the plain PPA; producer's CFaR95 EUR 1.29 m (plain 0.70 m). Deemed output: 80.6 in 2027.
- Merchant CFaR95 (curtailing): solar EUR 3.02 m (3.24 m producing). Step 8: Cal base for
  87% of the output sold cuts it by 72%.

## [1.7.0] (ticket PPA-8e: capture rates that follow the build-out)

### Changed
- Historical days are moved forward by the build-out trend before their intraday pattern is
  used (`[price_model] intraday_trend = true`; `estimate_intraday_trend` and `pattern_shift`
  in `prices/model.py`): u -> u + tau[season, hour] x (simulated day - historical day), with
  tau the change per year of the hourly shape, estimated from the same calendar month in
  different years. Used by the Step 5 and Step 6 simulations; `price_model.json` stores the
  trend and the pool days.
- Step 6 out-of-sample section compares with the model without the trend; the error Step 7
  carries is the mean of the test years fitted like the delivery year (2025-2026).
- Step 7 states what history's trend would do in one more year (solar −5.6 pp at the same
  forward) next to the base case's −1 pp a year after 2027.
- Memo: levers below 0.5 EUR/MWh are left out (the analog-pool lever is now 0.0).
- Notebook 6.7: `TREND` switch.

### Findings
- Out of sample the solar capture-rate error falls from +0.133 / +0.093 to +0.047 / +0.010
  (2025 / 2026); 7 and 5 of 11 statistics inside (4 and 4); negative hours 5.8% vs 6.6% and
  6.3% vs 7.2% (4.5%). Wind's error grows from +0.023 / +0.051 to +0.029 / +0.060: deeper
  midday dips raise the other hours. 2024 (fitted on one year) has no trend.
- In-sample 7 of 11 (Step 5) and 8 of 11 (Step 6) statistics inside; the solar park's 2024
  capture rate is now inside the range (0.614 vs 0.601).
- Which historical days represent 2027 no longer matters: solar fair price 77.5 / 77.2 / 77.5
  for pools from 2024, 2025 and the last 12 months (93.8 / 89.4 / 86.4 in v1.6).
- Borrentin: 2027 capture rate 0.55 (0.61), fair 41.1 EUR/MWh (48.6), indicative **28.1**
  (36.8); 25.3 less the remaining out-of-sample error. Everswinkel: 86.6 / **78.1** (86.0 /
  77.5). Solar output at negative prices in 2027: 17.5%.

## [1.6.0] (ticket PPA-6b: years the model never saw, and the negative tail)

### Added
- Out-of-sample test (`scenarios/out_of_sample.py`, Step 6 report section 4, chart
  `step06_out_of_sample.png`, `data/processed/out_of_sample.json`): for 2024, 2025 and 2026
  the model and the weather link are fitted on the days from 2023 up to the year only, with
  analog days from its last 12 months, then the year is simulated with its real weather and
  each quarter at its realised average price (a perfect forward). A second run lets the model
  see the year, which leaves only its structural error. `[scenarios] out_of_sample_*`.
- Negative prices with their own scale b in the transform (`negative_scale` in
  `prices/model.py`, `[price_model] negative_scale_eur_mwh = 15`): y = −a arcsinh(|P| / b),
  with a so that −500 EUR/MWh maps where it did; simulated prices below −500 are clipped.
  b chosen in the Step 6 report, section 3, among s, 40, 15 and 5: the smallest largest error
  over the 1% quantile, the share of negative hours and the solar output at negative prices.
- Step 7 sensitivity "Capture rate less the model's out-of-sample error"; memo lever.
- Notebook 6.7: play with a year the model never saw; 5.6 plays with s and b.

### Findings
- History's negative hours bunch just below zero (65% between −5 and 0 EUR/MWh). With b = 15
  the in-sample tail matches: 1% quantile −21.2 vs −20.1 (was −45.2), negative hours 6.6% vs
  6.2% (5.6%), solar output at negative prices 21.7% vs 21.8% (18.0%); 7 of 11 statistics
  inside the range (6).
- Out of sample the model overstates capture rates even with the price level given: solar
  +0.142, +0.133, +0.093 in 2024-2026, wind +0.023 to +0.051. Having seen the year it is
  +0.036 and +0.022: most of the solar error is one year of build-out (dips deepening), which
  the analog days and the daily shape learn late.
- The realistic tail raises the solar price: the old deep tail had been hiding midday dips
  that are not deep enough. Borrentin: fair 48.6 EUR/MWh (45.7 in v1.5), indicative **36.8**
  (34.9); **24.9** less the out-of-sample error. Everswinkel: 86.0 / **77.5** (85.8 / 77.3);
  74.3 less the error. 2027: solar output at negative prices 13.8% (was 10%).
- The model's slope of capture rate vs ln(price) is now 0.19 (0.25), still inside history's
  95% interval (0.10 to 0.45).

## [1.5.0] (ticket PPA-8d: the capture rate and the price level)

### Changed
- Each later contract year's capture rate moves with that year's forward along the price
  model's own response to the level (`tenor_price(level_response=...)`, `level_shift` in
  `pricing/risk.py`). Before, the 2027 capture rate (at a forward of 141) was held for years
  priced at 88. The response is measured by rebuilding the 2027 scenarios at twelve forwards
  with the same draws (about 50 s more in `ppa-lab pricing`) and published per park in the
  results, so the dashboard's forward knob and Step 8's market check move the capture rate
  too.
- The forward sensitivities (±10%) move the capture rate with the level, so they are no
  longer symmetric.
- The Step 7 sensitivity "Capture rate of the recent price level" (the shape-factor view) is
  replaced by history's 95% range for the slope, from the recent level.
- New Step 7 section 5 and chart `step07_level_effect.png`: history's regression against the
  model's slope; `[ppa] level_effect_start_year = 2023`.
- Memo: "later years: lower forwards and capture rates"; the level lever shows history's
  range; the forward lever shows both directions.

### Added
- `analysis/level_effect.py`: monthly panel (base price, capture rate and share of load per
  technology), OLS with month effects and HC1 standard errors, build-out pace.

### Findings
- Solar's capture rate rises with the price level: slope 0.27 per unit of ln(price) on
  2023-2026 (95% 0.10 to 0.45, t = 3.1, 45 months); the model's 0.25 lies inside and the
  shape-factor view (0) is rejected. On 2021-2026 the slope is 0.10: at a 9-11% solar share
  in 2021-2022, hours near zero were rare. Wind: 0.02 (−0.09 to 0.14), model 0.07.
- Borrentin: 10-year fair price 45.7 EUR/MWh (55.5 in v1.4), indicative **34.9** (44.7).
  Everswinkel: fair 85.8 (88.5), indicative 77.3 (80.0).
- History's build-out coefficient (−2.9 per unit of share of load) at the 2022-2025 pace
  means about −3.7 pp of solar capture rate a year at a fixed level, steeper than the −1 pp
  base-case trend (new backlog item PPA-8e).

## [1.4.0] (ticket PPA-1b: history from 2021, the 2022 gas crisis)

### Changed
- Market data from 1 Jan 2021 (`[market] start`): 24 more months of day-ahead prices and
  generation from Energy-Charts; 2,099 complete delivery days.
- Price limits per period: +3000 EUR/MWh until 10 May 2022, +4000 from delivery day
  11 May 2022 (SDAC HMMCP increase), −500 until 28 May 2026.
- Reconciliation for 2021-2022 (netztransparenz.de Jahresmarktwerte, EPEX and Energy
  Brainpool negative hours) and 24 more official monthly market values in
  `data/reference/`.
- Tests that assumed the first data year was 2023 now use the configured start year.

### Findings
- Mean prices 96.85 (2021) and 235.45 EUR/MWh (2022) and negative hours (139, 69) match the
  published values exactly; the spot price matches in 67 of 68 months.
- In the 2022 crisis solar's capture rate rose to 0.94 (2021: 0.79) while wind's fell to
  0.71: the history needed to test how capture rates move with the price level (PPA-8d).
- Solar 2022 differs from the official value by −0.21 ct/kWh although every month matches:
  a monthly weighting effect (explained difference). The wind gap (PPA-2b) is there in
  every year, largest in 2022.
- Pricing results (Steps 5-9) are unchanged: the price model is calibrated on 2024-2026.

## [1.3.0] (ticket PPA-4b: two Encavis parks)

### Changed
- The parks are two Encavis parks, modelled from public data (Encavis press releases, ERA5,
  public market data): Borrentin solar (114 MWp, Mecklenburg-Western Pomerania, about 121 GWh
  a year, PPA with Allego) and Everswinkel wind (28.5 MW, NRW, 4 Nordex N149 + 1 N163, about
  64 GWh a year, EEG). ERA5 weather downloaded for both sites (1995-2026).
- Unpublished details are stated assumptions: tilt 25°, DC/AC 1.2; the Enercon E-126 EP4
  curve as a stand-in for the Nordex N149 (similar specific power), hub height 164 m.
- Losses calibrated so that the P50 matches the published yields (solar 10 → 12.4%, wind
  12 → 26.4%: the physical models gave +2.8% and +19.5%); the Step 4 report shows the check.
- Dashboard park labels; Step 3 full-load hours from the published yields; memo header states
  that the results are no view on actual contracts.
- Step 3 also back-tests each park's own Step 4 profile (`site_energy`, report section 2), so
  every step from 3 to 9 is park-specific; Steps 1, 2 and 5 describe the German market (one
  bidding zone, the same price for both parks) and are park-independent by design.
- Notebook: site names and the turbine curve in the Step 4 cells come from the configuration.
- README: Borrentin is contracted to Allego (10-year PPA from December 2024) and Everswinkel
  is paid under the EEG, so the PPAs priced here are hypothetical.

### Findings
- Borrentin: 10-year indicative 44.7 EUR/MWh (fair 55.5; 37.5 at the recent level's capture
  rate); the PPA cuts the 95% cash flow at risk from EUR 3.68 m to 0.77 m.
- Everswinkel: 80.0 EUR/MWh; its wind moves the German price more than the North Frisian site
  did (−11.3 EUR/MWh per +0.1 capacity factor, correlation −0.69 in 2025), so ignoring the
  weather link overstates its fair price by 19 EUR/MWh.

## [1.2.0] (ticket PPA-8c: the market's seasonal shape and a cannibalisation trend)

### Changed
- Quarterly calibration: `build_scenarios(..., quarter_forwards=...)` solves one level per
  local quarter so that each quarter averages its forward; the targets are the Q1-Q4/27 quotes
  of 14 Sep 2026 (`[price_model.quarter_quotes]`, validated against that day's Cal) scaled to
  the Cal forward (`ppa_lab.pricing.forwards.quarter_forwards`), so the year still averages
  140.21 EUR/MWh: Q1 185.3, Q2 117.7, Q3 124.3, Q4 134.3. Used in Steps 6-8 and the notebook.
- Solar capture-rate trend −1 pp a year in the base case (`[ppa.parks.solar_park]`); the
  sensitivities are named relative to the base ("1 pp/yr steeper", "flatter").
- Results record the quarter forwards (`forward.quarters`); reports and memo describe them.
- METHODOLOGY v1.2: sections 9 and 10; availability (already in the site models' losses) and
  curtailment stated correctly in the limitations.

### Findings
- The market's winter premium hurts solar and helps wind: 2027 fair price solar 89.1 → 86.9,
  wind 127.9 → 130.7 EUR/MWh.
- Ten-year indicative price: solar 50.6 → 45.2 (38.0 at the recent level's capture rate),
  wind 80.1 → 81.8 EUR/MWh.

## [1.1.0] (ticket PPA-8b: the forward is the market's)

### Changed
- The price level is the market's: `[price_model] forward_eur_mwh` = 140.21 EUR/MWh, the EEX
  German Power Cal-27 base quote of 9 Oct 2026 (with `forward_date` and `forward_source`),
  instead of the illustrative 85 EUR/MWh; later contract years follow `[ppa.forward_curve]`
  (Cal-28 104.75, Cal-29 87.58), held flat after the last quote (`tenor_price`). The forward
  sensitivities and the dashboard's forward knob shift the whole curve.
- Reports, memo and dashboard name the forward's source (`ppa_lab.pricing.forwards`); the
  results carry `forward` and `forward_curve` instead of `forward_assumption`.
- The memo's price table runs from the 2027 forward through the later years to the ten-year
  indicative price; its market line reports how far the quotes moved.
- `[hedging.market_quotes]`: five Cal-27 base quotes from 31 Jul to 9 Oct 2026 (104.24 to
  140.21); the stale August peak quote was dropped.
- Exercise checks for Steps 6, 7 and 9 updated to the new scenario data (reference solutions
  re-verified on the old data first).

### Added
- Step 7 sensitivity "Capture rate of the recent price level": scenarios rebuilt at the analog
  pool's average price (104 EUR/MWh) and scaled to the forward (the shape-factor view), because
  in the arcsinh model the capture rate rises with the level; memo lever and METHODOLOGY v1.1.
- Steps 5 and 6 say when the comparison with the latest historical year mixes in the level.

### Findings
- Solar ten-year indicative price 50.6 EUR/MWh (fair 61.1; 2027 alone 89.1), wind 80.1; at the
  recent level's capture rate solar would be 43.1.
- The curve matters as much as the level: the weighted forward over ten years is 96.7 EUR/MWh.
- Hedging holds: Cal base at 83% (solar) / 91% (wind) of output cuts merchant CFaR95 by 78% /
  68%; the buyer's premium with the minimum-variance band is 4.8 instead of 8.0 (solar).

## [1.0.0] (Step 8, ticket PPA-8; all steps done)

### Added
- Hedging with power futures (`ppa_lab.hedging`): EEX products on the delivery calendar
  (Cal base and peak, quarters, months, in local time; `product_masks`), model forwards,
  hedge payoffs, minimum-variance hedges for one or several products (`min_variance_hedge`),
  strategies compared by CFaR and variance removed (`hedge_strategies`), the PPA buyer's
  minimum-variance band (`buyer_hedge`) and a back-test on history (`backtest_hedge`).
- Step 8 report (`ppa-lab hedging`, `make hedging`, part of `make all` before the memo) with
  the forward curve, a market check against published Cal-27 quotes, the strategies, the
  buyer's hedge and the back-test, three charts and `data/processed/hedging.json`.
- `[hedging]` settings: back-test years and market quotes (product, delivery year, price,
  date, source URL), validated.
- The memo's hedge recommendation and market check, and a Hedging tab in the dashboard,
  read the Step 8 results (`reports/results.json` now contains `hedging`).
- Step 8 learning-track page, notebook section (8.1-8.6, "My solutions"), exercises;
  METHODOLOGY v1.0 (section 11, assumptions renumbered to 12); data dictionary entries.

### Findings
- A Cal base hedge of about 90% of the average output cuts the merchant CFaR95 by 81%
  (solar) and 75% (wind); monthly hedges add little and mostly fit noise.
- The PPA buyer's premium with the minimum-variance band is 4.45 instead of 5.27 EUR/MWh
  (solar) and 2.92 instead of 3.39 (wind).
- Published Cal-27 base quotes (104.24 and 113.45 EUR/MWh) are well above the assumed
  85 EUR/MWh; at 113.45 the indicative prices would be 46.8 (solar) and 93.0 (wind).

## [0.9.0] (Step 9, ticket PPA-9; Step 8 follows)

### Added
- Dashboard (`app/streamlit_app.py`, `make app`): the answer, the price stack and the year
  table for your own assumptions (park, analog pool, forward, capture-rate trend, tenor,
  discount rate, degradation, costs), risk by structure, how it was built. It reads the
  committed `reports/results.json`, imports `ppa_lab` from `src/` and installs only
  `app/requirements.txt`, so it runs on Streamlit Community Cloud without the data pipeline.
- Dashboard logic in `ppa_lab.dashboard` (tested without Streamlit); a headless smoke test of
  the app (`tests/test_app.py`, skipped where Streamlit is not installed).
- One-page management memo (`ppa-lab memo`, `make memo`, part of `make all`):
  `reports/step09_memo.md` and `.pdf`, generated from the Step 7 results, plus
  `reports/results.json` for the dashboard. `app` optional dependency (Streamlit).
- README rebuilt as a front page (CI badge, the answer, the steps at a glance, run it yourself);
  Step 9 learning-track page, notebook section (9.1-9.3, "My solutions"), exercises.

### Changed
- Step 7 results also store the whole-window premium and the pricing assumptions, and are
  strict JSON (null instead of NaN).
- Lint covers `app/` (Makefile and CI).

## [0.7.0] (Step 7, ticket PPA-7)

### Added
- Pricing and risk on the joint scenarios (`ppa_lab.pricing.risk`): every structure struck at
  its fair price with expected and P5 revenue and CFaR95 (`structure_table`,
  `structure_revenues`, reusing the Step 3 contract functions); the buyer's value and risk
  premium after a baseload hedge, split into profile and volume (`buyer_value`,
  `risk_premia`); a multi-year price with drift, degradation and discounting (`tenor_price`).
- Step 7 report (`ppa-lab pricing`, `make pricing`, part of `make all`) with the structures,
  premia, price stack, ten-year price and sensitivities, three charts and
  `data/processed/ppa_pricing.json` for Step 9; `[ppa]` and `[ppa.parks.*]` settings with the
  analog-pool decision (last 12 months) and stated cost assumptions.
- Step 7 learning-track page, notebook section (7.1-7.6, "My solutions"), exercises;
  METHODOLOGY v0.4 (section 10); data dictionary entries.

### Fixed
- Data dictionary links still pointed to `...-day-N` anchors after the rename to steps.

### Found
- Ten-year solar pay-as-produced price: 41.1 fair, 33.3 indicative EUR/MWh (wind 74.8 / 68.4).
- A baseload hedge removes 80-88% of the buyer's risk; the residual premium is 5.3 EUR/MWh for
  solar (mostly profile) and 3.4 for wind (mostly volume).
- A pay-as-produced PPA cuts the producer's CFaR95 by 86% (solar) and 77% (wind).
- The negative-price clause at the plain strike costs the solar park 25% of its revenue.

## [0.6.0] (Step 6, ticket PPA-6)

### Added
- Weather inputs for scenarios (`ppa_lab.scenarios.weather`): daily capacity factors and
  temperature, generation as local day x hour matrices (23/25-hour days handled), calendar
  mapping of weather years (29 February), monthly climatology.
- Weather-price link (`ppa_lab.scenarios.link`): regression of the daily price level on
  weather anomalies per season, AR(1) residual, analog days (k nearest within ±30 days),
  `simulate_linked`, `calibrate_linked_level`, `restrict_pool`.
- Scenario generator (`ppa_lab.scenarios.generator`): weather years x price paths with one
  level for all, linked or independent prices, per-scenario table and fair price.
- Step 6 report (`ppa-lab scenarios`, `make scenarios`, part of `make all`) with three charts,
  an analog-pool sensitivity and `data/processed/scenarios_2027.parquet` for Step 7;
  `[scenarios]` settings.
- Step 6 learning-track page, notebook section (6.1-6.6, "My solutions"), exercises;
  METHODOLOGY v0.3 (section 9); data dictionary entries.

### Changed
- The project is organised in **steps** instead of sprint days: learning-track pages,
  exercises, reports, figures, report modules (`analysis/stepNN_report.py`,
  `write_stepNN_report`), tests, notebook sections and docs now say "Step N" (files moved
  with history). Report numbers are unchanged.
- `prices.model`: the level bisection is `solve_level` and the random streams are public
  (`random_streams`), both reused by the scenarios. `analysis.step05_report` exposes
  `calibration_history`.

### Found
- With independent prices the wind park earns the baseload price (capture rate 1.00-1.02);
  linked to the weather 0.87-0.89, history 0.83-0.88. 2027 fair price: wind 87.00 -> 75.35,
  solar 51.76 -> 48.66 EUR/MWh.
- The analog pool mixes years with different solar capacity: 2024 solar falls below its
  history in-sample (0.54 vs 0.62; 0.64 with a 2024-only pool), and the 2027 solar fair price
  drops to 41.08 EUR/MWh with analogs from the last 12 months.
- Wind 2024 stays outside the simulated range with any pool (open item).

## [0.5.0] (Step 5, ticket PPA-5)

### Added
- Price calendar (`ppa_lab.prices.calendar`): local hour, season and day type with the nine
  nationwide German holidays (Easter computed).
- Stochastic hourly price model (`ppa_lab.prices.model`): arcsinh transform, monthly levels
  and daily shape (back-fitted), a daily AR(1) factor with seasonal shocks, intraday patterns
  resampled as whole historical days; `calibrate_level` to a forward price by bisection with
  common random numbers; optional level volatility; JSON save/load.
- Validation against history (`ppa_lab.prices.validation`): quantiles, negative share and
  autocorrelation with a 5-95% range across paths.
- Step 5 report (`ppa-lab prices`, `make prices`, part of `make all`) with three charts and
  `data/processed/price_model.json` for Step 6; `[price_model]` settings.
- Step 5 learning-track page, notebook section (5.1-5.7, "My solutions"), exercises;
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

## [0.4.0] (Step 4, ticket PPA-4)

### Added
- ERA5 weather through the Open-Meteo archive API (`ppa_lab.data.open_meteo`): pure
  parser, conversion from end-of-hour radiation labels to interval-beginning hours, and a
  sun-position check of the timestamps (`radiation_timing_offset`).
- Weather pipeline (`ppa_lab.data.weather_pipeline`): one raw file per site and year with
  manifest (ERA5 grid point, licence, completeness), processed weather and generation.
- Site models: pvlib solar park (`ppa_lab.weather.pv`) and windpowerlib wind park with
  hourly shear (`ppa_lab.weather.wind`); P50/P90 and trends (`ppa_lab.weather.yields`,
  `ppa_lab.analysis.generation`).
- Step 4 report (`ppa-lab weather`, `make weather`, part of `make all`) with two charts.
- Sites and model specs in `[pricing.parks.*]`, `[weather]` settings; pvlib and
  windpowerlib as dependencies.
- Step 4 learning-track page, notebook section (4.1-4.6, "My solutions"), exercises;
  METHODOLOGY v0.1 (volume section); data dictionary entries.

### Changed
- Retry and back-off logic moved from the Energy-Charts client into a shared
  `JsonApiClient` (`ppa_lab.data.http`).

### Found
- Open-Meteo labels radiation at the end of its hour; without the shift solar output
  would sit one hour late against prices.
- The first wind site (54.50 N, 9.00 E) was an ERA5 cell with 0 m elevation (partly sea):
  3,961 full-load hours. Moved 0.25° inland (30 m): 3,668.

## [0.3.0] - 2026-10-08 (Step 3, ticket PPA-3)

### Added
- `ppa_lab.pricing.contracts`: cash flows per interval to the producer for merchant,
  pay-as-produced (with and without a negative-price clause), virtual PPA (CfD),
  floor / cap / collar and baseload PPAs; fair pay-as-produced and baseload prices
  (ratio of expectations, with discounting); works on pandas Series and NumPy scenarios.
- `ppa_lab.pricing.backtest`: illustrative parks from national profiles, strikes fixed
  from the previous year, plan (same terms on the previous year) and surprise.
- Step 3 report (`ppa-lab ppa`, `make ppa`, part of `make all`; skipped with a warning when
  the data range has no complete previous year) with two charts.
- `[pricing]` configuration (parks, delivery years, floor), validated on load.
- `METHODOLOGY.md` version 0: the pricing maths, conventions, assumptions, limitations.
- Step 3 learning-track page, notebook section (3.1-3.6 and "My solutions"), exercises.

### Changed
- Data dictionary: contract cash flows and back-test tables.

### Found
- Monthly revenue spread within a year measures seasonality, not risk (a PaP PPA looked
  riskier than merchant); replaced by the surprise against plan.

## [0.2.0] - 2026-10-08 (Step 2, ticket PPA-2)

### Added
- Capture prices and capture rates (`ppa_lab.analysis.capture`): the legal quarter-hour
  formula, hourly prices mapped onto the 15-minute generation grid without filling gaps,
  monthly and annual tables per technology with energy and share at negative prices.
- Official monthly market values 2023-01 to 2026-08 (`data/reference/`) and a monthly
  comparison; 15 new reconciliation references (annual market values 2023-2025 for solar,
  wind onshore and offshore; 2023/2024 spot; Vermarktungsmenge).
- `Reference.note` and the status "explained difference": a documented cause for a
  difference beyond tolerance (known-breaks register).
- Step 2 report (`ppa-lab capture`, `make capture`, part of `make all`) with three charts.
- Step 2 exercises with automatic checks; learning-track page and PDF.
- `notebooks/ppa_lab_playground.ipynb`: living playground notebook (Step 1 and Step 2
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
- The Step 1 report only shows the references it computes and lists documented causes.

### Found
- 2024 spot difference (−0.95 EUR/MWh) is the SDAC partial decoupling of 26 June 2024.
- Wind capture prices are systematically above the official values (open, PPA-2b).

### Fixed
- Step 2 report crashed on real data (`Period` with an f-string date format); covered
  by a new test.
- ENTSO-E returns two day-ahead series for DE-LU (`classificationSequence` 1 and 2);
  merging them doubled the rows. The client now keeps sequence 1 by default.

## [0.1.0] - 2026-10-07 (Step 1, ticket PPA-1)

### Added
- Project skeleton: `src/` layout, `pyproject.toml`, Makefile, CI workflow, MIT licence.
- `config/project.toml` with market, date range, SDAC price limits (floor -500 to
  -600 EUR/MWh from delivery day 29 May 2026) and reconciliation references.
- Energy-Charts API client with timeouts, exponential back-off and `Retry-After`
  handling for HTTP 429; pure parsers for prices and generation.
- Raw monthly Parquet cache with manifests (parameters, checksum, licence, completeness).
- Processed datasets: native-resolution prices, hourly prices, 15-minute and hourly generation.
- DST-aware data-quality checks, including a night-time solar check that catches time-zone bugs.
- Annual statistics, reconciliation against published figures, Step 1 report with four charts.
- 52 offline tests using real API fixtures (94% coverage); one opt-in live contract test.
- `make docs`: learning-track pages rendered to PDF with headless Chrome.

### Fixed during development
- pandas 3 infers datetime units: interval lengths are now computed from time
  differences, and all indexes are normalised to nanoseconds.
- The API returns HTTP 429 with `Retry-After`; the client now waits as instructed.
