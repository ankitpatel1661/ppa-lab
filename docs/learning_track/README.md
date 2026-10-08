# Learning track: building ppa-lab like a quant on a commercial team

This folder is your study guide for the project. Each day has one page that explains
**what was built, why it was built that way, the market and maths behind it, and
how the same work is done inside a company like Encavis**. PDF versions are in
[`pdf/`](pdf/) (rebuild them with `make docs`).

## How to use a day's page

Work through each page in four passes. That is how the material sticks, and how you
become able to explain it in an interview.

1. **Read** the concepts section with a notebook next to you (about 60-90 minutes).
2. **Run** the hands-on commands and check that you get the same results. Then open
   the day's section in the playground notebook (`make notebook`) and change the
   🎛 Play parameters until the charts make sense to you.
3. **Change** something: do the exercises; break a test on purpose and fix it.
4. **Explain**: answer the quiz without looking, then say the 60-second interview
   story out loud, in English and once in German.

Tick the checklist at the end of each page. Do not move to the next day until you can
explain every box in your own words.

## Pages

| Day | Ticket | Page | Topic |
|---|---|---|---|
| 1 | PPA-1 | [day01_market_data_foundation.md](day01_market_data_foundation.md) | Power-market basics, time and units, a real data pipeline, data quality, reconciliation |
| 2 | PPA-2 | [day02_capture_prices.md](day02_capture_prices.md) | Capture prices and rates, cannibalisation, official market values, investigating reconciliation breaks |
| 3 | PPA-3 | (next) | PPA pricing maths: pay-as-produced, baseload, CfD, floors |

## Companions

- [`../data_dictionary.md`](../data_dictionary.md): every dataset, column, unit and convention.
- `notebooks/ppa_lab_playground.ipynb`: one living notebook, one section per day, with
  play cells and open-ended ideas. The **graded** exercises stay in `exercises/dayNN_*.py`;
  each day ends with a **✅ My solutions** block that imports your answers from there, runs
  the checks (✅ passed, ⏳ not solved yet, ❌ wrong) and extends your results.

## Conventions used in every page

- **Real-world note**: how the same task looks inside a utility or IPP.
- **Pitfall**: a mistake that costs real money if it reaches a pricing model.
- **Interview**: phrasing you can reuse when talking about this work.
- Code references point to files in this repository, e.g. `src/ppa_lab/timeutils.py`.
