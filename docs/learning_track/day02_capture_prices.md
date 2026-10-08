# Day 2: Capture prices and capture rates (ticket PPA-2)

> **Time needed:** about 5 hours. Concepts take 75 minutes, the code tour and the
> investigation stories 75 minutes, hands-on and exercises 2 hours, to-dos 30 minutes.
> **You will be able to:** explain why solar earns far less than the baseload price,
> compute capture prices and capture rates correctly at quarter-hour resolution,
> tie them out to the official German market values, and investigate a reconciliation
> difference like an analyst instead of hiding it behind a wider tolerance.

**Contents:** [0. Scenario](#0-the-scenario) ·
[1. Concepts](#1-concepts-you-need-today) ·
[2. Architecture](#2-what-was-built-architecture) ·
[3. Code tour](#3-code-tour) ·
[4. Investigations](#4-four-real-findings-and-how-they-were-investigated) ·
[5. Hands-on](#5-hands-on-run-it-yourself) ·
[6. Results](#6-results-what-the-data-says) ·
[7. Exercises](#7-exercises) ·
[8. Quiz](#8-self-check-quiz) ·
[9. Interview](#9-interview-corner) ·
[10. Real work](#10-how-this-maps-to-real-work-at-encavis) ·
[11. To-dos](#11-your-to-dos-for-day-2) ·
[12. Glossary](#12-glossary) ·
[13. Sources](#13-sources)

---

## 0. The scenario

Tuesday, week one. Your lead forwards a request from Origination:

> *"An industrial buyer wants a 10-year pay-as-produced PPA from one of our German
> solar parks. Before we talk numbers I need to know what solar actually earns on the
> spot market compared with baseload, and how fast that is getting worse. Please also
> show me that your numbers agree with the official Marktwert Solar, otherwise
> nobody will believe them. Ticket PPA-2."*

Why this matters in money: a pay-as-produced PPA delivers the park's profile, not a
flat band. The buyer receives energy mostly at sunny middays, exactly when the spot
price is lowest. The price a buyer is willing to pay, and the price you can defend, is
anchored on the **capture price**, not on the baseload forward. In 2025 the gap was
**43 EUR/MWh**. On a 100 GWh-per-year PPA that is **EUR 4.3 million per year** of
difference between "baseload thinking" and reality.

**Ticket PPA-2: acceptance criteria (all met today)**

- [x] Function `capture_price(prices, generation)` = volume-weighted price, with tests
      (flat profile gives capture rate 1; generation only in negative hours gives a
      negative capture price).
- [x] Monthly and annual capture prices and capture rates for solar, wind onshore and
      wind offshore, 2023 to Sep 2026.
- [x] 2025 solar capture price reconciled with the official Jahresmarktwert Solar
      4.508 ct/kWh: ours is 4.595 ct/kWh, inside the ±0.10 tolerance fixed in advance,
      and the remaining difference is explained (section 4.3).
- [x] Chart of capture rate by month and technology, with a written interpretation.
- [x] This learning-track page.

Delivered beyond the ticket: the reconciliation was extended to **all three
technologies for 2023 to 2025** and to **44 official monthly values**. That turned up
two real findings: a market-coupling incident on 26 June 2024, and a systematic
difference for wind that is now an open investigation.

---

## 1. Concepts you need today

### 1.1 Capture price and capture rate

A generator does not sell "on average". It sells each quarter-hour's energy at that
quarter-hour's price. What it earns per MWh over a period is the **volume-weighted
average price**, called the **capture price**:

```
                     sum over t of  price_t x energy_t
capture price  =  ---------------------------------------      [EUR/MWh]
                          sum over t of  energy_t

capture rate   =  capture price / baseload price                [dimensionless]
```

The **baseload price** is the plain time-weighted average price of the same period:
what a flat 1 MW band would earn. The capture rate is also called the **value
factor** or (in German) *relativer Marktwert*.

Worked example, four quarter-hours:

| Quarter-hour | Price (EUR/MWh) | Solar energy (MWh) | Price x energy |
|---|---|---|---|
| 11:00 | 10 | 300 | 3,000 |
| 11:15 | 100 | 100 | 10,000 |
| 11:30 | 10 | 300 | 3,000 |
| 11:45 | 100 | 100 | 10,000 |
| **Sum** | | **800** | **26,000** |

Baseload price = (10 + 100 + 10 + 100) / 4 = **55 EUR/MWh**.
Capture price = 26,000 / 800 = **32.5 EUR/MWh**. Capture rate = 32.5 / 55 = **0.59**.

The park produces most when the price is low, so it earns 41% less than baseload.
That is the whole idea, and it is exactly one of today's tests
(`test_capture_price_is_volume_weighted`).

Two limiting cases make good tests, and both are acceptance criteria:

- A **flat profile** (same energy every interval) earns exactly the baseload price:
  capture rate = 1.
- A profile that produces **only in negative-price intervals** has a negative capture
  price: it pays to deliver.

### 1.2 Why solar cannibalises itself

Recall the merit order from Day 1: renewables bid near zero and push expensive plants
out of the market. When the sun shines, **all** German solar parks produce at the same
time (the country is small compared with a weather system). Midday supply jumps, the
clearing price falls, and every solar park sells into that low price. The more solar
is installed, the deeper the midday dip. This is **cannibalisation**.

Wind is less affected because windy hours are spread over day and night and across
seasons, and offshore wind blows more steadily than onshore wind. The ranking in our
data is the textbook one:

| 2025 | Capture rate |
|---|---|
| Wind offshore | 0.96 |
| Wind onshore | 0.87 |
| Solar | 0.51 |

The cannibalisation chart (section 6) shows it directly: each month's solar capture
rate against solar's share of German load. The fitted slope is about **−0.20 capture
rate for every +10 percentage points of solar share**.

> **Real-world note:** solar capture rates are what made battery storage, east-west
> and vertical bifacial layouts, and "hybrid" PPAs (solar plus storage, or solar
> plus wind) commercially interesting. All of them move energy away from the midday
> dip.

### 1.3 The three risks inside a pay-as-produced PPA

When a buyer agrees to take the whole output at a fixed price, the seller hands over
(and the buyer takes on) three different risks. Keep them apart. Every later day in
this project prices one of them.

| Risk | Question | Measured by | Project day |
|---|---|---|---|
| **Price level** | Will baseload prices be high or low? | Forward curve, price simulation | 5-6 |
| **Profile (shape)** | How much less than baseload does this profile earn? | Capture rate | **2 (today)** |
| **Volume** | Will the park produce more or less than expected, and when? | Weather years, P50/P90 | 4, 6 |

The **profile cost** turns the capture rate into money:

```
profile cost = (baseload price - capture price) x energy
```

German solar in 2025: (89.32 − 45.95) EUR/MWh × 70.1 TWh ≈ **EUR 3.0 billion** less
than the same energy sold at baseload (exercise 3 asks you to compute it).

> **Pitfall:** pricing a pay-as-produced solar PPA off the baseload forward (for
> example "Cal-27 base minus a discount") without an explicit capture-rate assumption.
> A capture rate of 0.55 instead of 0.65 is 10% of the baseload price, which is often
> more than the whole margin of the deal.

### 1.4 The official market values (Marktwerte) and why they exist

The German TSOs publish, for every month, the **Monatsmarktwert (MW)** of solar, wind
onshore and wind offshore, and for every year the **Jahresmarktwert (JW)**. The legal
formula (EEG 2023, Anlage 1, Nr. 3.3 and 4.3) is, word for word, a capture price:

> For each quarter-hour, multiply the spot price by the energy produced according to
> the TSOs' online extrapolation; sum over the month (year); divide by total energy.

They exist because of the **sliding market premium** (*gleitende Marktprämie*). An
EEG plant in direct marketing earns the spot market plus a premium:

```
market premium = max(0, AW - MW)       AW = the plant's awarded value (anzulegender Wert)
```

If solar's market value falls, the premium rises and the EEG account pays more.
Since 2023, new plants are settled against the **annual** value JW instead of the
monthly one. For our project the official values are a gift: an **independent,
legally defined capture price** to reconcile against.

### 1.5 Negative prices and the "Vermarktungsmenge"

Under EEG §51, plants lose the market premium when prices are negative (since the
*Solarspitzengesetz* of February 2025, new plants lose it for **every** negative
quarter-hour). Direct marketers therefore curtail many plants when the price is
below zero. Two consequences:

- The share of energy produced at **non-negative** prices (*Vermarktungsmenge*) is a
  key business-case number. Rödl & Partner report 75% for solar and 90% for onshore
  wind in 2025. Our data gives 75.8% for solar.
- **Measured** generation is lower than **potential** generation in negative hours.
  Keep that in mind for section 4.2.

> **Real-world note:** a PPA must say what happens in negative hours. Common clauses:
> the buyer does not pay for energy delivered at negative prices, or the seller must
> curtail, or the buyer pays the fixed price regardless. Each one moves value between
> the parties, and you can now quantify it from `negative_price_share`.

### 1.6 Curtailment: market-driven and grid-driven

Two very different reasons why a wind or solar park produces less than it could:

| | Market-driven | Grid-driven (redispatch) |
|---|---|---|
| Trigger | Negative price | A congested line, typically north to south |
| Decided by | Direct marketer / operator | Grid operator |
| Typical victims | Solar and wind at sunny or windy weekends | Wind in the north, **offshore** wind |
| Compensation | None (that is the point) | Yes, the operator is compensated |
| Size | Grows with negative hours | About 10.5 TWh of renewables in 2023, 9.4 TWh in 2024, over 80% wind (BNetzA) |

Both remove energy from **low-price** hours, because they happen when there is too much
renewable power. That will matter a lot in section 4.2.

### 1.7 Weighting at the right resolution

Generation data is quarter-hourly for the whole period. Day-ahead prices were
**hourly until 30 Sep 2025** and are **quarter-hourly since 1 Oct 2025**. The legal
formula works per quarter-hour, so we put the price on the quarter-hour grid:

- Before 1 Oct 2025, the hourly price applies to each of its four quarter-hours. Because
  the price is constant within the hour, `sum(price x quarter-hour energy)` equals
  `price x hourly energy`. Hourly and quarter-hourly methods give **identical** results.
- After 1 Oct 2025, the four quarter-hours have **different** prices. Averaging prices
  and generation to hourly first throws away the intra-hour correlation between price
  and solar output, and the result changes (exercise 4).

> **Pitfall:** "forward-filling" prices onto a finer grid also fills **gaps**. If an
> hour is missing, a careless `ffill()` invents a price for it. `prices_on_grid` only
> assigns a price to a timestamp that lies inside a published delivery interval;
> everything else stays empty (`test_prices_on_grid_leaves_missing_hours_empty`).

---

## 2. What was built: architecture

```
data/processed/prices_native.parquet   (60 min until Sep 2025, 15 min since)
data/processed/power_15min.parquet     (15 min throughout)
                │
                ▼
analysis/capture.py
  prices_on_grid()        hourly price -> its four quarter-hours, gaps stay NaN
  capture_price()         sum(p x q) / sum(q) on one shared time grid
  capture_rate()          capture price / base price
  capture_table()         per local month or year x technology:
                          base, capture price, capture rate, TWh, share at negative prices
  reconciliation_metrics()  -> ct/kWh and % (the units the TSOs publish)
  load_market_values()    data/reference/netztransparenz_market_values_monthly.csv
  compare_monthly()       ours vs official, month by month
                │
                ├──► analysis/reconcile.py  reconcile() against config/project.toml
                │                           (status: within / explained / OUTSIDE)
                ▼
analysis/day02_report.py  ──►  reports/day02_capture_prices.md + 3 charts
cli.py: `ppa-lab capture` (also part of `ppa-lab all`)
```

Nothing new is downloaded today: Day 2 is pure analytics on the Day 1 datasets, plus
one small committed reference file with the official market values.

---

## 3. Code tour

### 3.1 `analysis/capture.py`: the formula, done carefully

**`capture_price(prices, generation)`** is four lines of maths and three lines of
protection:

- It **refuses two series on different time grids** (`ValueError: same time grid`).
  Hourly prices against quarter-hourly generation would silently align on the full
  hours only and drop three quarters of the energy. Failing loudly is better than a
  plausible wrong number.
- It ignores intervals where either value is missing.
- It **refuses a period without generation** (the capture price is undefined, not 0).

**`prices_on_grid(prices, grid)`** finds, for every quarter-hour of the generation
grid, the delivery interval that contains it, using `searchsorted` on the price
timestamps and each interval's length (`interval_min`, from Day 1). It is generic: it
works for 60-minute, 15-minute and mixed data, and leaves uncovered timestamps empty.

**`capture_table(prices, power, tz, freq)`** computes everything per **local**
calendar period (`freq="M"` or `"Y"`) and technology, as a tidy table with index
`(period, technology)`. Energy is computed as MW × interval length in hours, so the
same code would work at any resolution. Grouping uses local time because a "month" in
a contract is a local month: 31 Jan 23:30 UTC is already February in Berlin
(`test_capture_table_groups_by_local_month_not_utc_month`).

**`reconciliation_metrics(annual)`** converts to the publisher's units: EUR/MWh ÷ 10
= ct/kWh, and the non-negative share in %. Then Day 1's `reconcile()` is **reused
unchanged**: same function, new metrics.

### 3.2 `config/project.toml`: references with tolerances fixed in advance

Fifteen new `[[reconciliation]]` entries: the official JW for three technologies and
three years, the 2023/2024 spot values, and the Vermarktungsmenge figures. The
tolerance (**±0.10 ct/kWh = 1 EUR/MWh**) was written down **before** the comparison
was run.

> **Pitfall:** choosing the tolerance after seeing the difference. If you widen it
> until everything is green, the reconciliation has stopped measuring anything. The
> wind references are deliberately left **outside tolerance** (section 4.2).

`Reference` has a new optional field **`note`**. A difference beyond tolerance with a
documented cause is reported as **"explained difference"**; without one it stays
**"OUTSIDE tolerance"**. This is a mini *known-breaks register*, a standard tool in
finance reconciliations: it separates "we understand this" from "nobody has looked".

### 3.3 `data/reference/netztransparenz_market_values_monthly.csv`

44 months (Jan 2023 to Aug 2026) of official monthly values, with a commented header
recording the source, the retrieval date and the one correction the TSOs published
(May 2026 solar). It is small, public and versioned with the code, so the
reconciliation is reproducible offline.

### 3.4 `analysis/day02_report.py` and `analysis/plotting.py`

The report builds the annual table, the reconciliation table (with an automatic line
counting differences that are still unexplained), the monthly comparison summary, a
few computed findings and three charts. Only complete months and years are compared
with official values (`complete_months`, `complete_years`): a half month against an
official full month would be a false break.

The chart style moved from the Day 1 report into `plotting.py` so both reports share
one palette. Colours follow the **technology**, never its rank: solar is always
orange, onshore wind blue, offshore wind aqua.

### 3.5 Tests: what each one protects

| Test file | Protects against |
|---|---|
| `test_capture.py` (15 tests) | simple instead of weighted mean; mixed grids; gaps filled with invented prices; UTC instead of local months; wrong units in reconciliation |
| `test_reconcile.py` (+2) | a documented note hiding a difference that is within tolerance; status logic |
| `test_config.py` (+2) | a typo in a reference metric name turning it silently into "not available" |
| `test_day02_report.py` (4) | report crashes on short ranges, on many months, and the bug in section 4.4 |
| `test_cli.py` (+1) | `ppa-lab capture` and `ppa-lab all` produce the report |

Every key test was checked by **mutation**: a deliberate bug was planted (UTC months,
forward-fill across gaps, simple mean) and the matching test had to fail. A test that
cannot fail is decoration. 85 tests, 94% coverage.

---

## 4. Four real findings, and how they were investigated

### 4.1 The spot price is off in exactly one month: 26 June 2024

- **Symptom:** our 2024 average price is 78.51 EUR/MWh, the official JW 2024 is
  79.46 EUR/MWh (−0.95). For 2023 and 2025 we match to the cent.
- **Narrow it down first:** comparing 44 monthly spot values, **43 match to
  0.000 ct/kWh**. All of the 2024 difference is in **June 2024**: −1.156 ct/kWh,
  i.e. −11.56 EUR/MWh × 720 hours. That is too large for rounding and too
  concentrated for a definition issue: it smells like one specific day.
- **The event:** on 25 June 2024 EPEX SPOT had a technical problem and could not hand
  over its order books before the coupling deadline. SDAC was **partially
  decoupled** for delivery on **26 June 2024**. EPEX ran a local German auction that
  cleared at about **492 EUR/MWh** on average, while Nord Pool's German auction
  cleared at about **103 EUR/MWh**.
- **Our data:** the daily mean on 26 June 2024 in our dataset is **103.01 EUR/MWh**,
  i.e. the Nord Pool result.
- **The rule:** EEG §3 Nr. 42a defines the spot price as the coupled price, but
  *"if the order books are not or only partly coupled, the volume-weighted average
  price of all power exchanges"*. The TSOs used that weighted average. Back of the
  envelope: 11.56 × 720 / 24 ≈ 347 EUR/MWh extra for that day, so the official day
  average was about 450 EUR/MWh, which implies EPEX carried roughly 89% of the
  volume.
- **Resolution:** documented as an **explained difference** with a `note` in the
  config. The data is **not** patched: we don't have both exchanges' volumes, and
  inventing them would be worse than a documented, understood break.
- **Lesson:** a reconciliation break that sits in one month is a story about one
  event. Find the event before touching code.

### 4.2 Wind is always higher than the official value: an open investigation

- **Symptom:** our onshore capture price is above the official JW by 0.16 to
  0.29 ct/kWh and offshore by 0.36 to 0.49 ct/kWh, in **every** year. Monthly: onshore
  is higher in 43 of 44 months, offshore in 43 of 44. The spot price matches, and the
  formula is the same one that reproduces solar, so the **volumes** must differ.
- **Evidence collected:**
  1. The direction never changes: our wind volumes put **relatively less energy in
     cheap hours** than the TSOs' volumes.
  2. The gap is bigger in months with many negative hours (correlation 0.61 for
     onshore in the 44 months), e.g. April 2026: +1.43 (onshore), +1.65 (offshore).
  3. It does not vanish in months **without** negative prices (Feb 2023: offshore
     +0.74), and it is largest for **offshore**, the technology most affected by grid
     curtailment.
  4. Independent check: our share of onshore energy at non-negative prices is 92.4%
     in 2025 against 90% reported from TSO data; for solar we match (75.8% vs 75%).
- **Hypothesis:** our series (Energy-Charts / ENTSO-E actual generation) is
  **measured feed-in after curtailment**. The official values use the TSOs'
  **online extrapolation** (*Online-Hochrechnung*), which seems to keep more of the
  curtailed energy, both grid-driven (redispatch, every wind-rich low-price hour) and
  market-driven (negative prices). Removing energy from cheap hours raises the
  capture price, which is exactly the direction we see.
- **Plausibility:** how much extra cheap energy closes the gap? If the missing energy
  is valued at about 0 EUR/MWh, the 2025 gaps correspond to about 1.6 TWh offshore,
  4.0 TWh onshore and 1.4 TWh solar. Grid curtailment of renewables was about 10.5 TWh
  in 2023 and 9.4 TWh in 2024, mostly wind. Same order of magnitude: the hypothesis
  survives this test, but it is **not proven**.
- **Decision:** the wind references stay **"OUTSIDE tolerance"**. The definitive test
  is to download the TSOs' online extrapolation itself (netztransparenz.de API,
  free registration) and recompute; the gap should vanish. That is now a backlog item
  (PPA-2b).
- **What it means for pricing:** for a PPA the relevant volume is what the park can
  actually deliver and get paid for. A capture rate computed on curtailed actuals is
  closer to that than the official market value. For EEG premium calculations,
  however, the official value is the legally binding one. Know which number you need.

> **Interview gold:** "My reconciliation was green for solar and red for wind. I
> didn't widen the tolerance; I showed that the price side matches to the cent, so it
> must be the volumes, and I traced it to curtailment in the generation data. It's in
> the backlog with the test that would settle it."

### 4.3 Solar: inside tolerance, but the gap is growing

- 2023: +0.025, 2024: +0.024, 2025: **+0.087** ct/kWh. Monthly, 33 of 44 months are
  inside ±0.10, but spring 2026 is not: April +0.59, May +0.49.
- Same signature as wind: the months with the largest gaps are the months with the
  most negative hours (April 2026: 123 negative hours, 47% of solar energy at negative
  prices). Since the Solarspitzengesetz, many more solar plants curtail at negative
  prices, so "measured" and "extrapolated" solar diverge in exactly those hours.
- **Answer to the acceptance criterion:** 4.595 vs 4.508 ct/kWh (+1.9%) for 2025 is
  inside tolerance; the remaining difference is consistent with negative-price
  curtailment in the generation data, the same mechanism as in 4.2.

### 4.4 A bug that only real data found

- **Symptom:** all 83 tests were green, then `ppa-lab capture` on the real data
  crashed: `TypeError: unsupported format string passed to Period.__format__`.
- **Cause:** the report wrote `f"{month:%b %Y}"`. That works for timestamps, but a
  pandas `Period` does not accept format specs in f-strings. The two-day smoke test
  never reached that line, because two days contain no complete month to compare.
- **Fix, test-first:** the text was moved into `monthly_comparison_text()`, a new test
  with two hand-made months reproduced the exact error (red), then `strftime` fixed it
  (green). A second test now renders the two charts the smoke test skips.
- **Lesson:** coverage tells you which lines ran, not which situations were tested. Ask
  "what input does production see that my tests never do?"

A fifth, smaller finding: **official data gets corrected too.** The TSOs revised the
May 2026 solar market value from 3.163 to 3.296 ct/kWh after an error in their solar
extrapolation for 1 May 2026. The reference file stores the corrected value and says
so in its header. Reference data needs provenance, just like your own data.

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                 # 85 offline tests, about 2 seconds
make capture              # writes reports/day02_capture_prices.md and 3 charts
make report               # Day 1 report, now with the 2023/2024 spot references
open reports/day02_capture_prices.md
```

Explore interactively (`.venv/bin/python`):

```python
import pandas as pd
from ppa_lab.config import load_settings
from ppa_lab.analysis.capture import capture_table

s = load_settings()
prices = pd.read_parquet(s.processed_dir / "prices_native.parquet")
power = pd.read_parquet(s.processed_dir / "power_15min.parquet")

monthly = capture_table(prices, power, s.timezone, freq="M")
monthly.xs("solar", level="technology").loc["2025-04":"2025-09"].round(3)
```

Check yourself: the solar row for 2025-06 should show a capture price of about
20.01 EUR/MWh, a capture rate of 0.313, and 47% of the energy at negative prices.

Then play: `make notebook` opens `notebooks/ppa_lab_playground.ipynb`. The Day 2 section
(2.1 to 2.8) has the capture tables, the seasonality grid, cannibalisation for any
technology, the comparison with the official values, and a quarter-hour view of any
day (default: Easter Sunday 2026, when solar earned −62 EUR/MWh). Column meanings are
in `docs/data_dictionary.md`.

---

## 6. Results: what the data says

### 6.1 Annual capture prices (EUR/MWh) and capture rates

| Year | Base | Solar | Rate | Wind onshore | Rate | Wind offshore | Rate |
|---|---|---|---|---|---|---|---|
| 2023 | 95.18 | 72.25 | 0.759 | 78.44 | 0.824 | 86.56 | 0.910 |
| 2024 | 78.51 | 46.48 | 0.592 | 64.54 | 0.822 | 71.40 | 0.909 |
| 2025 | 89.32 | 45.95 | 0.514 | 77.27 | 0.865 | 85.53 | 0.958 |
| 2026 (Jan-Sep) | 107.72 | 55.68 | 0.517 | 95.37 | 0.885 | 101.65 | 0.944 |

Share of solar energy produced at negative prices: 8.3% (2023), 18.3% (2024),
24.2% (2025), 22.8% (2026 to September). Solar produced 76.2 TWh in the first nine
months of 2026, already more than in the whole of 2025 (70.1 TWh).

### 6.2 Reconciliation

| | 2023 | 2024 | 2025 | Status |
|---|---|---|---|---|
| Solar, ours − official (ct/kWh) | +0.025 | +0.024 | +0.087 | within ±0.10 |
| Wind onshore | +0.223 | +0.161 | +0.286 | outside, open (4.2) |
| Wind offshore | +0.469 | +0.363 | +0.494 | outside, open (4.2) |
| Spot (EUR/MWh) | 0.00 | −0.95 | 0.00 | 2024 explained (4.1) |

### 6.3 The charts

![Capture rate by month](../../reports/figures/day02_capture_rate_monthly.png)

![Difference to the official market values](../../reports/figures/day02_official_gap.png)

![Solar cannibalisation](../../reports/figures/day02_solar_cannibalisation.png)

### 6.4 Five stories in the data

1. **Solar lost a third of its relative value in two years.** The capture rate fell
   from 0.76 (2023) to 0.51 (2025) while solar output grew by 30%. 2026 so far is
   flat at 0.52, not better.
2. **The worst months are spring and early summer, not midsummer.** June 2025 (0.31)
   and April 2026 (0.24): lots of sun, moderate demand, mild weather, holidays. In
   April 2026 solar earned 19 EUR/MWh while baseload was 79 EUR/MWh.
3. **Winter solar is worth baseload.** December and January capture rates are about 1.0:
   there is little solar, it produces at the daily peak around noon, and there is no
   cannibalisation.
4. **Wind's capture rate improved** (onshore 0.82 to 0.87 from 2024 to 2025), partly
   because solar now depresses the *midday* hours, which makes the windy evening and
   night hours relatively more valuable.
5. **The summer 2026 points sit above the cannibalisation line** (June 2026: 0.58 at
   a 32% solar share, where the fit predicts below 0.4). Higher baseload prices and more flexible demand and storage
   soaking up midday energy are candidate explanations; worth watching before
   extrapolating the trend.

### 6.5 What this means for pricing a solar PPA

A first, deliberately simple fair price for a pay-as-produced solar PPA is

```
PPA price  ≈  forward baseload price  x  expected capture rate  -  risk premia
```

Illustration (not a quote): with a forward baseload price of 85 EUR/MWh and an
expected capture rate of 0.55, the profile-adjusted value is about 47 EUR/MWh before
volume and price risk premia. Day 3 writes this maths properly; Days 5 to 7 replace
"expected capture rate" by a distribution from simulated prices and weather.

---

## 7. Exercises

**Warm-up (in `exercises/day02_capture.py`, checked by `.venv/bin/pytest exercises -q`)**

1. **One capture price by hand.** Solar, July 2024, from the hourly files. Compare with
   the official 3.554 ct/kWh.
2. **Energy at negative prices.** Solar 2023 to 2025. How fast is it growing?
3. **Profile cost.** In EUR billion, for German solar 2023 to 2025.
4. **Written:** hourly vs quarter-hourly. Why does the hourly method give 46.07 instead
   of 45.95 EUR/MWh for solar 2025, but exactly the same number for 2024?

**Core**

5. **EEG §51 view (test first).** Write `capture_price_nonnegative(prices, generation)`
   that ignores intervals with negative prices (energy and revenue). This is what a
   plant that curtails at negative prices earns per MWh produced. Write the failing
   test in `tests/test_capture.py` first. How much higher is solar 2025?
6. **Seasonality table.** Average solar capture rate by calendar month (Jan to Dec)
   over 2023 to 2025. Which months would you avoid in a seasonal PPA?
7. **Peak vs solar.** Compare the 2025 solar capture price with the 2025 peak price
   (Day 1 exercise 1). Why is the "peak" product a poor hedge for solar today?

**Stretch**

8. **Settle the wind question.** Register for the netztransparenz.de API, download the
   online extrapolation of wind onshore for one month and recompute the capture price
   with it. Does the gap to the official value vanish?
9. **Battery thought experiment.** Shift 20% of each day's solar energy from the
   cheapest 4 hours to the most expensive 4 hours of the same day (ignore losses).
   What is the new 2025 capture rate? What is that worth per MWh?

<details>
<summary>Hints and solution sketches</summary>

1. `p = prices.tz_convert(TZ).loc["2024-07", "price_eur_mwh"]`, same for `power`;
   `(p * g).sum() / g.sum()` ≈ 35.82 EUR/MWh, +0.28 against the official value: the
   generation-data difference from section 4.3.
2. About 8.3%, 18.3% and 24.2%: roughly tripled in two years.
3. About 1.24, 1.91 and 3.03 billion EUR.
4. Until 30 Sep 2025 each hour has one price, so the hourly sum of price x energy is
   exact. From 1 Oct 2025 the four quarter-hours of an hour have different prices;
   averaging first loses the covariance between price and output within the hour. The
   TSOs and our report use quarter-hours, as the law prescribes.
5. Mask with `prices >= 0` before the sums; solar 2025 rises from 45.95 to about
   65 EUR/MWh, at the cost of 24% less energy sold.
6. Group the monthly table by `period.month`; April to August are the weakest.
7. Peak (08:00-20:00 weekdays) still contains the evening ramp, which solar does not
   produce into, while solar also produces at weekends. A peak hedge leaves you short
   exactly when solar is long, and vice versa.
8. Compare month by month as in `compare_monthly`; if the gap disappears the
   curtailment hypothesis is confirmed and the note can be added to the references.
9. Per local day: sort hours by price, move energy, recompute; this is an upper bound
   on what a 4-hour battery adds.

</details>

---

## 8. Self-check quiz

1. Define capture price and capture rate in one sentence each.
2. Why is a simple mean of prices in hours with solar output **not** the capture price?
3. What is the capture rate of a perfectly flat profile, and why?
4. Why does solar cannibalise itself more than offshore wind?
5. Which three risks does a buyer take in a pay-as-produced PPA, and which one did we
   measure today?
6. What is the Jahresmarktwert Solar, who publishes it, and what is it used for?
7. Why must prices be put on the quarter-hour grid, and what changed on 1 Oct 2025?
8. What happened on 26 June 2024, and which price does EEG §3 Nr. 42a then prescribe?
9. Our wind capture prices are above the official ones. Give the hypothesis and the
   test that would confirm it.
10. Why is the tolerance written down before the comparison, and what does
    "explained difference" mean in our reconciliation?

<details>
<summary>Answers</summary>

1. Capture price: energy-weighted average price earned by a profile. Capture rate:
   capture price divided by the time-weighted baseload price of the same period.
2. A simple mean gives a quarter-hour with 10 MWh the same weight as one with
   10,000 MWh; the capture price weights each price by the energy sold at it.
3. Exactly 1: with equal energy in every interval, the energy weights are equal, so the
   weighted mean equals the time-weighted mean.
4. All German solar produces at the same hours (midday, sunny days), while offshore
   wind produces more evenly over day, night and seasons.
5. Price level, profile (shape), volume. Today: profile, through the capture rate.
6. The official annual capture price of solar (volume-weighted spot price with the
   TSOs' extrapolated generation), published by the four TSOs on netztransparenz.de;
   it sets the market premium (AW − JW) for EEG plants commissioned since 2023.
7. Generation is quarter-hourly and the law weights per quarter-hour. Since 1 Oct 2025
   day-ahead prices are quarter-hourly, so averaging to hours would lose information.
8. SDAC was partially decoupled after an EPEX technical problem; EPEX cleared about
   492, Nord Pool about 103 EUR/MWh. The law prescribes the volume-weighted average of
   all exchanges for that period.
9. Our generation is measured after curtailment (redispatch and negative prices), the
   official values use the TSOs' online extrapolation that keeps more of that energy;
   less energy in cheap hours means a higher capture price. Test: recompute with the
   TSOs' extrapolated series; the gap should vanish.
10. So the result cannot influence the yardstick. "Explained" means the difference is
    beyond tolerance but its cause has been found and documented (the `note`); it is
    not the same as "within tolerance".

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* to price a solar PPA you need to know what solar really earns, not the
> baseload price. *Task:* compute capture prices and rates for German solar and wind,
> 2023 to 2026, and prove them against the official market values. *Action:* I
> implemented the legal quarter-hour formula, handled the switch from hourly to
> 15-minute prices, and reconciled against all nine official annual values and 44
> monthly values with tolerances fixed in advance. *Result:* solar matches within
> 0.1 ct/kWh; I traced the only spot-price break to the SDAC decoupling of
> 26 June 2024; and I found a systematic wind difference that I attribute to
> curtailment in measured generation, documented as an open item with the test that
> would settle it. Solar's capture rate fell from 0.76 to 0.51 in two years, about
> 3 billion euros of profile cost in 2025.

**Likely questions and strong answers:**

- *"What is a capture rate and why does it matter for a PPA?"* The ratio of what a
  profile earns to baseload. It converts a baseload forward into a profile-adjusted
  value, and its uncertainty is a large part of the risk premium.
- *"How would you forecast solar capture rates?"* Fundamentally (more solar,
  batteries, demand flexibility, interconnection) and statistically (relationship to
  solar share, as in our cannibalisation chart), then simulate jointly with prices and
  weather instead of using one number.
- *"Your numbers don't match the official ones. Which is right?"* Both, for different
  questions: the official value is legally binding for the EEG premium; for what a
  specific park earns, I need its own (curtailed) delivery. The point is to know which
  number a decision needs.
- *"How do negative prices change PPA terms?"* They create explicit clauses: who bears
  negative hours, curtailment obligations, and whether the buyer pays for energy
  delivered at negative prices. With 24% of solar energy at negative prices in 2025,
  that clause is worth several EUR/MWh.

---

## 10. How this maps to real work at Encavis

| In this project | In a company |
|---|---|
| National solar and wind profiles | Each park's metered or forecast profile; portfolio aggregation |
| Official market values as a check | Settlement data from direct marketers, invoices, EEG statements |
| `capture_table` by month | Monthly revenue reporting and budget-vs-actual by asset |
| Profile cost | Shape and profile discounts in PPA term sheets |
| `negative_price_share` | Negative-price clauses, curtailment strategy, battery business cases |
| Known-breaks register (`note`) | Reconciliation sign-off with documented breaks before a pricing run |
| PPA-2b backlog item | An investigation ticket with owner and due date |

Encavis runs solar and wind across Europe and sells power through PPAs and direct
marketing. Capture rates per country and technology are inputs to every PPA offer and
every asset valuation; this day is that analysis for Germany.

---

## 11. Your to-dos for Day 2

- [ ] **CI chore first (still open from Day 1):** in `.github/workflows/ci.yml` set
      `runs-on: ubuntu-24.04`, upgrade the actions as agreed, commit
      `chore(ci): ...`, push, and check that CI is green without warnings.
- [ ] Read sections 1 and 4 with notes; redo the worked example in 1.1 on paper.
- [ ] Run section 5 and compare your numbers with section 6.
- [ ] Exercises 1 to 4 today; 5 to 7 tomorrow morning.
- [ ] **Commit Day 2** (commands below), then watch CI.
- [ ] **German vocabulary of the day:** der Marktwert / Monatsmarktwert /
      Jahresmarktwert, die Marktprämie, der anzulegende Wert, die Direktvermarktung,
      die Abregelung, das Netzengpassmanagement, die Hochrechnung, die
      Vermarktungsmenge, der Kannibalisierungseffekt, die Entkopplung (der Märkte).
- [ ] Stand-up update:
      *"Yesterday: capture prices for solar and wind 2023 to 2026, reconciled with the
      official market values; solar within 0.1 ct/kWh; one spot break explained by the
      June 2024 decoupling; wind difference open, likely curtailment. Today: PPA
      pricing maths (PPA-3). Blockers: none."*

Commit (stage files by name, never `.env`):

```bash
cd ".../Encavis quantitative/ppa-lab"
git status                          # check: no .env, no ' M .env.example'
git add src/ppa_lab/analysis/capture.py src/ppa_lab/analysis/day02_report.py \
        src/ppa_lab/analysis/plotting.py src/ppa_lab/analysis/day01_report.py \
        src/ppa_lab/analysis/reconcile.py src/ppa_lab/config.py src/ppa_lab/cli.py \
        src/ppa_lab/__init__.py pyproject.toml \
        config/project.toml data/reference/ Makefile \
        tests/test_capture.py tests/test_day02_report.py tests/test_reconcile.py \
        tests/test_config.py tests/test_cli.py \
        exercises/day02_capture.py exercises/test_day02_capture.py \
        notebooks/ppa_lab_playground.ipynb .gitignore \
        reports/ docs/ README.md CHANGELOG.md
git status                          # review once more
git commit -m "feat(analysis): capture prices and rates, reconciled with official market values (PPA-2)"
git push
gh run watch
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Capture price | Energy-weighted average price earned by a generation profile |
| Capture rate / value factor | Capture price divided by the baseload price |
| Baseload price | Time-weighted average price; what a flat band earns |
| Profile cost | (Baseload − capture price) × energy |
| Cannibalisation | Renewables depressing the price in the hours they produce |
| Pay-as-produced PPA | The buyer takes the actual output at a fixed price |
| Marktwert (MW / JW) | Official monthly / annual capture price per technology (EEG) |
| Market premium | AW − market value, paid to EEG plants in direct marketing |
| Vermarktungsmenge | Share of energy produced at non-negative prices |
| Redispatch | Grid operator changes plant output to relieve congestion |
| Online-Hochrechnung | TSOs' real-time extrapolation of wind and solar generation |
| Decoupling | SDAC fails to couple all order books; exchanges clear separately |
| Known-breaks register | List of reconciliation differences with documented causes |

## 13. Sources

- EEG 2023, Anlage 1 (calculation of market values) and §3 Nr. 42a (spot price
  definition, decoupling rule), gesetze-im-internet.de
- netztransparenz.de, Marktwertübersicht: monthly and annual market values 2023 to
  2026, retrieved 8 Oct 2026, including the May 2026 solar correction notice
- Rödl & Partner, "Wind + Sonne = Strom", February 2026: market values 2025, PV and
  onshore Vermarktungsmenge 2024/2025
- EPEX SPOT statement on the partial decoupling, 26 June 2024; ICIS, 25 June 2024
  (EPEX 492.04 vs Nord Pool 103.01 EUR/MWh for Germany)
- Bundesnetzagentur, network congestion management statistics 2023 and 2024
  (renewable curtailment 10.5 TWh and 9.4 TWh), as reported by Tagesspiegel
  Background and the Bavarian state parliament
- DGS, Jahres- und Monatsmarktwerte Solar 2025 (January 2026)
