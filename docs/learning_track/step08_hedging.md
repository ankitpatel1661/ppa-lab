# Step 8: Hedging with power futures (ticket PPA-8)

> **Numbers on this page (update for v1.1).** Sections 1-4.5 were written with the
> illustrative forward of 85 EUR/MWh (v1.0). The market check led to a decision: since v1.1 the
> model uses the market forward curve (section 4.6), and since v1.2 the market's seasonal
> shape and a solar cannibalisation trend (section 4.7), and since v1.3 two Encavis parks
> (Borrentin solar, Everswinkel wind) instead of illustrative ones; the current numbers are in
> `reports/step08_hedging.md`. The methods and lessons are unchanged.

> **Time needed:** about 4.5 hours. Concepts take 60 minutes, code tour and findings
> 45 minutes, hands-on, notebook and exercises 2 hours, to-dos 45 minutes.
> **You will be able to:** explain how German power futures hedge a renewable park, compute a
> minimum-variance hedge for one or several products, judge a hedge by the risk it removes (not
> by one year's P&L), size the PPA buyer's hedge, and check a model's forward against the market.

**Contents:** [0. Scenario](#0-the-scenario) ·
[1. Concepts](#1-concepts-you-need-today) ·
[2. Architecture](#2-what-was-built-architecture) ·
[3. Code tour](#3-code-tour) ·
[4. Findings](#4-five-real-findings) (and
[4.6 the v1.1 update](#46-update-v11-the-forward-is-now-the-markets),
[4.7 the v1.2 update](#47-update-v12-the-markets-seasons-and-a-cannibalisation-trend)) ·
[5. Hands-on](#5-hands-on-run-it-yourself) ·
[6. Results](#6-results-what-the-hedges-do) ·
[7. Exercises](#7-exercises) ·
[8. Quiz](#8-self-check-quiz) ·
[9. Interview](#9-interview-corner) ·
[10. Real work](#10-how-this-maps-to-real-work-at-encavis) ·
[11. To-dos](#11-your-to-dos-for-step-8) ·
[12. Glossary](#12-glossary) ·
[13. Sources](#13-sources)

---

## 0. The scenario

Friday, the treasury desk:

> *"Not every MWh will be sold through a PPA. For the output we keep, how much should we sell
> forward on EEX, in which product, and what does that do to our budget risk? And is the
> 85 EUR/MWh in your model anywhere near the market? Ticket PPA-8."*

Step 7 priced the PPA and showed that the buyer can hedge the price level with a baseload
forward. Step 8 makes that hedge explicit, for the producer's unsold output and for the PPA
buyer, and compares the model's forward with published market quotes.

**Ticket PPA-8: acceptance criteria (all met today)**

- [x] German futures products on the delivery calendar: Cal base and peak, quarters, months.
- [x] Hedge payoffs and minimum-variance hedges for one or several products.
- [x] Strategies for both parks' merchant output: none, 50% and 100% of average output,
      minimum-variance with Cal base, quarters, months; CFaR and variance removed.
- [x] The PPA buyer's minimum-variance band against Step 7's full band.
- [x] A back-test on 2024-2025 and a market check against published quotes.
- [x] Report, `hedging.json` for the memo and the dashboard, learning page, notebook, exercises.

---

## 1. Concepts you need today

### 1.1 What a futures hedge pays

A German power future delivers a constant MW over its period at a fixed price. Selling h MW
of a product k at forward F_k pays, at settlement,

    h · Σ_(t in k) (F_k − P_t)

the seller gains when spot ends below the forward. Products (EEX, local time):

| Product | Hours |
|---|---|
| Cal base | every hour of the year (8,760) |
| Cal peak | Monday to Friday 08:00-20:00, holidays included (3,132 in 2027) |
| Quarter / month base | every hour of the quarter / month |

A park that sells at spot and sells futures receives spot revenue **plus** the hedge payoff.
If prices fall, the hedge gains what the spot sales lose.

### 1.2 The minimum-variance hedge

How much to sell? The amount that makes the hedged revenue as stable as possible:

    h* = argmin Var(C + h X) = − Cov(C, X) / Var(X)

for one product (C = revenue per scenario, X = payoff of selling 1 MW). For several products,
the same is a least-squares regression of the revenue on the product payoffs. The classic
hedge ratio from finance (Ederington, 1979), applied to scenarios.

**Hedge ratio** = MW sold / average output in MW. Selling 100% of the average output is the
intuitive choice; it is not the optimal one when output is concentrated in cheap hours.

### 1.3 Why less than 100% for solar

A solar park produces when prices are low. If the price level rises by 10 EUR/MWh, its revenue
rises less than 10 EUR/MWh × its energy, because in the arcsinh price model high-price hours move
more than low-price hours, and solar produces in the low-price ones. A full baseload band then
over-hedges: in an expensive year the hedge loses more than the park gains. The minimum-variance
amount is about 90% of the average output for solar, 93-95% for wind.

### 1.4 Judging a hedge

A hedge is good if it **reduces risk**, not if it **made money** in one year. A hedge sold at a
fair price has an expected P&L of zero; it wins in some years and loses in others. Two measures:

- **CFaR reduction:** how much smaller the 95% cash flow at risk is.
- **Variance removed** (hedge effectiveness): 1 − Var(hedged) / Var(unhedged). Accounting rules
  for hedge accounting look at similar effectiveness tests.

### 1.5 Model forward and market forward

The model's forward is its expected average price (here the assumed 85 EUR/MWh, by construction
of the calibration in Step 5). The market forward is what someone will pay today. If they differ,
selling forward has an expected gain or loss: the **forward premium**. Before trading on it,
the question is who is wrong. A pricing model normally takes the market forward as its level and
uses the simulation only for shape and risk.

---

## 2. What was built: architecture

```
Step 7 scenarios (P, q; analog days from 2025-10-01)        config [hedging]: back-test years,
            │                                                market quotes (product, price, date, URL)
hedging/products.py   product_masks: Cal base/peak, Q1-Q4, M01-M12 (local time)
hedging/hedge.py      model_forwards · hedge_payoffs · min_variance_hedge
                      hedge_strategies · buyer_hedge · backtest_hedge
            │
analysis/step08_report.py ─► reports/step08_hedging.md + 3 charts        (`ppa-lab hedging`)
                          ─► data/processed/hedging.json ─► memo and dashboard (`ppa-lab memo`)
```

---

## 3. Code tour

### 3.1 `hedging/products.py` and `hedging/hedge.py`

`product_masks` turns the delivery hours into boolean masks per product, in local time (the March
month has 743 hours). `model_forwards` averages the scenario prices over each product's hours.
`hedge_payoffs` builds the matrix X (scenarios × products) of selling 1 MW; `min_variance_hedge`
solves the least-squares problem on centred values. `hedge_strategies` compares the standard
strategies; `buyer_hedge` sizes the PPA buyer's band; `backtest_hedge` sells Cal base for each
year at the previous year's average price.

### 3.2 `analysis/step08_report.py` and the memo

The report uses the same scenarios as Step 7, writes the tables and charts, and stores the
results in `hedging.json`. `ppa-lab memo` reads it: the memo's third recommendation now gives the
hedge, and its limits paragraph the market check; the dashboard has a Hedging tab.

### 3.3 Tests

| Test file | Protects against |
|---|---|
| `test_hedging.py` (6) | wrong product hours (peak window, DST month); forwards that are not averages; a hedge that does not recover a known exposure; strategies in the wrong order; a buyer band larger than needed; a back-test that sells at the same year's price |
| `test_step08_report.py` (2), `test_config.py` (+1), `test_cli.py` (+1) | the report end to end, the missing-weather message, `[hedging]` validation (back-test years, quote products), `ppa-lab hedging` and `all` |
| `test_step09_memo.py` (+1), `test_dashboard.py` (+1) | the memo and the dashboard using the hedging results |

Planted bugs that the tests catch: the hedge with the wrong sign, the back-test forward from the
same year, and the peak window shifted by one hour. The first products test only counted peak
hours and missed the shifted window (same count); it now checks the exact hours of a Wednesday
and a Saturday.

---

## 4. Five real findings

### 4.1 Selling about 90% of the average output removes most of the risk

| Merchant, 2027 | No hedge | Cal base 100% | Cal base minimum-variance |
|---|---|---|---|
| Solar park CFaR95 | EUR 1.44 m | EUR 0.35 m | **EUR 0.27 m** (5.6 MW, 89%) |
| Wind park CFaR95 | EUR 2.95 m | EUR 0.88 m | **EUR 0.74 m** (11.7 MW, 93%) |

A single Cal base contract does almost all the work: quarters and months reduce the CFaR only a
little further (solar 0.25 and 0.23).

### 4.2 Monthly hedges fit noise

The monthly minimum-variance amounts jump around and are even negative in some months (wind
January −4.8 MW, November 26 MW). With 496 scenarios, twelve coefficients mostly fit sampling
noise; and in this model one annual level shock moves all months together, so there is little
for monthly products to add. Real markets have month-specific shocks (gas, hydro, outages), which
is why desks do use them, with more data and constraints (no negative sales).

### 4.3 The PPA buyer needs a smaller band, so the premium is smaller

Step 7 assumed the buyer sells a band of 100% of the average output. The minimum-variance band
is 90% (solar) and 95% (wind), and the premium falls from **5.27 to 4.45 EUR/MWh** (solar) and
from 3.39 to 2.92 (wind). The Step 7 premium was conservative by about 0.8 EUR/MWh for solar.

### 4.4 One year of P&L says nothing

Back-test (Cal base at the previous year's average, 89-93% of P50 output): the hedge earned
EUR +0.82 m for the solar park in 2024 (sold at 95.18, spot 78.51) and lost EUR 0.53 m in 2025
(sold at 78.51, spot 89.32). With this naive forward the hedged revenue even moved more between
the two years than the merchant revenue (EUR 1.27 m vs 0.09 m), because last year's price moved
against this year's. Two years are an illustration; the scenario results measure the risk.

### 4.5 The model's forward is far below the market's

Published Cal-27 base quotes: **104.24 EUR/MWh** (31 Jul 2026,
[tacto.ai](https://www.tacto.ai/en/energy/electricity-price)) and **113.45 EUR/MWh**
(28 Aug 2026, [power2market](https://www.power2market.com/en/markets)); peak 119.48. The model
uses the assumed 85 from the preparation guide. At 113.45, with the same capture rate, premium
and costs, the solar indicative price would be **46.8 EUR/MWh instead of 33.3**, wind 93.0 instead
of 68.4. These are secondary web sources, not EEX settlement files; they are in the configuration
with date and URL so they can be replaced. The decision whether to re-anchor the model to the
market is recorded in the backlog: it moves every headline number.

### 4.6 Update (v1.1): the forward is now the market's

The market check led to a decision (backlog PPA-8b): the model's price level is now the
market's. When the quotes were checked again, Cal-27 base had risen further, from 113.45
(28 Aug) to **140.21 EUR/MWh** (9 Oct 2026, the year's high, driven by gas and weak French
nuclear output), and the curve falls steeply: **Cal-28 104.75**, **Cal-29 87.58**. A ten-year
PPA therefore follows the curve (`[ppa.forward_curve]`), with the years after 2029 held flat
at the Cal-29 quote (long-dated years trade too little for a quote).

| 10-year pay-as-produced PPA (2027-2036) | v1.0: 85 flat | v1.1: market curve |
|---|---|---|
| Solar: forward × capture rate = fair price 2027 | 85.4 × 0.48 = 41.1 | 141.0 × 0.63 = 89.1 |
| Solar: fair price, 10 years | 41.1 | **61.1** |
| Solar: buyer's risk premium after the hedge | 5.3 | 8.0 |
| Solar: indicative price, 10 years | 33.3 | **50.6** |
| Wind: indicative price, 10 years | 68.4 | **80.1** |

Three lessons:

1. **The curve matters as much as the level.** 2027 alone is at 141, but the discount- and
   energy-weighted forward over the ten years is 96.7 EUR/MWh: the ten-year price sits much
   closer to Cal-28 and Cal-29 than to Cal-27. A flat 140 would have overstated it badly.
2. **The capture rate moved with the level: check it.** The arcsinh price model (Step 5) raises
   all hours together in transformed units, so hours near zero are lifted too: the solar
   capture rate rises from 0.48 (at 85) to 0.63 (at 141), and the share of solar output at
   negative prices falls from 25% to 9%. History supports the direction for one step: from 2025
   to 2026 (January to September) the level rose from 88 to 108 EUR/MWh, prices in the sunniest
   10% of hours rose from 8 to 23 (the model predicts about +16), and the park's capture rate
   held at 0.51 although solar capacity kept growing. But 141 lies outside the data, so Step 7
   now also shows the usual shape-factor view (the capture rate of the recent level,
   104 EUR/MWh, with all prices scaled to the forward): solar indicative **43.1 instead of
   50.6**; wind barely moves (78.6 vs 80.1). That gap belongs in the conversation with Risk.
3. **The market's seasonal shape is steeper than the model's.** Q1-27 traded at 179.47 and
   Q2-27 at 114.04 EUR/MWh (14 Sep 2026), against the model's 141.4 and 124.3: the market prices
   a winter gas risk that 2024-2026 history does not contain. A quarterly forward curve is the
   next step (v2).

The hedging lessons hold at the new level: Cal base at 83% (solar) and 91% (wind) of the
average output cuts the merchant CFaR95 by 78% and 68%, and the PPA buyer's premium with the
minimum-variance band is 4.8 instead of 8.0 EUR/MWh (solar).

### 4.7 Update (v1.2): the market's seasons and a cannibalisation trend

Two steps towards how a pricing desk works:

1. **Each quarter at its market price.** A desk builds an hourly price forward curve (HPFC) that
   matches every traded product, not only the year. The market's seasonal shape is much steeper
   than the model's history-based one: on 14 Sep 2026 Q1-27 traded at 179.47 and Q2-27 at
   114.04 EUR/MWh with Cal-27 at 135.80. The scenarios now solve one level per quarter so that
   each quarter averages its forward: the quotes' shape scaled to today's Cal level
   (Q1 185.3, Q2 117.7, Q3 124.3, Q4 134.3 EUR/MWh; the year still averages 140.21). Months
   and hours within a quarter still come from history.
2. **A cannibalisation trend in the base case.** Solar's capture rate fell from 0.76 to 0.51 in
   2023-2025 as capacity grew. The base case now lets it fall 1 percentage point a year after
   2027 (0.62 → 0.53 by 2036), slower than history because batteries and curtailment at
   negative prices dampen it; ±1 and −2 pp are the sensitivities.

| 2027-2036, EUR/MWh | v1.1 | v1.2 |
|---|---|---|
| Solar: fair price 2027 | 89.1 | 86.9 |
| Wind: fair price 2027 | 127.9 | 130.7 |
| Solar: indicative price, 10 years | 50.6 | **45.2** |
| Solar: at the recent level's capture rate | 43.1 | 38.0 |
| Wind: indicative price, 10 years | 80.1 | **81.8** |

The lesson: **the market's winter premium hurts solar and helps wind.** Solar produces in the
cheaper Q2 and Q3, wind in the expensive winter. Item 3 of the plan, availability, turned out
to be in the models already (solar losses 10% incl. availability; wind 12%: wake, availability,
electrical); adding it again would have counted it twice. Grid curtailment is compensated in
Germany (§13a EnWG), so it is a contract question, not a price one.

---

## 5. Hands-on: run it yourself

```bash
cd ".../Encavis quantitative/ppa-lab"
make test                  # all offline tests
make hedging               # strategies, buyer's hedge, back-test, market check (about 7 s)
make memo                  # memo and dashboard results now include the hedge
open reports/step08_hedging.md
make notebook              # Step 8 section: 8.1 to 8.6, then your solutions
```

In the notebook: 8.2 draws the CFaR against the hedge size for any product, 8.5 changes the
back-test ratio.

---

## 6. Results: what the hedges do

![Cash flow at risk by hedge](../../reports/figures/step08_cfar.png)

![Monthly minimum-variance hedge vs expected output](../../reports/figures/step08_monthly_hedge.png)

![Solar revenue with and without the hedge](../../reports/figures/step08_revenue.png)

### 6.1 Five stories

1. **One product does it.** A Cal base hedge of about 90% of the average output removes 97% of
   the solar park's revenue variance in the model.
2. **100% is too much for solar.** Its output sits in cheap hours; a full band over-hedges.
3. **Finer products need more data.** Monthly hedges from 496 scenarios fit noise.
4. **The PPA buyer's premium shrinks** with an optimal hedge: about 4.5 instead of 5.3 EUR/MWh.
5. **The level is the big unknown.** The market says about 104-113 EUR/MWh for 2027, the model
   assumes 85: that gap moves the solar price by 13 EUR/MWh, far more than any hedge choice.

### 6.2 What this means

- For unsold output: sell about 90% of the average output as Cal base; review quarterly products
  once market data are in.
- For pricing: anchor the level to the market forward (a configuration change, see the backlog),
  then the simulation provides shape and risk around it.

---

## 7. Exercises

**Warm-up (in `exercises/step08_hedging.py`, checked by `.venv/bin/pytest exercises -q`)**

1. **What did a hedge earn in a real year?** 5 MW of baseload sold for 2024 and 2025 at the
   previous year's average.
2. **The minimum-variance hedge** on a toy market.
3. **How good is a hedge?** Variance removed for different sizes.
4. **Written:** "just hedge 100%".

**Core**

5. **Peak for solar.** Compare a Cal peak hedge with a Cal base hedge for the solar park (notebook
   8.2). Why does peak need more MW and do worse?
6. **No negative sales.** Re-solve the monthly hedge with h ≥ 0 (`scipy.optimize.nnls`). How
   much worse is the CFaR?
7. **The market forward.** Set `forward_eur_mwh = 113.45` in a copy of the configuration and run
   `make prices scenarios pricing hedging memo`. Which numbers change, and which stay?

**Stretch**

8. **Volume risk in the hedge.** Split the solar park's residual risk after the hedge into the part
   that comes from weather years and the part from price paths.
9. **Hedge accounting.** Read about the 80-125% effectiveness test; does the Cal base hedge pass?

<details>
<summary>Hints and solution sketches</summary>

1. `forward = prices.loc[str(year - 1)].mean()`, `mw * (forward - prices.loc[str(year)]).sum()`:
   EUR +0.73 m (2024) and −0.47 m (2025).
2. `-np.cov(cash, payoff)[0, 1] / np.cov(cash, payoff)[1, 1]`: 14.96 MW, 96% of the average output.
3. 0, 0.671 at 100% and 0.672 at the minimum-variance amount: the curve is flat near the optimum,
   so the exact ratio matters less than avoiding very small or very large hedges.
4. Solar produces in cheap hours, so its revenue moves less than a full band with the level; a
   100% hedge loses more than the park gains in an expensive year and the reverse in a cheap one.
   Judge a hedge by the risk it removes, not by one year's P&L (2024 +0.82, 2025 −0.53). If the
   market forward is far above the model's expectation, selling forward has an expected gain:
   either the market knows something (gas, CO2) or the model's level is wrong; check before trading.
5. Peak covers 36% of the hours; the solar park also produces at weekends.
6. Expect a small loss of effectiveness and much more sensible monthly amounts.
7. Prices, capture prices and premia scale with the level; the capture rate and the hedge ratio
   barely move.

</details>

---

## 8. Self-check quiz

1. What does selling 1 MW of Cal base at forward F pay?
2. Write the minimum-variance hedge for one product.
3. What is a hedge ratio here, and why is the optimum below 100% for solar?
4. Why do monthly hedges from 496 scenarios look strange?
5. How do you judge a hedge, and why not by its P&L?
6. Why did the PPA buyer's premium fall in Step 8?
7. What does the back-test with last year's price as forward show, and what does it not show?
8. What is a forward premium?
9. Why should a pricing model take its level from the market forward?
10. Which number in the whole project moves most if the forward changes from 85 to 113?

<details>
<summary>Answers</summary>

1. Σ over the year's hours of (F − P_t) per MW.
2. h* = −Cov(C, X)/Var(X), with C the revenue and X the payoff of selling 1 MW.
3. MW sold / average output; solar's revenue moves less than a flat band with the price level,
   because it produces in cheap hours, so a full band over-hedges.
4. Twelve coefficients estimated from 496 scenarios fit noise, and the model's level shock is
   annual, so monthly products have little extra to hedge.
5. By the risk it removes (CFaR, variance); a fair hedge has zero expected P&L and will win or lose
   in a single year by chance.
6. The minimum-variance band (90%) hedges the buyer's position better than a full band.
7. That hedges win and lose in single years; not how good the hedge is, because the forward proxy
   is not a real market price and two years are too few.
8. The difference between the market forward and the expected spot price.
9. The market price is where hedges and PPAs can actually be traded; the model adds shape and risk.
10. The indicative prices (solar 33.3 → 46.8 EUR/MWh, wind 68.4 → 93.0).

</details>

---

## 9. Interview corner

**Your 60-second story (STAR):**

> *Situation:* treasury asked how much of the unsold output to sell forward, and whether our
> model's price level matched the market. *Task:* size futures hedges on the joint scenarios and
> check the forward. *Action:* I modelled EEX base, peak, quarter and month products, computed
> minimum-variance hedges, compared strategies by cash flow at risk, re-sized the PPA buyer's hedge,
> back-tested on 2024-2025, and compared the model's forward with published Cal-27 quotes.
> *Result:* about 90% of average output as Cal base cuts the solar park's merchant CFaR by 81%;
> monthly hedges only fit noise; the buyer's premium is 0.8 EUR/MWh lower than assumed; and the
> market's Cal-27 is 104-113 against our 85, which I flagged as the biggest open assumption.

**Likely questions and strong answers:**

- *"How do you hedge a solar park?"* Sell baseload (or a profile-matched mix) for about 90% of the
  expected average output, sized by minimum variance on joint scenarios; review with real forward
  quotes and keep some volume unhedged for weather risk.
- *"Why not hedge 100%?"* Volume and shape: you would over-hedge in years when output is low or
  falls in cheap hours.
- *"Your hedge lost money in 2025. Was it a bad hedge?"* No: it was sold at a fair price and
  reduced risk; one year's P&L is not a measure of a hedge.
- *"Your forward is 85, the market says 113. What now?"* Re-anchor the level to the market and
  keep the simulation for shape and risk; the difference is the most important input to check.

---

## 10. How this maps to real work at Encavis

| In this project | In a company |
|---|---|
| Model forwards from scenarios | EEX settlement prices and a price forward curve (HPFC) from a vendor or the desk |
| Minimum-variance hedges on 496 scenarios | Hedge strategies with limits, liquidity and credit lines; rolling hedges over several years |
| Cal base, quarters, months | Cal, quarter, month and week products; peak and off-peak; profile products |
| Back-test with a naive forward | Back-tests and P&L attribution with real trade prices |
| Market check with secondary quotes | Daily market data feeds and model-vs-market reconciliation |

---

## 11. Your to-dos for Step 8

- [ ] Read sections 1 and 4. By hand: 5 MW sold at 100 EUR/MWh for 8,760 hours, spot averages 90:
      what is the hedge P&L? (EUR 0.44 m.)
- [ ] In the notebook, 8.2: find the hedge size where the solar park's CFaR is lowest.
- [ ] Exercises 1-4 in `exercises/step08_hedging.py`; check them in "My solutions: Step 8".
- [x] Decide whether to re-anchor the forward to the market: done in v1.1 (section 4.6).
- [ ] **Commit Step 8** (commands below).
- [ ] **German vocabulary of this step:** die Absicherung, das Termingeschäft, der Terminkontrakt
      (Future), das Grundlastprodukt (Base), das Spitzenlastprodukt (Peak), die Absicherungsquote
      (hedge ratio), die Varianz, die Wirksamkeit (effectiveness), der Terminaufschlag (forward
      premium), die Glattstellung, die Lieferperiode.

Commit (check `git status` first: no `.env`, no ` M .env.example`):

```bash
cd ".../Encavis quantitative/ppa-lab"
git status --short
git add src tests exercises config reports docs notebooks app METHODOLOGY.md README.md CHANGELOG.md Makefile pyproject.toml
git status --short
git commit -m "feat(hedging): futures hedges, buyer's hedge, back-test and market check (PPA-8)"
git push
gh run watch
```

---

## 12. Glossary

| Term | Meaning |
|---|---|
| Future / forward | Contract to deliver power over a future period at a fixed price |
| Base / peak | All hours / Monday-Friday 08:00-20:00 |
| Hedge payoff | What a sold contract pays: Σ (F − spot) per MW |
| Minimum-variance hedge | The hedge amount that makes hedged revenue as stable as possible |
| Hedge ratio | MW sold / average output |
| Hedge effectiveness | Share of the revenue variance removed by the hedge |
| Over-hedging | Selling more than the exposure; the hedge then adds risk |
| Forward premium | Market forward minus expected spot |
| Settlement price | The exchange's official daily price of a contract |

## 13. Sources

- Ederington, L. H. (1979): The hedging performance of the new futures markets. *Journal of
  Finance* 34(1), 157-170 (minimum-variance hedge ratio).
- Hull, J. C. (2022): *Options, Futures, and Other Derivatives*, 11th ed. Pearson (hedging with futures).
- EEX: German power futures contract specifications (base, peak, delivery periods).
- Market quotes: [tacto.ai, electricity price page](https://www.tacto.ai/en/energy/electricity-price)
  (Cal-27 base 104.24 EUR/MWh, 31 Jul 2026); [power2market, markets page](https://www.power2market.com/en/markets)
  (Cal-27 base 113.45, peak 119.48 EUR/MWh, 28 Aug 2026). Secondary sources; replace with EEX settlements.
- Encavis preparation guide: hedging with baseload futures, minimum-variance hedge ratio.
