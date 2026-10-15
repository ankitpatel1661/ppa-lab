# Step 3: PPA structures and pricing maths (ticket PPA-3)

> **Sites and numbers on this page (update for v1.3).** This page was written for two
> illustrative parks (a 50 MWp solar park in Lusatia, a 30 MW wind park in North Frisia).
> Since v1.3 the project models two Encavis parks from public data: the Borrentin solar park
> (114 MWp, Mecklenburg-Western Pomerania) and the Everswinkel wind park (28.5 MW, North
> Rhine-Westphalia). The methods and lessons are unchanged; current numbers are in the
> reports and the README, and the exercise checks use the current data.

> **Time needed:** about 5 hours. Concepts take 90 minutes, code tour and findings
> 60 minutes, hands-on, notebook and exercises 2 hours, to-dos 30 minutes.
> **You will be able to:** write down the cash flows of every common PPA structure,
> explain which risk each one moves from producer to buyer, compute fair (break-even)
> prices, and back-test the structures on real data without fooling yourself about risk.

**Contents:** [0. Scenario](#0-the-scenario) ·
[1. Concepts](#1-concepts-you-need-today) ·
[2. Architecture](#2-what-was-built-architecture) ·
[3. Code tour](#3-code-tour) ·
[4. Findings](#4-four-real-findings) ·
[5. Hands-on](#5-hands-on-run-it-yourself) ·
[6. Results](#6-results-what-the-back-test-says) ·
[7. Exercises](#7-exercises) ·
[8. Quiz](#8-self-check-quiz) ·
[9. Interview](#9-interview-corner) ·
[10. Real work](#10-how-this-maps-to-real-work-at-encavis) ·
[11. To-dos](#11-your-to-dos-for-step-3) ·
[12. Glossary](#12-glossary) ·
[13. Sources](#13-sources)

---

## 0. The scenario

Wednesday. Origination comes back:

> *"The buyer for the 50 MW solar park wants options, not one price. Give me the
> economics of a pay-as-produced PPA, a baseload PPA, and a virtual PPA with a floor,
> plus the negative-price clause they keep asking about. And Risk wants a written
> methodology before anything goes to the credit committee. Ticket PPA-3."*

Two things are being asked. First, **structures**: who pays whom, when, and which risk
each party carries. Second, a **methodology**: the maths written down so that Risk,
Finance and the buyer can check it. Every number in the rest of this project is a cash
flow of one of today's structures, evaluated on history today and on thousands of
simulated futures from Step 6 on.

**Ticket PPA-3: acceptance criteria (all met today)**

- [x] `pricing/contracts.py`: cash flows per interval for merchant, pay-as-produced
      (with and without a negative-price clause), virtual PPA (CfD), floor / cap /
      collar and baseload PPA; fair prices with discounting.
- [x] Works on one history (pandas) and on many scenarios (NumPy arrays), for Step 7.
- [x] Tests for the pricing invariants: a floor never lowers value, a CfD removes price
      risk, a baseload PPA is merchant plus a swap, the break-even strike is the
      capture price, and the fair price is a ratio of expectations.
- [x] `METHODOLOGY.md` version 0: formulas, conventions, assumptions and limitations.
- [x] Back-test 2024-2025 for a 50 MW solar and a 30 MW wind park, strikes fixed from
      the previous year, with plan and surprise per structure (`ppa-lab ppa`).
- [x] Learning page, notebook section, exercises.

---

## 1. Concepts you need today

### 1.1 What a PPA is, in one paragraph

A power purchase agreement is a long-term contract (typically 5-15 years) between a
producer and a buyer (a utility, a trader, or a corporate such as a chemicals or
data-centre company) to sell electricity at an agreed price. The producer gets
**bankable revenue** to finance the plant; the buyer gets **price certainty** and,
with guarantees of origin, a credible green-power claim. A **physical** PPA delivers
the energy (through balancing groups); a **virtual** (financial) PPA only settles a
price difference while both sides keep trading on the spot market.

### 1.2 The cash flows, from the producer's side

Everything in `pricing/contracts.py` is one line of this table. P = spot price,
q = energy produced in the interval, K = fixed price, B = band, F = floor, C = cap.

| Structure | Cash flow per interval | Risk left with the producer |
|---|---|---|
| Merchant | q · P | price level, shape, volume |
| Pay-as-produced (PaP) PPA | K · q | volume |
| PaP, no payment at negative prices | K · q, only when P ≥ 0 | volume, negative-price frequency |
| Virtual PPA (CfD) | q · P + (K − P) · q = K · q | volume (and basis) |
| Floor | q · max(P, F) | upside price, shape; downside capped |
| Cap | q · min(P, C) | downside price; upside sold |
| Collar | q · clip(P, F, C) | price only inside [F, C] |
| Baseload PPA | K_B · B + (q − B) · P | **shape** and volume |

Work through the running example from `tests/test_contracts.py` by hand. Four intervals,
a solar-like profile that produces in the cheap ones:

| | t1 | t2 | t3 | t4 | Total |
|---|---|---|---|---|---|
| Price P (EUR/MWh) | 50 | −10 | 100 | 20 | base 40 |
| Energy q (MWh) | 2 | 4 | 0 | 4 | 10 |
| Merchant q·P | 100 | −40 | 0 | 80 | **140** (capture 14) |
| PaP at 30 | 60 | 120 | 0 | 120 | 300 |
| PaP at 30, no pay below 0 | 60 | 0 | 0 | 120 | 180 |
| Floor 0: q·max(P, 0) | 100 | 0 | 0 | 80 | 180 |
| Baseload at 40, B = 2.5 | 75 | 85 | −150 | 130 | **140** |

Look at t3: the baseload seller must deliver 2.5 MWh it does not have, buys it at
100 EUR/MWh and pays 150 EUR net. That single cell is the essence of shape risk.

### 1.3 Pay-as-produced: the buyer takes price and shape

Under a PaP PPA the buyer takes every MWh the plant produces, whenever it produces, at K.
The producer's revenue is K · (total energy): **no price risk and no shape risk left**,
only volume risk (a poor solar year means less energy at the same K).

The buyer's view is the mirror image: it pays K for energy worth P at that moment, so
its gain per MWh against buying on the spot market is (P − K). Buying solar-shaped
energy at a fixed price means the buyer owns the cannibalisation problem from Step 2.
That is why the fair PaP price is the **capture price**, not the base price.

### 1.4 Baseload PPA: fixed level, but the shape stays with you

A baseload PPA promises a constant band B every hour. The solar park produces more than
B at midday in summer (it sells the surplus at low prices) and less than B at night and
in winter (it buys the shortfall, often at high prices). Rearranging the cash flow:

```
K_B · B + (q − B) · P   =   q · P   +   B · (K_B − P)
   baseload PPA             merchant     baseload swap
```

**A baseload PPA is merchant revenue plus a fixed-for-floating swap on a flat band.**
It fixes the price *level* of the band, but the producer still earns its own capture
price on its own profile. If base prices rise while solar's capture rate falls, the
swap loses and the merchant leg does not make it up. That is exactly what happened to
the solar park in 2025 (section 4.2).

> **Interview:** "Why is a baseload PPA priced differently?" Because the producer must
> buy its shortfalls at whatever the market charges, and for solar those hours are the
> expensive ones: volume and price are negatively correlated. The residual position is
> short the shape, and the producer prices that risk in.

### 1.5 Virtual PPA: a CfD that settles the difference

In a virtual PPA nothing is delivered. The producer sells on the spot market as usual,
and the two parties settle (K − P) · q: the buyer pays when the price is below K and
receives when it is above. Net for the producer: K · q, the same as a physical PaP.

What differs is not the economics but the plumbing:

- **Basis risk:** the settlement uses a reference price (here the DE-LU day-ahead price)
  that may differ from the price the plant actually achieves (intraday, imbalance,
  other bidding zones in multi-country deals).
- **Accounting:** a contract that settles net in cash can count as a derivative and
  may need fair-value accounting; physical PPAs often fall under an own-use exemption.
  Finance will ask about it.
- **Volume definition:** "as produced" (our case), "baseload volume", or a shaped profile.

### 1.6 Floors, caps and collars are options

A floor F pays max(F − P, 0) per MWh: the producer owns a strip of **put options**, one
per interval. A cap C costs the producer max(P − C, 0) per MWh: it **sells calls**. A
collar combines both; a **zero-cost collar** chooses F and C so that the premium paid for
the floor equals the premium received for the cap.

Two things to remember:

- **A floor at 0 EUR/MWh is the right to curtail.** A plant that can switch off when the
  price is negative earns q · max(P, 0), exactly the cash flow of owning a 0-strike floor.
  Flexibility is an option, and options have value.
- **Option payoffs are convex.** Raising a floor by 10 EUR/MWh adds more and more value as
  the floor moves into the bulk of the price distribution (exercise 2 shows the curve).
  This is why Step 7 needs Monte Carlo: the value depends on the whole distribution, not
  on the average price.

Today's cash flows show the **payoffs** only. What the option **costs** (its premium)
is its expected discounted payoff over simulated scenarios, which comes in Step 7.

### 1.7 Negative-price clauses

With 24% of solar energy produced at negative prices in 2025 (Step 2), every term sheet
says what happens then. The common version: the buyer **does not pay** for energy produced
while the price is below zero, and the producer curtails. For the producer that removes
a slice of paid volume, so the strike must go up to stay whole. How much is exercise 3;
spoiler: much more for solar than for wind, for the reason you saw in Step 2. A price of
exactly zero is still paid: EEG §51 and typical clauses refer to prices *below* zero
(`test_a_price_of_exactly_zero_is_not_negative`).

### 1.8 Fair prices: the maths in three lines

The fair (break-even) strike makes the contract worth the same as selling at spot, in
expectation over scenarios (price paths and weather years), with discount factors D:

```
K*    = E[ sum_t D_t · q_t · P_t ] / E[ sum_t D_t · q_t ]       pay-as-produced
K_B*  = E[ sum_t D_t · P_t ]       / sum_t D_t                  baseload
D_t   = (1 + r) ^ (−years from the valuation date)
```

Two traps, both tested:

- K* is a **ratio of expectations**, not the average of each scenario's capture price:
  a windy year with lots of energy weighs more than a calm one
  (`test_fair_price_is_a_ratio_of_expectations_not_an_average_of_ratios`).
- With one history and no discounting, K* is the capture price and K_B* the base price,
  and at those strikes every structure earns exactly the merchant revenue in total
  (`test_at_the_fair_price_every_structure_earns_the_merchant_revenue_in_total`).

Why the capture price sits below the base price, in one identity (METHODOLOGY.md §2):

```
capture price = base price + Cov(q, P) / mean(q)
```

Solar output and price move in opposite directions, the covariance is negative, and the
capture price falls below base. Step 2's cannibalisation chart is this covariance.

From a market quote to an offer, the stack your preparation guide sketches (Figure 5):

```
PaP price ≈ baseload forward × expected capture rate
            − profile & volume risk premium − negative prices & curtailment
            − balancing & route to market − credit & liquidity
e.g.  85 × 0.55 ≈ 47  − 3 − 1.5 − 1.5 − 1  ≈ 40 EUR/MWh   (illustrative only)
```

Today implements the first term on history; Steps 5-7 replace "expected capture rate"
by a simulated distribution and compute the premia.

---

## 2. What was built: architecture

```
data/processed/prices_native.parquet  ─┐
data/processed/power_15min.parquet    ─┤
                                        ▼
analysis/capture.py: prices_on_grid()   (Step 2: prices on the 15-min grid)
                                        │
pricing/backtest.py                     ▼
  park_energy()   national profile → 50 MW solar / 30 MW wind, scaled per year
  backtest()      strikes from Y−1, cash flows in Y, plan = same terms on Y−1
  summarise()     revenue, per MWh, vs merchant, plan, surprise, worst month
        │ uses
        ▼
pricing/contracts.py   merchant · pay_as_produced · cfd · collar · baseload
                       fair_pay_as_produced_price · fair_baseload_price · discount_factors
        │
        ▼
analysis/step03_report.py → reports/step03_ppa_structures.md + 2 charts   (`ppa-lab ppa`)
METHODOLOGY.md            the maths, conventions, assumptions and limitations (v0)
config/project.toml       [pricing]: parks, delivery years, floor
```

---

## 3. Code tour

### 3.1 `pricing/contracts.py`: one line per structure, on purpose

- **Cash flows per interval, not totals.** Each function returns an array (or Series)
  shaped like its inputs. The caller decides how to aggregate: by month for a report,
  by year for a back-test, by scenario for Monte Carlo. One function, three uses.
- **pandas or NumPy.** A Series in gives a Series out with the same index (so you can
  `groupby` months); arrays of shape (scenarios, intervals) work unchanged for Step 7.
- **Refuses mismatched time grids.** pandas aligns two Series on their index and fills
  gaps with NaN without a word. A one-hour shift (a time-zone bug) would silently
  produce NaN sums. `_check_same_grid` raises instead
  (`test_contracts_refuse_series_on_different_time_grids`).
- **Producer perspective everywhere.** One sign convention, stated in the module
  docstring and in METHODOLOGY.md. Mixing buyer and seller signs is a classic source of
  "the PPA is worth minus three million" surprises.
- **No premiums inside cash flows.** A floor's cash flow is its payoff; what it costs is
  a separate valuation question.

### 3.2 `pricing/backtest.py`: an honest back-test

- **`park_energy`** scales the national profile per year to capacity × full-load hours.
  Scaling per year removes the national fleet's growth (solar grew 30% from 2023 to
  2025), which a single park would not see, but keeps the real hour-by-hour shape.
- **No hindsight.** Strikes for year Y come from year Y−1 only
  (`test_strikes_are_fixed_at_the_previous_years_outcome`; a mutation that used the
  delivery year itself was caught).
- **Plan and surprise.** The plan applies the same contract terms to Y−1's prices and
  profile: what the producer expected when it signed. Realised minus plan is the risk
  the structure left with it. Section 4.1 explains why this replaced a first idea.

### 3.3 Configuration and command line

`config/project.toml` has a new `[pricing]` section: the two parks, the delivery years
and the floor. The config loader checks that each delivery year **and the year before**
are complete years inside the data range, and fails early otherwise. `ppa-lab ppa`
writes the report; inside `ppa-lab all` it **skips with a warning** when the data range
is too short (the two-day test fixtures), instead of breaking the whole pipeline.

### 3.4 Tests: what each protects

| Test file | Protects against |
|---|---|
| `test_contracts.py` (18) | floor coded as a cap; baseload residual with the wrong sign; average of ratios instead of ratio of expectations; zero price treated as negative; silent NaNs from misaligned indexes |
| `test_backtest.py` (8) | hindsight strikes; one scale factor for all years; wrong plan; wrong units |
| `test_step03_report.py` (1) | the full report on two synthetic years (all charts and tables) |
| `test_config.py` (+2), `test_cli.py` (+1) | invalid delivery years; `ppa` command and graceful skip in `all` |

Each key test was checked by mutation: the planted bug had to make it fail.

---

## 4. Four real findings

### 4.1 My first risk metric was wrong, and the data said so

- **First version:** the report showed the standard deviation of monthly revenue within
  each year as "risk".
- **Symptom:** for the solar park the pay-as-produced PPA came out **riskier** than
  merchant (monthly std 111k vs 71k EUR in 2025). A fixed-price contract cannot carry
  more price risk than the spot market. Something was measuring the wrong thing.
- **Diagnosis:** the spread across months within a year is mostly **seasonality**. Under
  a PaP PPA, revenue follows volume: big in summer, small in winter. Merchant revenue
  is smoother because the high summer volume meets low summer prices (a natural hedge).
  Seasonality is known in advance: it is a liquidity topic, not risk.
- **Fix:** risk is the **surprise against what you expected** when signing. The plan
  applies the structure to the previous year at the same terms; the surprise is
  realised − plan. Result: the PaP PPA has a surprise of exactly 0.00 EUR/MWh in every
  case, as it should. The monthly chart stays in the report, relabelled "seasonality
  and liquidity".
- **Lesson:** when a number contradicts what the contract obviously does, question the
  metric before the contract. In an interview this is worth more than any formula.

### 4.2 Same baseload PPA, opposite outcomes

Both parks signed a 2025 baseload PPA at 78.51 EUR/MWh (the 2024 base price). The 2025
base came in at 89.32, so the swap leg lost 10.81 EUR/MWh for both. But:

| 2025 | Merchant surprise | Swap leg | Baseload surprise |
|---|---|---|---|
| Solar park | −0.53 | −10.81 | **−11.34** |
| Wind park | +12.73 | −10.81 | **+1.92** |

Why is explained in exercise 4: write it yourself before you look at the notebook.

### 4.3 A baseload seller can have negative months

The solar park's baseload PPA had a **negative month in January 2025** (−24k EUR): the
band had to be delivered while the park produced almost nothing, and the shortfall was
bought at winter prices. For a project company with a debt service schedule, a negative
cash month is a real problem even if the year is fine. That is why lenders look at
monthly cash flows and why "worst month" is in the report.

### 4.4 Small ones

- NumPy 2 removed the `ndarray.ptp()` method; `np.ptp(array)` is the replacement.
- The two-day CLI test exposed a design question: should `ppa-lab all` fail when the data
  cannot support a back-test? No: it skips Step 3 with a clear warning, and the config
  validator catches impossible delivery years in real configurations.

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                  # 115 offline tests
make ppa                   # reports/step03_ppa_structures.md + 2 charts
open METHODOLOGY.md        # the maths, rendered on GitHub
make notebook              # Step 3 section: 3.1 to 3.6, then your solutions
```

In the notebook, start with 3.1 (the running example as a table), then play with 3.2
(one day, every structure, quarter by quarter) and 3.5 (your own contract terms).

---

## 6. Results: what the back-test says

### 6.1 Revenue per MWh produced, by structure (EUR/MWh)

| Park, year | Merchant | PaP | PaP, no pay < 0 | Baseload | Merchant + floor 0 |
|---|---|---|---|---|---|
| Solar 2024 (strikes 72.25 / 95.18) | 46.48 | **72.25** | 59.04 | 63.14 | 49.26 |
| Solar 2025 (strikes 46.48 / 78.51) | 45.95 | 46.48 | 35.22 | **35.14** | 49.25 |
| Wind 2024 (strikes 78.44 / 95.18) | 64.54 | 78.44 | 73.50 | **81.20** | 65.03 |
| Wind 2025 (strikes 64.54 / 78.51) | **77.27** | 64.54 | 59.63 | 66.46 | 77.71 |

![Revenue per MWh by structure](../../reports/figures/step03_structures_annual.png)

![Monthly revenue of the solar park](../../reports/figures/step03_structures_monthly.png)

### 6.2 Five stories

1. **Fixing a price is a bet on direction, even when it is "fair".** Signed at the 2023
   capture price, the solar PaP PPA earned 72.25 in 2024 against 46.48 merchant:
   +EUR 1.3 million for the 50 MW park. The wind PaP signed at the 2024 capture price
   gave up 12.73 EUR/MWh in 2025 when prices recovered. The PPA did its job both times:
   it removed the surprise. Whether it "won" is hindsight.
2. **The negative-price clause is expensive for solar.** In 2025 it cut the solar PaP
   from 46.48 to 35.22 EUR/MWh, a loss of 11.26 EUR/MWh: 24% of the energy was not paid.
   For wind it cost 4.91. A clause like this must be priced into the strike.
3. **Curtailment is worth real money.** A floor at 0 (or simply switching off at negative
   prices) added 3.30 EUR/MWh for solar in 2025 and 0.44 for wind.
4. **Baseload hedges the level, not the shape.** Solar 2025: −11.34 EUR/MWh surprise under
   the baseload PPA, worse than merchant (−0.53). The level rose, solar's share of it did
   not (section 4.2).
5. **Liquidity is not the same as value.** The solar baseload PPA had a negative month
   (January 2025); the PaP PPA had its weakest months in winter; merchant in spring. Lenders
   care about all three.

### 6.3 What this means for pricing the solar PPA

The fair PaP price is anchored on the capture price (about 46 EUR/MWh on 2024-2025 data),
not on the base price (78-89). A negative-price clause raises the break-even strike
substantially, and a baseload structure leaves the producer short the shape: if the buyer
wants a baseload product from a solar park, the producer must charge for that risk or
firm the profile (storage, a wind portfolio, or buying back shape on the market). Step 7
puts numbers on these risk premia.

---

## 7. Exercises

**Warm-up (in `exercises/step03_ppa.py`, checked by `.venv/bin/pytest exercises -q`)**

1. **A baseload PPA by hand.** Revenue per MWh for solar and wind in 2025 at 78.51.
2. **What is a floor worth?** For floors at 0 and 20 EUR/MWh in 2025.
3. **Break-even strike with a negative-price clause.** By how much does the clause raise
   the fair strike for solar and for wind?
4. **Written:** same baseload contract, opposite outcomes (section 4.2). Why?

**Core**

5. **Monthly floor (test first).** Many floors settle on the **monthly average** capture
   price, not per interval. Write `monthly_floor_value(prices, volumes, floor, tz)` in a
   new test-first function and compare it with the interval floor for solar 2025. Which
   is worth more, and why (think about averaging and convexity)?
6. **Zero-cost collar.** For solar 2025, find the cap C that makes a collar with floor 20
   cost nothing on history (floor payout = cap payout). Use a simple bisection.
7. **Hybrid park.** Combine the solar and wind parks into one portfolio and compute the
   portfolio's capture rate and the baseload PPA surprise for 2025. Does the portfolio
   suit a baseload product better than solar alone?

**Stretch**

8. **Discounting over ten years.** Build a 10-year PaP with flat expected prices and a
   6% discount rate. Show that discounting changes the fair price only if volumes or
   prices are not flat over time (hint: the ratio of expectations).
9. **Buyer's view.** Write the buyer's P&L for each structure and check that producer
   P&L + buyer P&L = 0 against the spot alternative.

<details>
<summary>Hints and solution sketches</summary>

1. B = q.sum() / len(q); cash = K·B + (q − B)·P; divide the sum by q.sum(). Solar is far
   below merchant, wind slightly below.
2. (floor − p).clip(lower=0) times q, summed, divided by q.sum(). Raise the floor and
   watch the value grow faster than linearly.
3. Solve K · (energy at P ≥ 0) = merchant revenue. Compare with Step 2's capture price.
4. Split each baseload surprise into "merchant surprise" + "swap leg"; the swap leg is the
   same for both parks; the merchant surprise is not. What drives each park's merchant
   surprise: the level, the shape, or both?
5. Group by month: payout_m = q_m · max(F − capture_m, 0). By Jensen's inequality the
   average of payoffs is at least the payoff of the average: the interval floor is worth more.
6. Write f(C) = floor payout − cap payout; f decreases in C; bisect between 20 and 500.
7. Sum the two energy series; the portfolio's profile is flatter, so the residual is smaller.
8. With flat q and P, the weights D_t·q_t are proportional for numerator and denominator.
9. Buyer of a physical PaP: (P − K) · q per interval.

</details>

---

## 8. Self-check quiz

1. Write the producer's cash flow of a PaP PPA, a CfD and a baseload PPA.
2. Why do a physical PaP PPA and a virtual PPA give the producer the same cash flow?
3. Which risk does a PaP PPA leave with the producer, and which does a baseload PPA leave?
4. Show that a baseload PPA equals merchant revenue plus a swap.
5. Why is a floor at 0 EUR/MWh the same as the right to curtail?
6. Why is the fair PaP price a ratio of expectations and not an average of capture prices?
7. What does a negative-price clause do to the fair strike, and why more for solar?
8. Why was the monthly revenue spread a bad risk measure, and what replaced it?
9. What is the "plan" in the back-test, and why must strikes come from the year before?
10. What is missing between the historical fair price and a price you would quote?

<details>
<summary>Answers</summary>

1. PaP: K·q. CfD: q·P + (K − P)·q = K·q. Baseload: K_B·B + (q − B)·P.
2. In the virtual PPA the producer sells at spot and receives (K − P)·q from the buyer;
   the price terms cancel. Differences are basis, volume definition and accounting.
3. PaP: volume only. Baseload: shape and volume (the price level of the band is fixed).
4. K_B·B + (q − B)·P = q·P + B·(K_B − P): merchant plus a fixed-for-floating swap on B.
5. Curtailing at P < 0 earns q·max(P, 0), the payoff of spot plus a 0-strike put.
6. Scenarios with more energy contribute more revenue and more MWh; averaging capture
   prices would give a calm year the same weight as a windy one.
7. It removes paid volume in negative hours, so K must rise to keep revenue equal to
   merchant; solar produces far more of its energy at negative prices (24% in 2025).
8. Within a year it mostly measures seasonality, which is known in advance; the surprise
   against plan (realised − expected at signing) measures risk.
9. The same contract terms applied to the previous year's prices and profile: the
   expectation at signing. Using delivery-year data for the strike would be hindsight.
10. Forward prices instead of last year's outcome, a distribution instead of one history,
    risk premia, negative-price and curtailment costs, balancing, route to market,
    credit and discounting over the full tenor.

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* a buyer asked for alternatives to a pay-as-produced solar PPA. *Task:*
> show the economics and the risk transfer of each structure and write the methodology
> for Risk. *Action:* I implemented the cash flows of merchant, pay-as-produced, virtual
> PPA, floors and collars and baseload PPAs as vectorised functions, tested their
> invariants (a floor never lowers value, a baseload PPA is merchant plus a swap) and
> back-tested them on 2024-2025 with strikes fixed from the previous year. *Result:* the
> PaP PPA removed all price surprise; the baseload PPA on solar lost 11 EUR/MWh against
> plan in 2025 because it hedged the level but not the shape; and a negative-price clause
> cost 11 EUR/MWh. I also caught my own wrong risk metric: monthly volatility was
> seasonality, so I replaced it with surprise against plan.

**Likely questions and strong answers:**

- *"How would you price a 10-year PaP PPA for a German solar park?"* Baseload forward
  curve times a simulated capture rate (joint weather and price scenarios), fair price as
  E[sum D·q·P] / E[sum D·q], then risk premia from the distribution (P5 or CFaR), minus
  negative-price, balancing, route-to-market and credit costs; sanity-check against
  market values.
- *"Why is a baseload PPA priced differently?"* The producer delivers a flat band and
  buys its shortfalls when it does not produce; for solar those are the expensive hours,
  so it is short the shape. Baseload PPA = merchant + swap.
- *"What is a floor worth?"* The expected discounted payoff of a strip of puts; convex in
  the strike, so it needs the price distribution, not the average. A 0-strike floor is
  the value of curtailment.
- *"The buyer wants no payment at negative prices. What do you do?"* Quantify the share
  of energy at negative prices in the scenarios, raise the strike to keep value
  (substantially for solar), or offer curtailment rights or a battery to shift energy.

---

## 10. How this maps to real work at Encavis

| In this project | In a company |
|---|---|
| `contracts.py` cash flows | The pricing library behind every term sheet and the deal model |
| Prior-year strikes | Forward curves from EEX, broker quotes, the hourly price forward curve |
| One history | Monte Carlo over price paths and weather years (Steps 5-7) |
| Plan and surprise | Budget vs actual reporting, PPA performance monitoring |
| METHODOLOGY.md | Model documentation for Risk, auditors and model validation |
| Negative-price clause, floors | Term-sheet negotiation with offtakers; structuring desk |
| Worst month | Debt sizing and liquidity planning with lenders |

Encavis sells part of its output through PPAs (and runs merchant and regulated assets
too); each new PPA starts with exactly these structure comparisons.

---

## 11. Your to-dos for Step 3

- [ ] Read sections 1 and 4 with a notebook; redo the running example (1.2) by hand.
- [ ] Read `METHODOLOGY.md` once on GitHub (formulas render there).
- [ ] Run section 5; play with notebook cells 3.2 and 3.5.
- [ ] Exercises 1-4 in `exercises/step03_ppa.py`; check them in the notebook's
      "My solutions: Step 3" block.
- [ ] **Commit Step 3** (commands below).
- [ ] **German vocabulary of this step:** der Stromabnahmevertrag (PPA), erzeugungsabhängig
      (pay-as-produced), die Bandlieferung (baseload), der Differenzvertrag (CfD), die
      Preisuntergrenze (floor), die Preisobergrenze (cap), der Ausübungspreis (strike),
      die Gegenpartei, das Ausfallrisiko (credit risk), die Liquidität.
- [ ] Stand-up update: *"Yesterday: PPA structures and methodology v0; back-test shows a
      baseload PPA on solar leaves shape risk (−11 EUR/MWh in 2025). Today: weather to
      power (PPA-4). Blockers: none."*

Commit (check `git status` first: no `.env`, no ` M .env.example`):

```bash
cd ".../Encavis quantitative/ppa-lab"
git status --short
git add src tests exercises config reports docs notebooks METHODOLOGY.md README.md CHANGELOG.md Makefile pyproject.toml
git status --short
git commit -m "feat(pricing): PPA structures, fair prices and 2024-2025 back-test (PPA-3)"
git push
gh run watch
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| PPA | Power purchase agreement: long-term contract to buy or sell electricity |
| Pay-as-produced | The buyer takes the actual output at a fixed price |
| Baseload PPA | Constant band every hour; producer settles the residual at spot |
| Virtual PPA / CfD | Financial contract settling (K − P) on a volume; no delivery |
| Strike | The fixed price K of a PPA, CfD or option |
| Floor / cap / collar | Minimum / maximum price, or both; strips of puts / calls |
| Zero-cost collar | Floor and cap chosen so their premiums offset |
| Shape risk | Risk from when energy is produced vs when it is expensive |
| Basis risk | Difference between the settlement price and the achieved price |
| Fair (break-even) price | Strike making the contract worth the same as merchant |
| Plan / surprise | Expected outcome at signing / realised minus plan |
| CFaR | Cash flow at risk: expected cash flow minus a low quantile |

## 13. Sources

- Encavis preparation guide (7 Oct 2026): pricing equations, Figure 5 pricing stack,
  interview questions, project specification (sections 3.3, 5, 6.2)
- AFRY, "Correctly valuing baseload PPAs in the Nordic market" (guide source S14)
- EEG 2023 §51 (no payment entitlement in periods with negative prices)
- Step 2 results: capture prices and negative-price shares 2023-2025 (`reports/step02_capture_prices.md`)
