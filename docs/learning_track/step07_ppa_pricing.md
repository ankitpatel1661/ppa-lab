# Step 7: Pricing the PPA and its risk (ticket PPA-7)

> **Numbers on this page (update for v1.1).** This page was written with the illustrative
> forward of 85 EUR/MWh (v1.0). Since v1.1 the model uses the market forward curve (EEX Cal-27
> base 140.21 EUR/MWh on 9 Oct 2026, Cal-28 104.75, Cal-29 87.58; see
> [Step 8, section 4.6](step08_hedging.md#46-update-v11-the-forward-is-now-the-markets)), and
> since v1.2 the market's seasonal shape and a solar cannibalisation trend
> ([section 4.7](step08_hedging.md#47-update-v12-the-markets-seasons-and-a-cannibalisation-trend)),
> so prices and fair prices are higher. Since v1.3 the parks are two Encavis parks modelled from
> public data (Borrentin solar, 114 MWp; Everswinkel wind, 28.5 MW) instead of illustrative
> ones. The methods and lessons are unchanged; current numbers are in the reports and the
> README, and the exercise checks use the current data.

> **Time needed:** about 5 hours. Concepts take 75 minutes, code tour and findings
> 45 minutes, hands-on, notebook and exercises 2 hours, to-dos 45 minutes.
> **You will be able to:** price the standard PPA structures on joint scenarios, measure
> what each one leaves with the producer (cash flow at risk), compute the buyer's risk
> premium after a baseload hedge and split it into profile and volume risk, and build an
> indicative ten-year price from a forward price, with its sensitivities.

**Contents:** [0. Scenario](#0-the-scenario) ·
[1. Concepts](#1-concepts-you-need-today) ·
[2. Architecture](#2-what-was-built-architecture) ·
[3. Code tour](#3-code-tour) ·
[4. Findings](#4-five-real-findings) ·
[5. Hands-on](#5-hands-on-run-it-yourself) ·
[6. Results](#6-results-the-answer) ·
[7. Exercises](#7-exercises) ·
[8. Quiz](#8-self-check-quiz) ·
[9. Interview](#9-interview-corner) ·
[10. Real work](#10-how-this-maps-to-real-work-at-encavis) ·
[11. To-dos](#11-your-to-dos-for-step-7) ·
[12. Glossary](#12-glossary) ·
[13. Sources](#13-sources)

---

## 0. The scenario

Tuesday, pricing committee at 3 pm. The head of origination:

> *"We have the scenarios. Now I need a number I can put in front of the buyer for ten years of
> the Lusatia solar park, a number I can defend in front of Risk, and one sentence on how much
> risk we keep. Ticket PPA-7."*

Steps 1 to 6 built the ingredients: prices that reconcile (Step 1), capture prices (Step 2),
the contract cash flows (Step 3), the parks' output over 31 weather years (Step 4), price
paths (Step 5) and the two simulated together (Step 6). Step 7 turns them into the answer to
the project question.

**Ticket PPA-7: acceptance criteria (all met today)**

- [x] Every structure (merchant, pay-as-produced with and without a negative-price clause,
      merchant with a floor, baseload) on the joint scenarios: fair price, expected and P5
      revenue, 95% cash flow at risk.
- [x] The buyer's risk premium after a baseload hedge, split into profile and volume risk;
      the unhedged premium for comparison.
- [x] A price stack from the forward to an indicative price, with stated cost assumptions.
- [x] A ten-year price with discounting, degradation and sensitivities (capture-rate trend,
      forward, analog pool).
- [x] The decision on the analog pool from Step 6, made explicit in the configuration.
- [x] Report, `ppa_pricing.json` for Step 9, learning page, notebook section, exercises.

---

## 1. Concepts you need today

### 1.1 Two sides of the same contract

A pay-as-produced (PaP) PPA at strike K moves risk from one party to the other:

| | Producer (Encavis) | Buyer |
|---|---|---|
| Receives / pays | receives K for every MWh produced | pays K for every MWh produced, sells it at P |
| Annual cash flow | K · Σ q | Σ q (P − K) |
| Risk it keeps | volume only (how much the weather delivers) | price level, shape (profile) and volume |

The same contract therefore needs two risk measures: the producer's **cash flow at risk**
(how much less than expected could the year bring?) and the buyer's **risk premium** (how much
must the strike be below the fair price for the buyer to accept the risk?).

### 1.2 Cash flow at risk

For annual revenue R over the scenarios,

    CFaR95 = E[R] − q5%(R)

the shortfall of a bad year (one in twenty) against an average year. It is the producer's
version of value at risk, in cash, which is what lenders and the CFO care about. A structure
that fixes the price leaves only volume risk; a structure that fixes the band (baseload)
leaves profile risk; merchant leaves everything.

### 1.3 The buyer's premium, and why the hedge matters

At the fair price K* the buyer breaks even on average: E[Σ q (P − K*)] = 0. Its risk is the
spread around zero. The premium it asks for is the 5% shortfall per expected MWh:

    premium = (E[V] − q5%(V)) / E[Σ q],      V = Σ_t q_t (P_t − K)

But most of that spread is the **price level**: if 2027 is a 100 EUR/MWh year instead of 85,
the buyer gains on every MWh. The level is hedgeable with a baseload forward: the buyer sells
a band B = E[Σ q] / 8,760 MW at the forward F, adding B · Σ_t (F − P_t) to V. What is left
is the risk nobody can hedge with standard products: **profile** (the shape of the output
against the shape of prices) and **volume** (how much the weather delivers, and the fact that
sunny and windy years are cheap years). That residual premium is what the buyer can
reasonably ask for; the unhedged number would charge the producer for a risk the buyer can
remove at almost no cost.

Splitting it:

- **profile:** the same calculation with the *expected* hourly volume in every scenario
  (only the price shape varies);
- **volume:** joint − profile: what varying volumes, and their correlation with prices, add.

### 1.4 The price stack

    indicative PaP price = forward × capture rate − risk premium − balancing − credit
                         = fair price            − risk premium − costs

The forward and the capture rate come from the scenarios (Steps 5 and 6); the premium from
1.3; balancing and route-to-market costs and credit and liquidity costs are stated
assumptions (`[ppa.parks.*]` in the configuration: 1.5 and 1.0 EUR/MWh for solar, 2.0 and
1.0 for wind, the preparation guide's illustrative values).

### 1.5 From one year to ten

The scenarios cover 2027. A ten-year price needs assumptions for the later years:

    K_y = F_y · c_y,   c_y = c_2027 + drift · (y − 2027) + γ(F_y) − γ(F_2027),
    E_y = E_2027 · (1 − degradation)^(y − 2027)
    K_10y = Σ_y D_y E_y K_y / Σ_y D_y E_y,   D_y = (1 + r)^−(y − 2027 + 0.5)

an energy- and discount-weighted average of the yearly fair prices. γ(F) is the capture rate
at price level F: since v1.5 the scenarios are rebuilt at each year's forward, so a year at 88
EUR/MWh gets the capture rate of an 88 year, not 2027's (Step 8 page, section 4.8). With a flat
forward and a flat capture rate it equals the 2027 price; the sensitivities show what a trend
does. The
risk premium and the costs per MWh of the first year are applied to every year (a
simplification: a ten-year contract averages weather years but adds uncertainty about the
level and the capture-rate trend).

### 1.6 The analog-pool decision

Step 6 showed that which historical days stand in for 2027 moves the solar fair price from
48.7 (whole 2024-2026 window) to 41.1 EUR/MWh (the last twelve months). Step 7 takes the last
twelve months as the base case (`analog_pool_start = 2025-10-01`), because 2027 will have at
least as much solar capacity as 2026, and reports the whole window as a sensitivity. It is a
judgement, written down where Risk can see and challenge it.

---

## 2. What was built: architecture

```
Step 6: build_scenarios(..., restrict_pool(link, analog_pool_start))   config [ppa], [ppa.parks.*]
            │  prices P[s, t], volumes q[s, t] per park (496 x 8,760)          │
            ▼                                                                  │
pricing/risk.py   structure_revenues / structure_table  (Step 3 contract functions)
                  buyer_value · risk_premia (unhedged, joint, profile, volume) │
                  cash_flow_at_risk · premium · tenor_price ◄──────────────────┘
            │
analysis/step07_report.py ─► reports/step07_ppa_pricing.md + 3 charts      (`ppa-lab pricing`)
                          ─► data/processed/ppa_pricing.json (input for Step 9)
```

---

## 3. Code tour

### 3.1 `pricing/risk.py`

- `structure_revenues` reuses the **Step 3 contract functions unchanged** (`merchant`,
  `pay_as_produced`, `collar`, `baseload`) on (scenario × hour) arrays: the same tested code
  that priced history now prices the future. Each structure is struck at its fair price; the
  floor's fair premium is deducted from the floor variant.
- `structure_table` turns each revenue array into expected revenue, P5, CFaR95 and CFaR as a
  share of expected revenue.
- `buyer_value` and `risk_premia` implement 1.3; `tenor_price` implements 1.5 and returns the
  year-by-year table with the tenor price in `.attrs["price"]`.

### 3.2 `analysis/step07_report.py` and `ppa-lab pricing`

Builds the Step 6 scenarios twice (the configured pool and the whole window), prices both
parks, writes the structure, premium, stack and tenor tables, the answer paragraph, three
charts and `ppa_pricing.json`. About a minute: the capture rate's response to the price level
rebuilds the scenarios at twelve forwards (v1.5). `ppa-lab all` now ends with this step.

### 3.3 Tests: what each one protects

| Test file | Protects against |
|---|---|
| `test_risk.py` (12) | wrong CFaR or premium arithmetic; a buyer that does not break even at the fair price; a hedge that does not remove the level risk of flat volumes; a profile/volume split that does not add up or misses the volume–price link; structures with different expected revenue at fair strikes; a free floor; a clause that ignores negative prices; tenor prices without drift, degradation or discounting; a forward curve that is ignored; a capture rate that does not move with the level, or is read off the wrong scale (it is linear in ln level, flat beyond the measured range) |
| `test_level_effect.py` (6) | a regression that misses a known slope or invents one, a sample that does not start where configured, capture rates and shares computed wrongly, an answer where the data cannot separate level from build-out, a build-out pace from incomplete years |
| `test_step07_report.py` (2), `test_config.py` (+1), `test_cli.py` (+1) | the report end to end and its internal consistency (indicative = fair − premium − costs), the missing-weather message, `[ppa]` validation, `ppa-lab pricing` and `all` |

Planted bugs that the tests catch: the joint premium without the hedge, the profile premium
with the actual volumes, the floor premium not deducted, no discounting, the clause ignored.
One test needed a fix to catch its bug: the first synthetic prices were never negative, so a
free floor looked fair; the structures test now shifts prices into negative territory.

---

## 4. Five real findings

### 4.1 A PPA removes 77-86% of the producer's risk

| 2027 | Merchant CFaR95 | PaP CFaR95 | Reduction |
|---|---|---|---|
| Solar park | EUR 1.44 m (64% of revenue) | EUR 0.20 m (9%) | 86% |
| Wind park | EUR 2.95 m (36%) | EUR 0.68 m (8%) | 77% |

What is left is volume: a dull year still delivers fewer MWh. A baseload PPA sits in between
(solar 0.35 m): it fixes the level but leaves the producer with the profile. A floor at 0
EUR/MWh reduces solar CFaR only to EUR 1.07 m: it removes the negative-price tail, not the
price level.

### 4.2 Most of the buyer's risk is hedgeable

| EUR/MWh | Unhedged premium | After baseload hedge | of which profile | of which volume |
|---|---|---|---|---|
| Solar park | 25.23 | **5.27** | 4.96 | 0.32 |
| Wind park | 27.88 | **3.39** | 0.88 | 2.50 |

80-88% of the buyer's risk is the price level, which a baseload forward removes. Without
the hedge the "premium" would eat 60% of the solar fair price. The residual tells the story
of each technology: **solar's risk is profile** (how deep the midday dip is in a given year),
**wind's risk is volume** (how much wind, and the fact that windy years are cheap).

### 4.3 The negative-price clause costs solar a quarter of its revenue

At the plain fair strike, a clause that pays nothing for output at negative prices cuts the
solar park's expected revenue from EUR 2.26 m to 1.69 m (−25%), the wind park's by 9%. That
matches history: 24% of solar energy was produced at negative prices in 2025 (Step 2). The
same fact makes a floor at 0 EUR/MWh worth 9.34 EUR/MWh for solar (wind 3.05). A buyer that
asks for the clause must pay a much higher strike for it (that strike is Step 3, Exercise 3).

### 4.4 The indicative price, and what moves it

| Ten-year price 2027-2036 (EUR/MWh) | Solar fair | Solar indicative | Wind fair | Wind indicative |
|---|---|---|---|---|
| **Base case** | **41.08** | **33.31** | **74.81** | **68.43** |
| Capture rate −2 pp per year | 34.28 | 26.51 | 67.94 | 61.56 |
| Capture rate −1 pp per year | 37.68 | 29.91 | 71.38 | 64.99 |
| Capture rate +1 pp per year | 44.48 | 36.71 | 78.25 | 71.86 |
| Forward −10% | 36.97 | 29.20 | 67.33 | 60.95 |
| Forward +10% | 45.19 | 37.42 | 82.30 | 75.91 |
| Analog days from the whole window | 48.66 | 40.89 | 75.35 | 68.97 |

For solar, the three biggest levers are the **analog pool** (+7.6), the **capture-rate trend**
(±3.4 per pp per year) and the **forward** (±4.1 for ±10%). The risk premium (5.3) and the costs
(2.5) together matter less than any of them. Wind is far less sensitive to the pool (+0.5):
its price depends on the forward and on wind's own cannibalisation.

### 4.5 Small ones

- **A deprecated plotting argument** (`vert=False` in Matplotlib 3.11) raised a warning in the
  report test; it now uses `orientation="horizontal"`.
- **Chart labels hit the titles** in the first price stack; the y axis now leaves room.
- **A test set-up that could not fail:** the first synthetic prices had the same daily shape
  in every scenario, so profile risk was zero by construction. Each scenario now has its own
  dip depth.
- **The analog pool** is now a configuration value with a comment that explains it, not a
  hidden choice in code.

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                  # 207 offline tests
make pricing               # structures, premia, stack, ten-year price (about 12 s)
open reports/step07_ppa_pricing.md
make notebook              # Step 7 section: 7.1 to 7.6, then your solutions
```

In the notebook: 7.3 shows the buyer's side at any strike, 7.5 builds your own offer, 7.6
changes the analog pool.

---

## 6. Results: the answer

![Price stack, solar and wind](../../reports/figures/step07_price_stack.png)

![What each structure leaves with the producer](../../reports/figures/step07_revenue.png)

![The buyer's risk with and without a baseload hedge](../../reports/figures/step07_buyer_risk.png)

> *"For a 10-year pay-as-produced PPA (2027-2036) from the 50 MWp solar park in Lusatia, the
> fair price before risk premia is 41.1 EUR/MWh (forward 85.4 × expected capture rate 0.48).
> After a profile and volume risk premium of 5.3 EUR/MWh and balancing and credit costs of
> 2.5 EUR/MWh, the indicative price is 33.3 EUR/MWh. Expected annual energy is 55.1 GWh (P50;
> one-year P90 51.5 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR
> 1.44 m (merchant) to EUR 0.20 m per year: only volume risk is left."*

### 6.1 Five stories

1. **Solar sells at less than half the baseload price.** 85 × 0.48 = 41: the shape alone
   takes 44 EUR/MWh, eight times more than the risk premium.
2. **The hedge is the negotiation.** A buyer who quotes a 25 EUR/MWh premium is charging
   for risk it can hedge for free; the defensible premium is about 5.
3. **Wind and solar have different risks.** Solar: profile. Wind: volume. They belong in
   different structures (solar: PaP or baseload with a shape adjustment; wind: volume
   protections or a portfolio).
4. **The clause is not free.** A quarter of the solar output falls at negative prices; a
   buyer asking for the clause must pay for it in the strike.
5. **The biggest uncertainty is the future of cannibalisation,** not the weather: the analog
   pool and the capture-rate trend move the price more than the premium and costs together.

### 6.2 What this means for the rest of the project

- **Step 8** (hedging): the producer's remaining merchant exposure (if it keeps part of the
  output) and the buyer's baseload hedge, with market forwards instead of one assumed number.
- **Step 9** (public MVP): `ppa_pricing.json` feeds the dashboard and the one-page memo.

---

## 7. Exercises

**Warm-up (in `exercises/step07_pricing.py`, checked by `.venv/bin/pytest exercises -q`)**

1. **How much risk does a PPA take away?** Merchant and pay-as-produced CFaR95 from the Step 6
   scenario file.
2. **One price for ten years,** with a capture-rate trend, degradation and discounting.
3. **The buyer's premium,** with and without a baseload hedge, on a toy market.
4. **Written:** the price negotiation between 33 and 41 EUR/MWh.

**Core**

5. **The fair strike with the clause on scenarios.** Solve "PPA revenue with the clause = merchant
   revenue" over the scenarios (your Step 3 Exercise 3, now in expectation). How far above 41 is it?
6. **A premium at a different quantile.** Recompute the premia at 10% and 1%. Which park's
   premium grows faster, and why?
7. **A zero-cost collar.** With a floor at 0 EUR/MWh for solar, find the cap C at which the
   cap is worth as much as the floor (METHODOLOGY section 4), so the producer pays nothing net.

**Stretch**

8. **Multi-year premium.** Simulate ten consecutive years by drawing ten weather years and price
   paths per scenario. Is the ten-year premium per MWh smaller or larger than the one-year one?
9. **Capital.** If the buyer holds capital equal to its premium at 10% per year for ten years,
   what does that add to the price?

<details>
<summary>Hints and solution sketches</summary>

1. Linked rows, `K = rev.sum() / mwh.sum()`, PPA revenue `K * mwh`, `mean - quantile(0.05)`:
   solar EUR 3.54 m vs 0.84 m for the 114 MWp Borrentin park (v1.6; v1.3: 3.74 vs 0.85; 50 MWp
   at 85: 1.38 vs 0.23; the file uses analog days from the whole window).
2. Loop over the years; with a −1 pp drift and 0.5% degradation at 6%: 37.68 EUR/MWh.
3. `buyer_value` by hand; the toy gives 28.61 without and 9.64 with the hedge.
4. The 8 EUR/MWh are the premium after the hedge (about 5) and the costs (2.5). Concede the
   hedged premium, not the unhedged one: the buyer can sell a baseload forward. Challenge
   first which historical days represent 2027 (and the capture-rate trend): they move the price
   more than everything the buyer asks for.
5. `K_clause = E[Σ q P] / E[Σ q 1(P ≥ 0)]`; for solar about 41.1 / 0.75 ≈ 55 EUR/MWh.
6. `risk_premia(P, Q, quantile=0.10)`.
7. Cap value E[Σ q (P − C)⁺] / E[Σ q] falls as C rises; bisect C until it equals the floor value
   (9.34 EUR/MWh).
8. Use `build_scenarios` with different seeds and sum over years before taking the quantile.
9. 10% × premium-at-risk per MWh, discounted.

</details>

---

## 8. Self-check quiz

1. Under a pay-as-produced PPA, which risks does the producer keep and which does the buyer take?
2. Define CFaR95. Why do lenders and CFOs like it?
3. What is the buyer's value of a PaP PPA per scenario, and why is it zero on average at the fair price?
4. Why must the premium be computed after a baseload hedge?
5. How is the premium split into profile and volume, and why is solar's mostly profile?
6. Write the price stack from the forward to the indicative price.
7. How does a ten-year price follow from the first year's price, and when are they equal?
8. Why does a negative-price clause cost the solar park so much?
9. Which three assumptions move the solar price most, and by how much?
10. Why is the analog pool a configuration value?

<details>
<summary>Answers</summary>

1. Producer: volume. Buyer: price level, shape (profile) and volume.
2. Expected revenue minus its 5% quantile: the cash shortfall of a one-in-twenty year, which
   is what debt service and budgets must survive.
3. Σ q (P − K): it pays K for each MWh and sells at P. At K* = E[Σ q P]/E[Σ q] the expectation is zero.
4. The price level is hedgeable with a baseload forward; charging for it would price a risk the
   buyer can remove almost for free.
5. Profile: expected hourly volume in every scenario; volume = joint − profile. Solar's volume
   barely varies between years (CoV 5%), while the depth of the midday dip varies a lot.
6. Forward × capture rate = fair price; minus risk premium, balancing and route to market,
   credit and liquidity = indicative price.
7. Energy- and discount-weighted average of yearly fair prices; equal when forward and capture
   rate are flat.
8. About a quarter of its output falls in negative-price hours, which the clause leaves unpaid.
9. The analog pool (+7.6 EUR/MWh), the capture-rate trend (about ±3.4 per pp per year) and the
   forward (about ±4.1 for ±10%).
10. It is a judgement that moves the answer by 15%; it must be visible and challengeable, not
    buried in code.

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* origination needed a defensible ten-year price for a 50 MWp solar PPA and a
> statement of the risk we keep. *Task:* price the standard structures on joint weather and
> price scenarios and build the price from the forward to an offer. *Action:* I reused the
> tested contract functions on 496 scenarios, measured the producer's cash flow at risk per
> structure, computed the buyer's premium after a baseload hedge and split it into profile
> and volume, and added a ten-year layer with sensitivities. *Result:* a fair price of 41.1 and
> an indicative 33.3 EUR/MWh; the PPA cuts our CFaR by 86%; and I showed that the assumption
> on future cannibalisation moves the price more than the whole risk premium.

**Likely questions and strong answers:**

- *"How do you price a pay-as-produced PPA?"* Forward times expected capture rate from joint
  weather–price scenarios, minus a premium for the unhedgeable profile and volume risk, minus
  balancing, route-to-market and credit costs; then a term structure for multi-year deals.
- *"What risk premium would you accept?"* The premium after the buyer hedges the level with
  baseload forwards; here about 5 EUR/MWh for solar, 3.4 for wind.
- *"What does the PPA do to our risk?"* It replaces price and shape risk with a fixed price; we
  keep volume risk (CFaR from EUR 1.44 m to 0.20 m per year for the solar park).
- *"What would make you change the price?"* A view on future solar capacity and batteries (the
  capture-rate trend and the analog pool), and market forwards (Step 8).

---

## 10. How this maps to real work at Encavis

| In this project | In a company |
|---|---|
| Fair price from 496 joint scenarios | PPA pricing models with weather years and price scenarios, often from vendors |
| Premium after a baseload hedge, 5% quantile | Risk premia from desk hedging costs, internal capital charges, market quotes |
| Balancing, credit as stated costs | Route-to-market contracts, balancing cost models, counterparty credit assessment |
| Ten-year price with a capture-rate trend | Long-term price curves and cannibalisation scenarios per technology |
| CFaR per structure | Budget at risk, debt sizing, the risk committee's view of a deal |
| `ppa_pricing.json` | Deal sheets and pricing memos for the investment committee |

---

## 11. Your to-dos for Step 7

- [ ] Read sections 1 and 4. By hand: forward 85, capture rate 0.48, premium 5.3, costs 2.5 →
      indicative price? (33.3 EUR/MWh.)
- [ ] Run section 5; in the notebook, find the strike in 7.3 at which the buyer's 5% quantile is zero.
- [ ] Exercises 1-4 in `exercises/step07_pricing.py`; check them in "My solutions: Step 7".
- [ ] **Commit Step 7** (commands below).
- [ ] **German vocabulary of this step:** der Strombezugsvertrag (PPA), der Festpreis, der
      Abnehmer, der Erzeuger, die Risikoprämie, das Profilrisiko, das Mengenrisiko, die
      Absicherung (hedge), der Terminkontrakt, Cashflow at Risk, der Kreditaufschlag, die
      Laufzeit, die Abzinsung, die Kannibalisierung.
- [ ] Stand-up update: *"Yesterday: priced the PPAs on the joint scenarios: solar 41.1 fair,
      33.3 indicative for ten years; the PPA cuts our cash flow at risk by 86%. Today: the public
      MVP (Step 9). Blockers: none."*

Commit (check `git status` first: no `.env`, no ` M .env.example`):

```bash
cd ".../Encavis quantitative/ppa-lab"
git status --short
git add src tests exercises config reports docs notebooks METHODOLOGY.md README.md CHANGELOG.md Makefile pyproject.toml
git status --short
git commit -m "feat(pricing): PPA prices, risk premia and cash flow at risk on joint scenarios (PPA-7)"
git push
gh run watch
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Cash flow at risk (CFaR95) | Expected cash flow minus its 5% quantile |
| Risk premium | Discount on the fair price a risk taker asks for; here the 5% shortfall per MWh |
| Baseload hedge | Selling a constant band of power forward to fix the price level |
| Profile risk | Risk from the shape of output against the shape of prices |
| Volume risk | Risk from how much is produced, including its link to prices |
| Price stack | The layers from a forward price to an indicative PPA price |
| Tenor | Duration of a contract |
| Degradation | Annual loss of output of PV modules |
| Capture-rate trend | Expected change of the capture rate per year (cannibalisation vs storage) |
| Negative-price clause | No payment for output at negative prices; the producer curtails |
| Floor | Option that guarantees a minimum price |

## 13. Sources

- Jorion, P. (2007): *Value at Risk*, 3rd ed. McGraw-Hill (VaR and cash-flow-at-risk concepts).
- RiskMetrics Group (1999): *CorporateMetrics Technical Document* (cash flow at risk).
- Jordan, D. C. and Kurtz, S. R. (2013): Photovoltaic degradation rates: an analytical review.
  *Progress in Photovoltaics* 21(1), 12-29 (median about 0.5% per year).
- Hirth, L. (2013): The market value of variable renewables. *Energy Economics* 38, 218-236.
- Industry PPA market reports (for example Pexapark, LevelTen) for current European PPA prices
  and structures.
- Encavis preparation guide: price stack (illustrative costs), PPA pricing interview questions.
