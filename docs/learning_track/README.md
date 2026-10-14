# Learning track: building ppa-lab like a quant on a commercial team

This folder is your study guide for the project. Each step has one page that explains
**what was built, why it was built that way, the market and maths behind it, and
how the same work is done inside a company like Encavis**. PDF versions are in
[`pdf/`](pdf/) (rebuild them with `make docs`).

## How to use a step's page

Work through each page in four passes. That is how the material sticks, and how you
become able to explain it in an interview.

1. **Read** the concepts section with a notebook next to you (about 60-90 minutes).
2. **Run** the hands-on commands and check that you get the same results. Then open
   the step's section in the playground notebook (`make notebook`) and change the
   🎛 Play parameters until the charts make sense to you.
3. **Change** something: do the exercises; break a test on purpose and fix it.
4. **Explain**: answer the quiz without looking, then say the 60-second interview
   story out loud, in English and once in German.

Tick the checklist at the end of each page. Do not move to the next step until you can
explain every box in your own words.

## Pages

| Step | Ticket | Page | Topic |
|---|---|---|---|
| 1 | PPA-1 | [step01_market_data_foundation.md](step01_market_data_foundation.md) | Power-market basics, time and units, a real data pipeline, data quality, reconciliation |
| 2 | PPA-2 | [step02_capture_prices.md](step02_capture_prices.md) | Capture prices and rates, cannibalisation, official market values, investigating reconciliation breaks |
| 3 | PPA-3 | [step03_ppa_structures.md](step03_ppa_structures.md) | PPA structures as cash flows, fair prices, options, an honest back-test |
| 4 | PPA-4 | [step04_weather_to_power.md](step04_weather_to_power.md) | ERA5 reanalysis, pvlib and windpowerlib site models, P50/P90 volume risk |
| 5 | PPA-5 | [step05_price_model.md](step05_price_model.md) | Stochastic price model: arcsinh transform, seasonality, mean reversion, calibration to a forward, validation |
| 6 | PPA-6 | [step06_joint_scenarios.md](step06_joint_scenarios.md) | Joint weather and price scenarios: the covariance of volume and price, a weather-price link with analog days, what ignoring it costs |
| 7 | PPA-7 | [step07_ppa_pricing.md](step07_ppa_pricing.md) | Pricing and risk: structures on scenarios, cash flow at risk, the buyer's premium after a hedge, the price stack, a ten-year price |
| 8 | PPA-8 | [step08_hedging.md](step08_hedging.md) | Hedging with futures: EEX products, the minimum-variance hedge, judging a hedge, the buyer's band, a market check of the forward |
| 9 | PPA-9 | [step09_memo_dashboard.md](step09_memo_dashboard.md) | Telling the result: a one-page memo, a dashboard with knobs, the README as a front page, deployment |

## Companions

- [`../data_dictionary.md`](../data_dictionary.md): every dataset, column, unit and convention.
- `notebooks/ppa_lab_playground.ipynb`: one living notebook, one section per day, with
  play cells and open-ended ideas. The **graded** exercises stay in `exercises/dayNN_*.py`;
  each step ends with a **✅ My solutions** block that imports your answers from there, runs
  the checks (✅ passed, ⏳ not solved yet, ❌ wrong) and extends your results.

## Conventions used in every page

- **Real-world note**: how the same task looks inside a utility or IPP.
- **Pitfall**: a mistake that costs real money if it reaches a pricing model.
- **Interview**: phrasing you can reuse when talking about this work.
- Code references point to files in this repository, e.g. `src/ppa_lab/timeutils.py`.
