# Step 8 report: hedging with power futures

Generated 2026-10-14 08:13 UTC by `ppa-lab hedging`.

Inputs: the Step 7 scenarios for 2027 (496 scenarios,
analog days from 2025-10-01). Selling a product at its forward pays, per MW,
the sum over its hours of (forward − spot). Forwards below are the model's expected prices,
so every hedge is fair in expectation and only changes the spread.

## 1. The forward curve

| Product   |   Model forward (EUR/MWh) |
|:----------|--------------------------:|
| Cal base  |                     85.42 |
| Cal peak  |                     86.09 |
| Q1        |                     86.39 |
| Q2        |                     71.17 |
| Q3        |                     87.47 |
| Q4        |                     96.53 |

### Market check

| Product   |   Market quote (EUR/MWh) | Quote date   |   Model forward (EUR/MWh) |   Market − model | Source                                                                  |
|:----------|-------------------------:|:-------------|--------------------------:|-----------------:|:------------------------------------------------------------------------|
| cal_base  |                   104.24 | 2026-07-31   |                     85.42 |            18.82 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai) |
| cal_base  |                   113.45 | 2026-08-28   |                     85.42 |            28.03 | [link](https://www.power2market.com/en/markets) (www.power2market.com)  |
| cal_peak  |                   119.48 | 2026-08-28   |                     86.09 |            33.39 | [link](https://www.power2market.com/en/markets) (www.power2market.com)  |

The model is calibrated to the assumed forward of 85
EUR/MWh; the published quotes are higher. At the latest market quote, with the same capture
rate, premium and costs (the dashboard's forward knob):

- Solar park: indicative 33.3 EUR/MWh at the model forward 85.4; **46.8 EUR/MWh** at the market quote 113.45 (2026-08-28)
- Wind park: indicative 68.4 EUR/MWh at the model forward 85.4; **93.0 EUR/MWh** at the market quote 113.45 (2026-08-28)

## 2. Hedging merchant output

What each park's revenue risk would be if it sold at spot, and with each hedge. Hedge ratio =
MW sold / average output in MW.

| Park       | Strategy                         |   Sold (MW, year average) | Hedge ratio   |   CFaR95 (EUR m) | CFaR reduction   | Variance removed   |
|:-----------|:---------------------------------|--------------------------:|:--------------|-----------------:|:-----------------|:-------------------|
| Solar park | No hedge (merchant)              |                       0   | 0%            |             1.44 | 0%               | 0%                 |
| Solar park | Cal base, 50% of average output  |                       3.1 | 50%           |             0.68 | 53%              | 78%                |
| Solar park | Cal base, 100% of average output |                       6.3 | 100%          |             0.35 | 75%              | 96%                |
| Solar park | Cal base, minimum-variance       |                       5.6 | 89%           |             0.27 | 81%              | 97%                |
| Solar park | Quarters, minimum-variance       |                       5.6 | 90%           |             0.25 | 83%              | 98%                |
| Solar park | Months, minimum-variance         |                       5.7 | 90%           |             0.23 | 84%              | 98%                |
| Wind park  | No hedge (merchant)              |                       0   | 0%            |             2.95 | 0%               | 0%                 |
| Wind park  | Cal base, 50% of average output  |                       6.3 | 50%           |             1.52 | 49%              | 74%                |
| Wind park  | Cal base, 100% of average output |                      12.5 | 100%          |             0.88 | 70%              | 93%                |
| Wind park  | Cal base, minimum-variance       |                      11.7 | 93%           |             0.74 | 75%              | 94%                |
| Wind park  | Quarters, minimum-variance       |                      11.7 | 93%           |             0.73 | 75%              | 95%                |
| Wind park  | Months, minimum-variance         |                      11.7 | 93%           |             0.67 | 77%              | 95%                |

For the solar park, the minimum-variance Cal base hedge sells
5.6 MW (89% of average output) and cuts the cash flow
at risk by 81%; quarters and months add little, and
their monthly amounts are noisy (some even negative): with 496 scenarios the
finer split mostly fits noise.

## 3. The PPA buyer's hedge

Step 7 assumed the buyer sells a band equal to the average output. The minimum-variance band
is smaller, because the parks produce more in cheap hours than a flat band:

| Park       |   Full band (MW) |   Premium, full band | Minimum-variance band (MW)   |   Premium, min-var band |
|:-----------|-----------------:|---------------------:|:-----------------------------|------------------------:|
| Solar park |             6.28 |                 5.27 | 5.64 (90%)                   |                    4.45 |
| Wind park  |            12.53 |                 3.39 | 11.96 (95%)                  |                    2.92 |

## 4. Back-test on history

Cal base sold for year Y at year Y-1's average spot price (a naive forward proxy), at the
minimum-variance ratio of the P50 average output; real futures quotes would replace the proxy.

| Park       |   Year |   Forward proxy (EUR/MWh) |   Realised base (EUR/MWh) |   Merchant (EUR m) |   Hedge P&L (EUR m) |   Hedged (EUR m) |
|:-----------|-------:|--------------------------:|--------------------------:|-------------------:|--------------------:|-----------------:|
| Solar park |   2024 |                     95.18 |                     78.51 |               2.79 |                0.82 |             3.61 |
| Solar park |   2025 |                     78.51 |                     89.32 |               2.88 |               -0.53 |             2.34 |
| Wind park  |   2024 |                     95.18 |                     78.51 |               7.19 |                1.71 |             8.9  |
| Wind park  |   2025 |                     78.51 |                     89.32 |               8.13 |               -1.11 |             7.03 |

Across the back-test years, solar park: merchant revenue moved by EUR 0.09 m between the years, hedged revenue by EUR 1.27 m; wind park: merchant revenue moved by EUR 0.95 m between the years, hedged revenue by EUR 1.87 m. A hedge can lose money in a single year,
and with a naive forward (last year's price) it can even add variation, because the proxy moves
against the realised price. Two years are an illustration, not evidence: the scenario results
in section 2 measure the risk.

## 5. Charts

![Cash flow at risk by hedge](figures/step08_cfar.png)

![Monthly hedge vs expected output](figures/step08_monthly_hedge.png)

![Revenue with and without the hedge](figures/step08_revenue.png)

Results for the memo and the dashboard: `data/processed/hedging.json`.
