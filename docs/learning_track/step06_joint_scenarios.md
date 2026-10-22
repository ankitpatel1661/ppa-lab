# Step 6: Weather and prices together (ticket PPA-6)

> **Numbers on this page.** The parks are the Borrentin solar park (114 MWp) and the
> Everswinkel wind park (28.5 MW); prices are calibrated to the market forward (EEX Cal-27
> base 140.21 EUR/MWh, each quarter at the market's seasonal shape). Results are from
> `reports/step06_joint_scenarios.md` (v1.11). The updates in sections 4.6 and 4.7 keep the
> numbers of the version they describe.

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

> *"Your wind park earns 106% of the baseload price in your simulation. In reality it has
> never earned more than 87%. Windy hours are cheap hours. Fix the correlation before
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
1.0; for Everswinkel history says 0.82-0.87 (0.70 in the 2022 crisis). The error is not small and not random: it always favours the
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

For a simulated day with weather w (from any weather year), the candidates are the
historical days within ±30 days of the same date: in any of 2024-2026 for the validation (998
days in the pool), from the last 12 months for 2027 (section 4.3). Their distance to w is

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
over all scenarios equals the forward, each quarter at its own level (Cal-27 140.21 EUR/MWh,
Q1-Q4 185 / 118 / 124 / 134; Step 5's bisection, now over all scenarios), and the level
uncertainty adds one shift per scenario.

The fair pay-as-produced price is Step 3's formula over the scenarios:

    K* = E[Σ_t q_t P_t] / E[Σ_t q_t] = Σ_s revenue_s / Σ_s energy_s

It is **not** the average of the scenario capture prices: years with more energy weigh
more (Exercise 3 shows the difference).

### 1.6 How many scenarios are enough?

The Monte Carlo standard error of a ratio estimator is

    SE(K*) ≈ sd_s(revenue_s − K* · energy_s) / (√S · mean_s(energy_s))

With 496 scenarios it is 0.77 EUR/MWh for Borrentin and 1.00 EUR/MWh for Everswinkel: mostly the level
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
| `test_step06_report.py` (4), `test_config.py` (+1), `test_cli.py` (+1) | the report end to end, the missing-Step-4 message, the pool options, `[scenarios]` validation, `ppa-lab scenarios` and `all`; since v1.6 the out-of-sample section (a perfect forward must reproduce the year's mean; the error stored is the median minus history) and the negative-tail table |

Each key test was checked by planting the bug: no weather effect, analogs drawn without
looking at the weather, in-sample anomalies against climatology, no exclusion, prices
conditioned on the first weather year only, a level off by 0.05. The first version of the
generator test survived the "wrong weather year" bug, because averaging over all weather
years hid it; it now checks every weather year separately for wind.

---

## 4. Five real findings

### 4.1 Wind is where independence hurts most

| Everswinkel capture rate | History | Step 5 (independent) | Step 6 (linked) |
|---|---|---|---|
| 2024 | 0.818 | 1.008 (0.980-1.042) | 0.848 (0.831-0.865) |
| 2025 | 0.855 | 1.037 (1.012-1.064) | 0.874 (0.858-0.887) |

With independent prices the wind park earns **more than the baseload price**, as if wind had
no influence on prices. With the link it earns 85-87% of it, close to history. In money: the
2027 fair pay-as-produced price falls from 149.51 to 130.56 EUR/MWh, **18.95 EUR/MWh or 13%**.
For Borrentin the error is 2.31 EUR/MWh (79.78 → 77.47), because Step 5 already knew the
*average* midday dip; it did not know that sunny days have deeper ones.

### 4.2 The daily level responds to weather as the merit order says

At 140 EUR/MWh, per +0.1 capacity factor of the two parks (and per +1 °C):

| Season | R² | Solar | Wind | Temperature |
|---|---|---|---|---|
| Winter | 0.64 | −6.2 | −12.3 | −2.4 |
| Spring | 0.49 | −17.1 | −13.9 | −1.7 |
| Summer | 0.47 | −9.5 | −14.3 | +1.5 |
| Autumn | 0.69 | −1.2 | −16.0 | −1.3 |

Every sign makes sense: more wind or sun means cheaper power; cold winter days are
expensive (heating, more gas plants running), hot summer days slightly expensive (cooling
demand, rivers too warm for thermal plants). Spring solar has the largest effect: high
sun, mild demand. Weather explains half to two thirds of the day-to-day price moves; the
rest (gas, demand, outages, weather abroad) keeps a memory of φ = 0.374 per day, half-life
0.70 days. In daily data the within-month correlation between Everswinkel's wind and the
price is −0.64 in history, −0.01 for one Step 5 path and −0.62 for one Step 6 path (chart
`step06_link.png`).

### 4.3 The analog pool mixes years with different amounts of solar

Each simulated day takes its hourly pattern from a historical day with similar weather. But
historical days come from years with less solar: a 2024 May day has a shallower midday dip
than a 2027 May day will. So **which past represents 2027** decides solar's price. Until v1.6
it did, by several EUR/MWh: the more recent the pool, the lower Borrentin's fair price, and
out of sample the model overstated Borrentin's capture rate by 0.09 to 0.14 (section 4.6).

The fix (v1.7, section 4.7) moves every historical day to the day it stands in for, by the
measured trend of the hourly shape. The test that the fix works is that the pool no longer
matters:

| Analog days from | Borrentin fair price 2027 | Everswinkel fair price 2027 |
|---|---|---|
| 2025-10-01 (last 12 months, base case) | 77.53 | 129.94 |
| 2024-01-01 (whole window) | 77.47 | 130.56 |

> **Interview:** "The biggest single assumption in my solar price was not the stochastic
> model but which historical days represent 2027. I showed the sensitivity, then measured how
> the daily shape changes year by year and moved the old days forward; after that the choice
> no longer moved the price, and the out-of-sample error fell from 0.09-0.14 to 0.01-0.05."

### 4.4 What is still not explained

- **Everswinkel's capture rate sits just below the range in-sample** (2024: history 0.818,
  Step 6 0.831-0.865; 2025: 0.855 against 0.858-0.887), and Borrentin's 2025 too (0.542
  against 0.550-0.595). Candidates: a stronger price response to wind than one regression per
  season can carry, and curtailment of real parks at negative prices (our parks produce their
  potential output here; Step 7 curtails since v1.8). Open item; Step 7 prices the remaining
  out-of-sample error as a sensitivity.
- **In-sample statistics:** Step 6 meets 8 of 11 (Step 5: 7). The 5% and 95% quantiles stay
  just outside (−2.2 and 178.5 against −0.1 and 173.7), and the 24-hour autocorrelation is
  still short (0.635 against 0.700): the link makes days more extreme in both directions.
- **Auction limits:** in v1.0, with a symmetric transform, 0.0008% of simulated hours fell
  below −500 EUR/MWh (the 2027 floor is −600). Since v1.6 negative prices have their own
  scale and the tail is far thinner (1% quantile −19.9 against −20.1 in history).

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

### 4.6 Update (v1.6): years the model never saw, and the negative tail

Every check so far was in-sample: the model had seen the days it was tested on (only analog
days within a week were excluded). A pricing model has to forecast a year it has not seen.

**The test.** For each year 2024, 2025 and 2026, fit the model and the link on the days from
2023 up to the end of the year before, with analog days from its last 12 months, exactly as
for 2027. Then simulate the year with its real weather and give the model each quarter's
realised average price: a perfect forward. Whatever is wrong now is the model's shape, not
the level. A second run lets the model see the year too; its error is the model's structure.

| Solar capture rate | 2024 | 2025 | 2026 (Jan-Sep) |
|---|---|---|---|
| History | 0.601 | 0.542 | 0.526 |
| Model, out of sample (median) | 0.743 | 0.675 | 0.619 |
| Model, year seen | 0.631 | 0.584 | 0.563 |

**What it says.** The model overstates solar's capture rate by 0.09 to 0.14 in every year,
even with the price level given; wind by 0.02 to 0.05. Seeing the year removes most of the
solar error: the midday dips deepen every year as solar capacity grows, and analog days from
last year cannot know that. The 2027 scenarios are built the same way, so the base case is
probably too optimistic for solar: taking the mean error off every year lowers Borrentin's
indicative price from 36.8 to 24.9 EUR/MWh (Step 7 sensitivity; backlog PPA-8e).

**The negative tail.** 65% of 2024-2026's negative hours lie between −5 and 0 EUR/MWh: when
renewables exceed demand, flexible plants stop producing at about zero, so prices bunch just
below it. The arcsinh transform treats −20 like +20, so the model spread that bunch into a
deep tail: 1% quantile −45 instead of −20, and too few negative hours. Negative prices now get
their own scale b, with −500 kept where it was:

| In-sample, real weather | 1% quantile | Negative hours | Solar output at negative prices |
|---|---|---|---|
| History | −20.1 | 6.2% | 21.8% |
| b = 120 (symmetric, until v1.5) | −45.2 | 5.6% | 18.0% |
| b = 15 (v1.6) | −21.2 | 6.6% | 21.7% |

b was chosen by a rule stated with the candidates (smallest largest error over these three
statistics), then checked out of sample, where the tail is too shallow because negative hours
are too few: the build-out problem again.

Three lessons:

1. **In-sample checks flatter.** The in-sample solar capture rate was close (0.569 vs 0.560);
   out of sample it was 0.13 off. Always ask what the model knew.
2. **Two errors can cancel.** The realistic tail raised the solar capture rate in-sample
   (0.569 → 0.587): the deep tail had been hiding midday dips that are not deep enough. Fixing
   one error exposed the other, and the out-of-sample test says which one matters more.
3. **Split the error before fixing it.** "Year seen" separates what the model cannot do
   (structure, about 0.04) from what it cannot know (one year of build-out, about 0.09).
   They need different fixes: a better model, or a view on the build-out.

### 4.7 Update (v1.7): moving old days to the simulated day

Section 4.6 showed what the model could not know: last year's analog days have last year's
shallower midday dips. The fix measures how fast the hourly shape changes and moves every
historical day to the day it stands in for:

    u(j, h)  ->  u(j, h) + tau(season, h) x (simulated day − day j) in years

tau compares the **same calendar month in different years** (May 2024 with May 2025), so the
dip that deepens from March to June every year is not mistaken for build-out. Fitted on
2024-2026, tau at midday is −0.08 to −0.17 per year in spring, smaller in summer and autumn,
about zero in winter; it sums to zero over the day, so it moves the shape, not the level.

| Out of sample, solar capture rate | 2024 | 2025 | 2026 |
|---|---|---|---|
| History | 0.601 | 0.542 | 0.526 |
| Model without the trend (v1.6) | 0.743 | 0.675 | 0.619 |
| Model with the trend (v1.7) | 0.743 (one fit year: no trend) | 0.589 | 0.537 |

Three lessons:

1. **A test you can fail is worth more than a fix you like.** The rule was set before the fix:
   keep it only if the out-of-sample error shrinks. It did, from +0.13 / +0.09 to +0.05 / +0.01.
2. **Report what got worse.** Wind's error grew by 0.006-0.009: if midday prices fall and the
   daily level stays, the other hours rise, and wind produces more in them. The backlog's rule
   said "without hurting wind"; the change was kept and the breach written down.
3. **A side effect that confirms the mechanism.** Which past days represent 2027 used to move
   the solar fair price from 93.8 to 86.4 EUR/MWh; with every day moved to 2027 it is 77.5,
   77.2 and 77.5 for the three pools. If the trend captures what changed, the pool should not
   matter, and it no longer does.

What it does not settle: continued in a straight line, the trend would cut solar's capture
rate by 5.6 pp a year. The scenarios use it only up to 2027. After 2027 solar's capture rate
follows solar and storage build-out scenarios (v1.11, Step 7 page, section 4.8).

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                  # the offline tests (290 in v1.11)
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
| Statistics inside the 5-95% range (of 11) | | 7 | 8 |
| Share of negative hours | 6.2% | 5.9% | 6.5% |
| Autocorrelation at 24 hours | 0.700 | 0.607 | 0.635 |
| Within-month correlation, Everswinkel's wind vs daily price (one path) | −0.64 | −0.01 | −0.62 |
| Borrentin capture rate 2025 | 0.542 | 0.609 | 0.571 |
| Everswinkel capture rate 2025 | 0.855 | 1.037 | 0.874 |

### 6.2 Delivery year 2027 (31 weather years × 16 paths, Cal-27 base 140.21 EUR/MWh)

| Park | Prices | Fair PaP price | Capture rate 5/50/95% | Revenue P10/P50/P90 (EUR m) | Corr(energy, baseload price) |
|---|---|---|---|---|---|
| Borrentin | independent | 79.78 | 0.501 / 0.563 / 0.615 | 6.98 / 9.49 / 12.32 | +0.01 |
| Borrentin | **linked** | **77.47** | 0.481 / 0.546 / 0.602 | 6.88 / 9.26 / 12.16 | +0.02 |
| Everswinkel | independent | 149.51 | 1.023 / 1.059 / 1.099 | 7.54 / 9.49 / 11.74 | −0.01 |
| Everswinkel | **linked** | **130.56** | 0.882 / 0.930 / 0.962 | 6.60 / 8.27 / 10.31 | −0.16 |

Borrentin's 2025 capture rate (0.542) falls inside its linked 5-95% range; Everswinkel's
(0.855) just below it (0.882-0.962), and far below the independent one. The comparison mixes
in the price level: 2027 is simulated at 140 EUR/MWh, 2025 averaged 89, and the capture rate
rises with the level (Step 7, section 7); the in-sample validation above is the test.

![Capture rate per scenario: linked vs independent, with history](../../reports/figures/step06_capture_rates.png)

![Within-month daily price vs wind: history, Step 5, Step 6](../../reports/figures/step06_link.png)

![Convergence of the fair price](../../reports/figures/step06_convergence.png)

### 6.3 Five stories

1. **Independence is a gift to the seller.** Prices that ignore the weather overstate the
   fair price by 2.3 EUR/MWh for Borrentin and 19 EUR/MWh for Everswinkel. On Everswinkel's
   64 GWh a year that is about EUR 1.2 million per year.
2. **A windy year is a cheap year.** Across weather years, Everswinkel's energy and the
   baseload price correlate at −0.16: more MWh, each worth less. Volume risk and price risk
   partly offset for the producer, and a model must keep that.
3. **The weather explains half to two thirds.** R² of 0.47-0.69 per season: the rest of the
   daily price moves comes from gas, demand and outages, which is why the AR(1) residual
   stays.
4. **Which past represents the future** decided the solar price until the old days were moved
   forward by the measured build-out trend (section 4.3). Data choices you might not notice
   (the pool) can matter more than model choices you can see (a regression).
5. **496 scenarios give ±0.8 (solar) to ±1.0 (wind) EUR/MWh.** Precise enough to compare
   structures in Step 7, not precise enough to quote to the cent.

### 6.4 What this means for pricing

- Step 7 prices the pay-as-produced PPAs on these scenarios and adds the risk premium (Step
  3, METHODOLOGY section 5), with analog days from the last 12 months (2025-10-01 on), moved
  to 2027 by the build-out trend.
- Every number above is for the **potential** output of the parks. Curtailment at negative
  prices (common for real parks) raises their capture rates a little; Step 7 models it since
  v1.8, and it is one candidate for Everswinkel's in-sample gap.

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

1. Daily means of `price_eur_mwh` and `mw / 28.5`, `groupby(index.month).transform("mean")` to
   take out each month, then `sum(w * p) / sum(w ** 2)`. 2025: −11.34 EUR/MWh per +0.1 CF,
   correlation −0.694 (2024: −11.78 and −0.621), for Everswinkel. The link's
   seasonal responses (−12.3 to −15.6, at the 140 EUR/MWh forward level) are consistent.
2. Filter by circular day-of-year gap ≤ 30, drop |days| < `exclude`, scale by the column
   standard deviations over all rows, sum squares, sort stably. Without exclusion the first
   analog is 15 June 2025 itself; with `exclude=8` the first is 3 July 2025.
3. `groupby("prices")` and Σ revenue / Σ MWh: Borrentin 79.78 → 77.47, Everswinkel
   149.51 → 130.56 at the market forward and its quarter shape. The mean of the capture prices gives 77.48 and 130.85: years with more
   energy count more in the fair price, and for wind those are the cheaper years.
4. Cov(q, P) < 0 for wind: windy hours are cheap, so an independent model pays every MWh the
   average price (capture rate 1.04 instead of 0.86 for Everswinkel in 2025). For solar Step 5
   already knew the average midday dip, so only the day-to-day part (sunny days deeper) was
   missing. But out of sample, before the v1.7 trend, Borrentin's capture rate was 0.09-0.14
   too high: independence was not solar's biggest error.
5. `weights = 0.5 ** (age_days / 365)`; draw with `rng.choice(near, p=w / w.sum())`.
6. `fit_link(model, hist.loc["2024"], ...)` and compare `link.beta["wind"]`.
7. Group the hourly scenario prices by month before summing.
8. `q = np.where(P < 0, 0, q)`; recompute Σ qP / Σ q.
9. SE scales with 1/√S: (0.77 / 0.25)² × 496 ≈ 4,700 scenarios for Borrentin, (1.00 / 0.25)²
   × 496 ≈ 7,900 for Everswinkel.

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
8. What does a correlation of −0.16 between annual wind energy and baseload price mean for the producer?
9. Why did the model overstate solar's capture rate out of sample, and how was it fixed?
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
9. Analog days come from earlier years with less solar capacity and shallower midday dips;
   2027 will have more solar still. v1.7 moves every historical day to the simulated day by
   the measured trend of the hourly shape: the error fell from 0.09-0.14 to 0.01-0.05.
10. With 1/√S: four times the scenarios for half the error.

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* my first price model was independent of the weather, so the Everswinkel wind
> park earned more than the baseload price in simulation, against at most 87% in reality. *Task:* simulate prices and
> volumes together so their correlation is preserved. *Action:* I regressed the daily price
> level on solar, wind and temperature anomalies per season, kept an AR(1) for the rest,
> and took hourly patterns from historical analog days with similar weather. I validated it
> with the real weather of 2024-2026, excluding nearby days, and built 496 joint scenarios for
> 2027. *Result:* the wind fair price fell from 150 to 131 EUR/MWh and solar from 79.8 to
> 77.5; and a test on years the model never saw showed it overstated solar by 0.09-0.14,
> until I moved the historical days forward by the measured build-out trend (0.01-0.05 left).

**Likely questions and strong answers:**

- *"How do you handle the correlation between generation and price?"* Simulate them from the
  same weather: prices conditional on the weather scenario, through a structural response plus
  matched historical days, then validate the simulated correlation and capture rates against
  history.
- *"Why not a copula?"* A copula on annual or daily aggregates can match a correlation, but a
  PPA needs the hourly joint behaviour (the midday dip on sunny days). Conditioning on the
  weather keeps it by construction.
- *"Your model has a limited history of prices. How do you price 2027?"* The weather comes
  from 31 years; the price response and patterns from 2024-2026, moved to 2027 by the
  measured build-out trend and tested on years the model never saw. For the later years of a
  contract I use solar and storage build-out scenarios.
- *"How many scenarios do you need?"* Enough that the Monte Carlo error is small against the
  decision: here ±0.8 to ±1.0 EUR/MWh with 496; the error falls with 1/√S.

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
- [ ] Stand-up update: *"Yesterday: joint weather and price scenarios; Everswinkel's fair price
      falls from 150 to 131 EUR/MWh once prices see the weather. Today: price the Borrentin
      PPA with its risk premium (PPA-7). Blockers: none."*

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
