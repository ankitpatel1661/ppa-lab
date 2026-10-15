# Step 6: Weather and prices together (ticket PPA-6)

> **Numbers on this page (update for v1.1).** This page was written with the illustrative
> forward of 85 EUR/MWh (v1.0). Since v1.1 the model uses the market forward curve (EEX Cal-27
> base 140.21 EUR/MWh on 9 Oct 2026, Cal-28 104.75, Cal-29 87.58; see
> [Step 8, section 4.6](step08_hedging.md#46-update-v11-the-forward-is-now-the-markets)), and
> since v1.2 the market's seasonal shape and a solar cannibalisation trend
> ([section 4.7](step08_hedging.md#47-update-v12-the-markets-seasons-and-a-cannibalisation-trend)),
> so prices and fair prices are higher. The methods and lessons are unchanged; current numbers
> are in the reports and the README, and the exercise checks use the current data.

> **Time needed:** about 5 hours. Concepts take 75 minutes, code tour and findings
> 60 minutes, hands-on, notebook and exercises 2 hours, to-dos 45 minutes.
> **You will be able to:** explain why volumes and prices must be simulated together, build
> a weather-conditioned price simulation (a regression for the daily level plus analog days
> for the hourly shape), validate it out of the box, and show what ignoring the link costs in
> EUR/MWh.

**Contents:** [0. Scenario](#0-the-scenario) ·
[1. Concepts](#1-concepts-you-need-today) ·
[2. Architecture](#2-what-was-built-architecture) ·
[3. Code tour](#3-code-tour) ·
[4. Findings](#4-five-real-findings) ·
[5. Hands-on](#5-hands-on-run-it-yourself) ·
[6. Results](#6-results-what-the-scenarios-say) ·
[7. Exercises](#7-exercises) ·
[8. Quiz](#8-self-check-quiz) ·
[9. Interview](#9-interview-corner) ·
[10. Real work](#10-how-this-maps-to-real-work-at-encavis) ·
[11. To-dos](#11-your-to-dos-for-step-6) ·
[12. Glossary](#12-glossary) ·
[13. Sources](#13-sources)

---

## 0. The scenario

Monday. Risk management reviews the Step 5 numbers and sends one line back:

> *"Your wind park earns 102% of the baseload price in your simulation. In reality it has
> never earned more than 90%. Windy hours are cheap hours. Fix the correlation before
> anything goes to the pricing committee. Ticket PPA-6."*

They are right. Step 4 produced 31 years of weather and park output; Step 5 produced price
paths. But the price paths never looked at the weather: a stormy day was as likely to get
an expensive price day as a calm one. For a wind or solar PPA that is the worst possible
simplification, because **what a park earns is the product of its volume and the price in
the same hour**, and the two move against each other. Step 6 simulates them together.

**Ticket PPA-6: acceptance criteria (all met today)**

- [x] Daily weather features per site and day (solar and wind capacity factor, temperature),
      generation as a day × hour matrix that can be placed on any delivery calendar.
- [x] A weather-price link: the daily price level responds to the weather anomaly; the
      hourly pattern comes from historical analog days with similar weather.
- [x] Parameter recovery on synthetic data with a known weather response and known memory.
- [x] Scenarios: every weather year 1995-2025 × 16 price paths for 2027, with one level
      calibrated to the forward; the same scenarios with independent prices for comparison.
- [x] Checks: simulated correlation between weather and price ≈ history; historical capture
      rates inside the simulated range; convergence with the number of scenarios.
- [x] Report, per-scenario results for Step 7, learning page, notebook section, exercises.

---

## 1. Concepts you need today

### 1.1 Why volume and price must be simulated together

For one hour, a park earns q × P. Over a year the **capture price** is Σ qP / Σ q, and

    E[q P] = E[q] · E[P] + Cov(q, P)

The covariance term is negative for renewables: when the wind blows, every wind park in
Germany produces, the merit order shifts, and the price falls (Step 1 showed it for
residual load). A model in which q and P are independent sets Cov(q, P) = 0 and therefore
pays every MWh the **average** price of its hours. For wind that means a capture rate near
1.0; history says 0.83-0.88. The error is not small and not random: it always favours the
seller of renewable power.

> **Pitfall:** "We simulate weather and prices, then combine them" sounds right but is
> wrong unless the two simulations share the same weather. Independence is a modelling
> choice, and here a very expensive one.

### 1.2 Two ways to link them, and the one used here

| Approach | Idea | Strength | Weakness |
|---|---|---|---|
| **Structural** | Price responds to renewable output through a regression (or a merit-order model) | Extrapolates to weather that never happened | Needs a functional form; misses the shape of a day |
| **Matched historical days** (analogs) | Take the prices of a historical day with similar weather | Keeps every real feature of a day's prices | Limited to what happened in the calibration window |

The model uses **both**, each where it is strong:

    y_t = seasonal mean (Step 5) + E_d + r_d + u_(j, hour)

- **E_d, the weather effect** on the day's level: one regression per season of the Step 5
  daily factor on the day's weather anomalies (solar CF, wind CF, temperature).
- **r_d, what weather does not explain** (gas, demand, outages, weather in other countries):
  an AR(1) across days, as in Step 5 but smaller.
- **u_(j, hour), the intraday pattern of an analog day j:** one of the k = 10 historical days
  within ±30 days of the same date whose weather was closest. The analog day also supplies
  the shock of r.

### 1.3 Anomalies: within the month in-sample, against climatology for the future

The regression uses **anomalies**, not raw weather, and which anomaly depends on the use:

- **In the calibration window** the Step 5 monthly levels already contain each month's
  average weather (a windy January has a low fitted January level). Only the deviation
  from the month's own mean may move the daily level, otherwise the weather is counted
  twice.
- **For a future year** the monthly levels are "normal" (from the forward), so the anomaly is
  taken against the **climatology** of the weather years 1995-2025: a windy January in
  weather year 2015 is a cheap January in 2027.

`weather_effect(link, weather, in_sample)` implements exactly this switch, and a test
checks that a constant shift of the weather moves nothing in-sample but moves the price for
a future year.

### 1.4 Analog days (k nearest neighbours)

For a simulated day with weather w (from any weather year), the candidates are the 998
historical days within ±30 days of the same date, in any of 2024-2026. Their distance to w is

    distance² = Σ_features ((w_f − w_f,candidate) / sd_f)²

(each feature scaled by its standard deviation over the pool, so a capacity factor and a
temperature count equally). The 10 nearest form the menu; each path draws one at random.
This is the classic k-nearest-neighbour bootstrap of hydrology and weather generators
(Lall and Sharma, 1996): it reproduces the joint distribution of weather and prices without
writing it down.

In-sample validation must **exclude the neighbourhood of the day itself** (here ±7 days):
otherwise a historical day finds itself as its own nearest analog and the validation
measures memory, not modelling.

### 1.5 The scenario set and the fair price

A scenario s is a pair (weather year Y, price path n). Its volumes are the parks' output in
weather year Y, **placed date by date** on the 2027 calendar (29 February maps to 28
February); its prices are simulated for that weather. 31 weather years × 16 paths = 496
scenarios, all with equal weight. One annual level is calibrated so that the average price
over all scenarios equals the 85 EUR/MWh forward (Step 5's bisection, now over all
scenarios), and the level uncertainty adds one shift per scenario.

The fair pay-as-produced price is Step 3's formula over the scenarios:

    K* = E[Σ_t q_t P_t] / E[Σ_t q_t] = Σ_s revenue_s / Σ_s energy_s

It is **not** the average of the scenario capture prices: years with more energy weigh
more (Exercise 3 shows the difference).

### 1.6 How many scenarios are enough?

The Monte Carlo standard error of a ratio estimator is

    SE(K*) ≈ sd_s(revenue_s − K* · energy_s) / (√S · mean_s(energy_s))

With 496 scenarios it is 0.75 EUR/MWh for solar and 0.80 EUR/MWh for wind: mostly the level
uncertainty, which moves whole years. Halving it needs four times as many scenarios. The
convergence chart shows the running estimate settling inside ±2 standard errors after about
100 scenarios.

---

## 2. What was built: architecture

```
Step 4: generation_<park>.parquet, weather_solar_park.parquet        Step 5: price model (fit)
            │                                                               │
scenarios/weather.py  daily_features (solar CF, wind CF, temperature) ─ monthly_climatology
                      day_hour_matrix (local day x 24) ─ weather_days_for (calendar mapping)
            │                                                               │
scenarios/link.py     fit_link(): regression per season + AR(1) residual + analog pool
                      analog_days(): k nearest within ±window, optional exclusion
                      simulate_linked() / calibrate_linked_level() / restrict_pool()
            │
scenarios/generator.py  build_scenarios(): weather years x paths, one level for all
                        scenario_table(): energy, revenue, capture price and rate per scenario
                        fair_price(): E[sum qP] / E[sum q]
            │
analysis/step06_report.py ─► reports/step06_joint_scenarios.md + 3 charts      (`ppa-lab scenarios`)
                        ─► data/processed/scenarios_2027.parquet (input for Step 7)
```

Two small refactors of Step 5 code made this possible without copying: the level bisection is
now `solve_level(mu0, x, scale, target)` and the seeded random streams are public
(`random_streams(seed)`). The Step 5 tests passed unchanged.

---

## 3. Code tour

### 3.1 `scenarios/weather.py`

- `daily_features` turns hourly MW into **capacity factors** (mean MW / capacity) per local
  day; temperature is the daily mean. Capacity factors make solar and wind comparable.
- `day_hour_matrix` stores generation as local day × 24 local hours. A 25-hour October day
  averages its two 02:00 hours, a 23-hour March day interpolates its missing 02:00. Any
  weather day can then be placed on any delivery hour by (day, local hour), whatever the
  daylight-saving calendar of either year.
- `weather_days_for(delivery_days, year)` keeps the calendar date and maps 29 February to
  28 February when the weather year has none.

### 3.2 `scenarios/link.py`

`fit_link` decomposes the calibration history exactly as Step 5 does (transform, minus the
seasonal mean), then regresses each season's daily level on the within-month weather
anomalies, fits the AR(1) of what is left, and stores the analog pool: each complete day's
date, weather, standardised shock and 24-hour pattern. `simulate_linked` takes one row of
weather per simulated day and returns paths × hours in EUR/MWh; without an annual level it
re-simulates the calibration window (in-sample), with one it simulates a future year.

### 3.3 `scenarios/generator.py`

`build_scenarios` loops over the weather years, places their volumes on the delivery hours,
simulates their residuals (linked or independent), then solves **one** level for all
scenarios so the overall average is the forward. `Scenarios.volume(park)` expands the
per-year generation rows to one row per scenario only when needed (memory: 496 × 8,760
prices take 35 MB).

### 3.4 `analysis/step06_report.py` and `ppa-lab scenarios`

Fit, in-sample validation against Step 5 with the real weather, capture rates per historical
year, the 2027 scenarios (linked and independent), the pool sensitivity, three charts, and
`scenarios_2027.parquet`. About 20 seconds. `ppa-lab all` now ends with this step.

### 3.5 Tests: what each one protects

| Test file | Protects against |
|---|---|
| `test_scenarios_weather.py` (5) | capacity factors in UTC days; wrong 23/25-hour day handling; 29 February crashes; climatology over the wrong years |
| `test_scenarios_link.py` (11) | failure to recover a known wind response (−1.5) and residual memory; missing weather days; analogs outside the window or too close to the target; no wind effect on future prices; no deeper midday dip on sunny days; weather counted twice in-sample; a level that misses the forward; a constant feature turning distances into NaN; pool restriction |
| `test_scenarios_generator.py` (6) | wrong scenario count or order; volumes from the wrong weather year; average price ≠ forward; prices built on another year's weather; fair price computed as a mean of capture prices |
| `test_step06_report.py` (3), `test_config.py` (+1), `test_cli.py` (+1) | the report end to end, the missing-Step-4 message, the pool options, `[scenarios]` validation, `ppa-lab scenarios` and `all` |

Each key test was checked by planting the bug: no weather effect, analogs drawn without
looking at the weather, in-sample anomalies against climatology, no exclusion, prices
conditioned on the first weather year only, a level off by 0.05. The first version of the
generator test survived the "wrong weather year" bug, because averaging over all weather
years hid it; it now checks every weather year separately for wind.

---

## 4. Five real findings

### 4.1 Wind is where independence hurts most

| Wind park capture rate | History | Step 5 (independent) | Step 6 (linked) |
|---|---|---|---|
| 2024 | 0.827 | 1.000 (0.978-1.023) | 0.865 (0.845-0.883) |
| 2025 | 0.881 | 1.021 (0.998-1.040) | 0.893 (0.875-0.911) |

With independent prices the wind park earns **the baseload price**, as if wind had no
influence on prices. With the link it earns 87-89% of it, close to history. In money: the
2027 fair pay-as-produced price falls from 87.00 to 75.35 EUR/MWh, **11.64 EUR/MWh or 13%**.
For solar the error is 3.09 EUR/MWh (51.76 → 48.66), because Step 5 already knew the
*average* midday dip; it did not know that sunny days have deeper ones.

### 4.2 The daily level responds to weather as the merit order says

At 85 EUR/MWh, per +0.1 capacity factor (and per +1 °C):

| Season | R² | Solar | Wind | Temperature |
|---|---|---|---|---|
| Winter | 0.44 | −6.3 | −5.6 | −2.1 |
| Spring | 0.52 | −11.7 | −6.0 | −0.3 |
| Summer | 0.56 | −7.2 | −6.4 | +1.1 |
| Autumn | 0.54 | −0.4 | −8.3 | −0.5 |

Every sign makes sense: more wind or sun means cheaper power; cold winter days are
expensive (heating, more gas plants running), hot summer days slightly expensive (cooling
demand, rivers too warm for thermal plants). Spring solar has the largest effect: high
sun, mild demand. Weather explains about half of the day-to-day price moves; the rest
(gas, demand, outages, weather abroad) keeps a memory of φ = 0.456 per day, half-life 0.88
days. In daily data the within-month correlation between wind and price is −0.58 in
history, 0.00 for Step 5 and −0.60 for Step 6 (chart `step06_link.png`).

### 4.3 The analog pool mixes years with different amounts of solar

In-sample, 2024 falls **outside** the simulated range for solar (history 0.622, Step 6
0.513-0.568). The cause is the pool: 2024 days get intraday patterns from 2025 and 2026, when
more solar capacity made midday dips deeper. The experiment that proves it: with analogs from
2024 only, the simulated 2024 solar capture rate is 0.643, close to history.

For 2027 this matters a lot, because 2027 will have even more solar than 2026:

| Analog days from | Days in pool | Solar fair price | Solar median capture rate | Wind fair price |
|---|---|---|---|---|
| 2024-01-01 (whole window, base case) | 998 | 48.66 | 0.570 | 75.35 |
| 2025-01-01 | 635 | 44.87 | 0.523 | 75.26 |
| 2025-10-01 (last 12 months) | 363 | 41.08 | 0.479 | 74.81 |

The choice of which past represents 2027 moves the solar price by **7.6 EUR/MWh (15%)**, more
than the weather link itself. Wind barely moves. The base case stays the whole window (it is
what was validated); Step 7 must decide, and this table is the argument. A professional answer
would add a fundamental view of 2027 solar capacity.

> **Interview:** "The biggest single assumption in my solar price was not the stochastic
> model but which historical days represent 2027. I showed the sensitivity instead of hiding
> it: 48.7 with the full window, 41.1 with the last twelve months."

### 4.4 What is still not explained

- **Wind 2024** stays outside the range (history 0.827, Step 6 0.845-0.883) even with a
  2024-only pool. The pool is not the cause; candidates are a stronger price response to wind
  in 2024 or curtailment of real parks at negative prices (our park produces its potential
  output). Open item.
- **One statistic fewer inside the range in-sample:** Step 6 meets 6 of 11 (Step 5: 7). The 95%
  quantile moves out (178.3 vs 173.7), while the 24-hour autocorrelation improves (0.593 →
  0.621), as do the negative share (4.9% → 5.1%) and the weekly autocorrelation. The link
  makes days more extreme in both directions; the soft floor at zero (Step 5, section 4.4) is
  still missing.
- **Auction limits:** 0.0008% of simulated hours fall below −500 EUR/MWh (minimum −660; the
  2027 floor is −600). Clipping them would move the solar fair price by 0.004 EUR/MWh, so the
  model leaves them.

### 4.5 Small ones

- **A test that averaged a bug away:** "prices linked to the wrong weather year" passed the
  first capture-rate test, because the one correctly linked year pulled the average down
  enough. The test now checks every weather year for wind (solar's effect is too small per
  year to test that way).
- **Weather counted twice:** the first draft took anomalies against climatology also
  in-sample, where the monthly levels already contain the month's weather. A dedicated test
  now pins the in-sample rule.
- **A flat feature:** the fake weather in the end-to-end test has a constant temperature, so
  its standard deviation is 0 and every analog distance became NaN. Constant features are now
  scaled by 1.
- **Dates in UTC:** the first report printed the calibration start as 2023-12-31 (the UTC
  timestamp of local midnight on 1 January). It now prints the configured local dates.
- **Chart labels on top of bars:** the historical-year markers moved into the legend.

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                  # 194 offline tests
make scenarios             # link, validation, 2027 scenarios, sensitivity (about 20 s)
open reports/step06_joint_scenarios.md
make notebook              # Step 6 section: 6.1 to 6.6, then your solutions
```

In the notebook: 6.2 shows analog days of any date (their hourly prices look alike), 6.3
prices one week of 2027 with the weather of any year, 6.6 changes the analog pool.

---

## 6. Results: what the scenarios say

### 6.1 Validation with the real weather of 2024-2026

| Check | History | Step 5 | Step 6 |
|---|---|---|---|
| Statistics inside the 5-95% range (of 11) | | 7 | 6 |
| Share of negative hours | 6.2% | 4.9% | 5.1% |
| Autocorrelation at 24 hours | 0.700 | 0.593 | 0.621 |
| Within-month correlation, wind vs daily price | −0.58 | 0.00 | −0.60 |
| Solar capture rate 2025 | 0.555 | 0.617 | 0.575 |
| Wind capture rate 2025 | 0.881 | 1.021 | 0.893 |

### 6.2 Delivery year 2027 (31 weather years × 16 paths, forward 85 EUR/MWh)

| Park | Prices | Fair PaP price | Capture rate 5/50/95% | Revenue P10/P50/P90 (EUR m) | Corr(energy, baseload price) |
|---|---|---|---|---|---|
| Solar | independent | 51.76 | 0.458 / 0.605 / 0.692 | 1.71 / 2.82 / 4.06 | +0.00 |
| Solar | **linked** | **48.66** | 0.404 / 0.570 / 0.661 | 1.52 / 2.67 / 3.90 | −0.03 |
| Wind | independent | 87.00 | 0.990 / 1.018 / 1.050 | 6.97 / 9.55 / 12.49 | +0.01 |
| Wind | **linked** | **75.35** | 0.830 / 0.883 / 0.915 | 5.88 / 8.23 / 10.95 | −0.12 |

The 2025 capture rates of both parks (0.555 and 0.881) fall inside the linked 5-95% ranges;
the wind one is far outside the independent range.

![Capture rate per scenario: linked vs independent, with history](../../reports/figures/step06_capture_rates.png)

![Within-month daily price vs wind: history, Step 5, Step 6](../../reports/figures/step06_link.png)

![Convergence of the fair price](../../reports/figures/step06_convergence.png)

### 6.3 Five stories

1. **Independence is a gift to the seller.** Prices that ignore the weather overstate the
   fair price by 3 EUR/MWh for solar and 12 EUR/MWh for wind. On 110 GWh of wind a year that
   is about EUR 1.3 million per year.
2. **A windy year is a cheap year.** Across weather years, the wind park's energy and the
   baseload price correlate at −0.12: more MWh, each worth less. Volume risk and price risk
   partly offset for the producer, and a model must keep that.
3. **The weather explains half.** R² of 0.44-0.56 per season: the other half of daily price
   moves comes from gas, demand and outages, which is why the AR(1) residual stays.
4. **Which past represents the future** moves the solar price by 15%. Model choices you
   can see (a regression) matter less than data choices you might not notice (the pool).
5. **496 scenarios give ±0.8 EUR/MWh.** Precise enough to compare structures in Step 7, not
   precise enough to quote to the cent.

### 6.4 What this means for pricing

- Step 7 prices the solar pay-as-produced PPA on these scenarios, adds the risk premium
  (Step 3, METHODOLOGY section 5) and must choose the analog pool explicitly.
- Every number above is for the **potential** output of the parks. Curtailment at negative
  prices (common for real parks) would raise their capture rates a little and is one candidate
  for the wind 2024 gap.

---

## 7. Exercises

**Warm-up (in `exercises/step06_joint.py`, checked by `.venv/bin/pytest exercises -q`)**

1. **How much does wind move the price?** Slope and correlation of daily price on the wind
   park's capacity factor, within the month, for 2025.
2. **Analog days:** the 5 days of 2024-2025 whose weather is closest to 15 June 2025.
3. **The fair price from scenarios,** linked and independent, from `scenarios_2027.parquet`.
4. **Written:** the colleague who priced wind with independent prices.

**Core**

5. **Recency weighting instead of a cut.** Instead of restricting the pool, weight analog
   days by age (for example halving every 12 months). Implement it in `analog_days` behind a
   parameter, test first, and compare with the sensitivity table.
6. **Wind 2024.** Fit the link on 2024 only and on 2025-2026 only. Is the wind response
   different? Does it explain the 2024 gap (section 4.4)?
7. **Monthly capture rates.** Compute the solar capture rate per calendar month over the
   scenarios. In which months does the link change it most, and why?

**Stretch**

8. **Curtailment.** Set the parks' output to zero in hours with negative prices and recompute
   capture rates. How much of the wind 2024 gap disappears?
9. **More scenarios.** How many scenarios do you need for a standard error of 0.25 EUR/MWh?
   Check with `paths_per_weather_year = 64`.

<details>
<summary>Hints and solution sketches</summary>

1. Daily means of `price_eur_mwh` and `mw / 30`, `groupby(index.month).transform("mean")` to
   take out each month, then `sum(w * p) / sum(w ** 2)`. 2025: −6.64 EUR/MWh per +0.1 CF,
   correlation −0.579 (2024: −7.57 and −0.590). The link's seasonal responses (−5.6 to −8.3)
   are in the same range.
2. Filter by circular day-of-year gap ≤ 30, drop |days| < `exclude`, scale by the column
   standard deviations over all rows, sum squares, sort stably. Without exclusion the first
   analog is 15 June 2025 itself; with `exclude=8` the first is 26 June 2024.
3. `groupby("prices")` and Σ revenue / Σ MWh: solar 99.08 → 95.61, wind 145.43 → 131.13 with
   the market forward curve and seasonal shape of v1.2 (at 85: 51.76 → 48.66 and 87.00 → 75.35).
   The mean of the capture prices gives 95.66 and 131.25: years with more energy count more in the fair price, and for
   wind those are the cheaper years.
4. Cov(q, P) < 0 for wind: windy hours are cheap, so an independent model pays every MWh the
   average price (capture rate about 1.0 instead of 0.88). For solar Step 5 already knew the
   average midday dip, so only the day-to-day part (sunny days deeper) was missing. But the
   pool sensitivity shows the solar price could be up to 7.6 EUR/MWh lower if recent days
   represent 2027, so the true solar error may be larger than 3.
5. `weights = 0.5 ** (age_days / 365)`; draw with `rng.choice(near, p=w / w.sum())`.
6. `fit_link(model, hist.loc["2024"], ...)` and compare `link.beta["wind"]`.
7. Group the hourly scenario prices by month before summing.
8. `q = np.where(P < 0, 0, q)`; recompute Σ qP / Σ q.
9. SE scales with 1/√S: (0.8 / 0.25)² × 496 ≈ 5,000 scenarios.

</details>

---

## 8. Self-check quiz

1. Write E[qP] in terms of E[q], E[P] and Cov(q, P). Which term does an independent model drop?
2. Why does the wind park's capture rate come out near 1.0 with independent prices?
3. What are the two parts of the weather-price link, and what does each do best?
4. Why are weather anomalies taken within the month in-sample but against climatology for 2027?
5. What is an analog day, and why must validation exclude days close to the target?
6. How is a weather year from 2004 placed on the 2027 calendar?
7. Why is the fair price Σ revenue / Σ energy and not the mean of the capture prices?
8. What does a correlation of −0.12 between annual wind energy and baseload price mean for the producer?
9. Why did 2024 solar fall outside the simulated range, and what does it imply for 2027?
10. How does the Monte Carlo standard error fall with the number of scenarios?

<details>
<summary>Answers</summary>

1. E[qP] = E[q]E[P] + Cov(q, P); independence sets the covariance to zero.
2. Each MWh is paid the average price of its hours, and wind produces at all hours of the day,
   so its volume-weighted price is close to the baseload price.
3. A regression per season moves the day's level with the weather (and extrapolates to new
   weather); analog days supply realistic 24-hour patterns for that weather.
4. In-sample the fitted monthly levels already contain each month's weather; for 2027 the
   levels are normal, so a windy month must lower prices relative to normal.
5. A historical day within ±30 days of the date, in any year, with the closest weather. Without
   exclusion a day would find itself and the check would reproduce history by construction.
6. Date by date: 15 June 2004 → 15 June 2027 (29 February maps to 28 February), hour by local
   hour through the day × hour matrix.
7. The fair price is the ratio of expected revenue to expected energy; averaging capture
   prices gives a low-energy year the same weight as a high-energy year.
8. Windy years bring more MWh at lower prices: volume and price risk partly offset, so revenue
   varies less than volume alone suggests.
9. The pool's 2025-2026 days have deeper midday dips (more solar capacity). 2027 will have even
   more solar, so the whole-window pool probably overstates what solar earns in 2027.
10. With 1/√S: four times the scenarios for half the error.

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* my first price model was independent of the weather, so a wind park earned
> the baseload price in simulation, against 83-88% in reality. *Task:* simulate prices and
> volumes together so their correlation is preserved. *Action:* I regressed the daily price
> level on solar, wind and temperature anomalies per season, kept an AR(1) for the rest,
> and took hourly patterns from historical analog days with similar weather. I validated it
> with the real weather of 2024-2026, excluding nearby days, and built 496 joint scenarios for
> 2027. *Result:* the wind fair price fell from 87 to 75 EUR/MWh and solar from 52 to 49; the
> historical capture rates fall inside the simulated ranges; and I found that the period of
> historical days used moves the solar price by another 15%.

**Likely questions and strong answers:**

- *"How do you handle the correlation between generation and price?"* Simulate them from the
  same weather: prices conditional on the weather scenario, through a structural response plus
  matched historical days, then validate the simulated correlation and capture rates against
  history.
- *"Why not a copula?"* A copula on annual or daily aggregates can match a correlation, but a
  PPA needs the hourly joint behaviour (the midday dip on sunny days). Conditioning on the
  weather keeps it by construction.
- *"Your model has a limited history of prices. How do you price 2027?"* The weather comes
  from 31 years; the price response and patterns from 2024-2026. The sensitivity to which
  years represent 2027 is reported; a fundamental view of 2027 capacity should anchor it.
- *"How many scenarios do you need?"* Enough that the Monte Carlo error is small against the
  decision: here ±0.8 EUR/MWh with 496; the error falls with 1/√S.

---

## 10. How this maps to real work at Encavis

| In this project | In a company |
|---|---|
| Regression of the daily level on weather + analog days | Fundamental (merit-order) models driven by weather years; vendor scenario sets |
| ERA5 at two sites as weather proxies | National and European weather years for all technologies and demand |
| 31 weather years × 16 paths | Thousands of joint scenarios feeding PPA valuation and risk |
| Fair price with and without the link | Shape and volume risk premia, cannibalisation discounts |
| Analog-pool sensitivity | Scenario assumptions on capacity build-out (PV, batteries) |
| Capture rates in range of history | Back-testing of PPA valuations against realised settlement |

Encavis prices PPAs for its own solar and wind parks: exactly the case where an independent
model would overstate revenue and lead to offers that look profitable but are not.

---

## 11. Your to-dos for Step 6

- [ ] Read sections 1 and 4. By hand: with E[q] = 10 MWh, E[P] = 85 EUR/MWh and
      Cov(q, P) = −150, what is E[qP] and the capture price? (700, 70 EUR/MWh.)
- [ ] Run section 5; in the notebook, find an analog day in 6.2 whose hourly prices differ
      strongly from the target. What does its weather have in common, and what not?
- [ ] Exercises 1-4 in `exercises/step06_joint.py`; check them in "My solutions: Step 6".
- [ ] **Commit Step 6** (commands below).
- [ ] **German vocabulary of this step:** die Korrelation, die Kovarianz, das Wetterjahr, der
      Analogtag, das Szenario, die Monte-Carlo-Simulation, der Standardfehler, das
      Erzeugungsprofil, der Kannibalisierungseffekt, der Kapazitätsfaktor (auch
      Auslastungsgrad), die Klimatologie, die Abregelung (curtailment).
- [ ] Stand-up update: *"Yesterday: joint weather and price scenarios; the wind fair price falls
      from 87 to 75 EUR/MWh once prices see the weather. Today: price the solar PPA with its
      risk premium (PPA-7). Blockers: the analog-pool choice for 2027 needs a decision."*

Commit (check `git status` first: no `.env`, no ` M .env.example`):

```bash
cd ".../Encavis quantitative/ppa-lab"
git status --short
git add src tests exercises config reports docs notebooks METHODOLOGY.md README.md CHANGELOG.md Makefile pyproject.toml
git status --short
git commit -m "feat(scenarios): joint weather x price scenarios with a validated weather link (PPA-6)"
git push
gh run watch
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Joint scenario | One weather year paired with one price path simulated for that weather |
| Capacity factor (CF) | Mean output / capacity over a period (0 to 1) |
| Anomaly | Deviation from a reference: the month's mean (in-sample) or the climatology |
| Climatology | Average weather per calendar month over many years (here 1995-2025) |
| Weather-price link | How prices respond to weather; here a regression plus analog days |
| Analog day | A historical day with similar weather near the same date |
| k-nearest-neighbour bootstrap | Resampling among the k most similar observations |
| Exclusion window | Days near the target left out of the analogs during validation |
| Analog pool | The historical days available as analogs |
| Fair price | Break-even price: E[Σ qP] / E[Σ q] |
| Monte Carlo standard error | Uncertainty of an estimate from a finite number of scenarios |
| Curtailment | Reducing output, e.g. at negative prices |

## 13. Sources

- Lall, U. and Sharma, A. (1996): A nearest neighbor bootstrap for resampling hydrologic time
  series. *Water Resources Research* 32(3), 679-693.
- Rajagopalan, B. and Lall, U. (1999): A k-nearest-neighbor simulator for daily precipitation and
  other weather variables. *Water Resources Research* 35(10), 3089-3101.
- Hirth, L. (2013): The market value of variable renewables: the effect of solar wind power
  variability on their relative price. *Energy Economics* 38, 218-236.
- Lorenz, E. N. (1969): Atmospheric predictability as revealed by naturally occurring analogues.
  *Journal of the Atmospheric Sciences* 26(4), 636-646.
- Glasserman, P. (2003): *Monte Carlo Methods in Financial Engineering.* Springer (standard errors,
  ratio estimators).
- EPEX SPOT / SDAC: harmonised maximum and minimum clearing prices (−600 EUR/MWh from 29 May 2026,
  `config/project.toml`).
- Encavis preparation guide: joint weather and price risk, "How do you use weather data in risk?".
