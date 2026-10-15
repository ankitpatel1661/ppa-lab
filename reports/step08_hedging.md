# Step 8 report: hedging with power futures

Generated 2026-10-15 07:41 UTC by `ppa-lab hedging`.

Inputs: the Step 7 scenarios for 2027 (496 scenarios,
analog days from 2025-10-01). Selling a product at its forward pays, per MW,
the sum over its hours of (forward − spot). Forwards below are the model's expected prices,
so every hedge is fair in expectation and only changes the spread.

## 1. The forward curve

| Product   |   Model forward (EUR/MWh) |
|:----------|--------------------------:|
| Cal base  |                    140.98 |
| Cal peak  |                    142.29 |
| Q1        |                    141.36 |
| Q2        |                    124.25 |
| Q3        |                    144.14 |
| Q4        |                    153.99 |

### Market check

| Product   |   Market quote (EUR/MWh) | Quote date   |   Model forward (EUR/MWh) |   Market − model | Source                                                                           |
|:----------|-------------------------:|:-------------|--------------------------:|-----------------:|:---------------------------------------------------------------------------------|
| cal_base  |                   104.24 | 2026-07-31   |                    140.98 |           -36.74 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   113.45 | 2026-08-28   |                    140.98 |           -27.53 | [link](https://www.power2market.com/en/markets) (www.power2market.com)           |
| cal_base  |                   135.8  | 2026-09-14   |                    140.98 |            -5.18 | [link](https://www.power2market.com/de/markets/de/termin) (www.power2market.com) |
| cal_base  |                   126.47 | 2026-09-29   |                    140.98 |           -14.51 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   140.21 | 2026-10-09   |                    140.98 |            -0.77 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |

The model's forward is the market: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The quotes show how fast the level moves: between 104.24 and 140.21 EUR/MWh from 2026-07-31 to 2026-10-09. A 10% move of the whole curve changes the solar park's ten-year indicative price by 6.1 EUR/MWh (Step 7), so an offer must be refreshed with the curve on the day of signing.

## 2. Hedging merchant output

What each park's revenue risk would be if it sold at spot, and with each hedge. Hedge ratio =
MW sold / average output in MW.

| Park       | Strategy                         |   Sold (MW, year average) | Hedge ratio   |   CFaR95 (EUR m) | CFaR reduction   | Variance removed   |
|:-----------|:---------------------------------|--------------------------:|:--------------|-----------------:|:-----------------|:-------------------|
| Solar park | No hedge (merchant)              |                       0   | 0%            |             1.67 | 0%               | 0%                 |
| Solar park | Cal base, 50% of average output  |                       3.1 | 50%           |             0.75 | 55%              | 80%                |
| Solar park | Cal base, 100% of average output |                       6.3 | 100%          |             0.62 | 63%              | 91%                |
| Solar park | Cal base, minimum-variance       |                       5.2 | 83%           |             0.37 | 78%              | 95%                |
| Solar park | Quarters, minimum-variance       |                       5.2 | 82%           |             0.39 | 77%              | 95%                |
| Solar park | Months, minimum-variance         |                       5.3 | 84%           |             0.35 | 79%              | 97%                |
| Wind park  | No hedge (merchant)              |                       0   | 0%            |             3.74 | 0%               | 0%                 |
| Wind park  | Cal base, 50% of average output  |                       6.3 | 50%           |             1.96 | 48%              | 71%                |
| Wind park  | Cal base, 100% of average output |                      12.5 | 100%          |             1.38 | 63%              | 89%                |
| Wind park  | Cal base, minimum-variance       |                      11.4 | 91%           |             1.19 | 68%              | 89%                |
| Wind park  | Quarters, minimum-variance       |                      11.5 | 92%           |             1.19 | 68%              | 91%                |
| Wind park  | Months, minimum-variance         |                      11.5 | 91%           |             1.1  | 71%              | 92%                |

For the solar park, the minimum-variance Cal base hedge sells
5.2 MW (83% of average output) and cuts the cash flow
at risk by 78%; quarters and months add little, and
their monthly amounts are noisy (some even negative): with 496 scenarios the
finer split mostly fits noise.

## 3. The PPA buyer's hedge

Step 7 assumed the buyer sells a band equal to the average output. The minimum-variance band
is smaller, because the parks produce more in cheap hours than a flat band:

| Park       |   Full band (MW) |   Premium, full band | Minimum-variance band (MW)   |   Premium, min-var band |
|:-----------|-----------------:|---------------------:|:-----------------------------|------------------------:|
| Solar park |             6.28 |                 8.04 | 5.25 (84%)                   |                    4.76 |
| Wind park  |            12.53 |                 4.44 | 11.80 (94%)                  |                    3.54 |

## 4. Back-test on history

Cal base sold for year Y at year Y-1's average spot price (a naive forward proxy), at the
minimum-variance ratio of the P50 average output; real futures quotes would replace the proxy.

| Park       |   Year |   Forward proxy (EUR/MWh) |   Realised base (EUR/MWh) |   Merchant (EUR m) |   Hedge P&L (EUR m) |   Hedged (EUR m) |
|:-----------|-------:|--------------------------:|--------------------------:|-------------------:|--------------------:|-----------------:|
| Solar park |   2024 |                     95.18 |                     78.51 |               2.79 |                0.76 |             3.55 |
| Solar park |   2025 |                     78.51 |                     89.32 |               2.88 |               -0.49 |             2.38 |
| Wind park  |   2024 |                     95.18 |                     78.51 |               7.19 |                1.67 |             8.86 |
| Wind park  |   2025 |                     78.51 |                     89.32 |               8.13 |               -1.08 |             7.05 |

Across the back-test years, solar park: merchant revenue moved by EUR 0.09 m between the years, hedged revenue by EUR 1.17 m; wind park: merchant revenue moved by EUR 0.95 m between the years, hedged revenue by EUR 1.80 m. A hedge can lose money in a single year,
and with a naive forward (last year's price) it can even add variation, because the proxy moves
against the realised price. Two years are an illustration, not evidence: the scenario results
in section 2 measure the risk.

## 5. Charts

![Cash flow at risk by hedge](figures/step08_cfar.png)

![Monthly hedge vs expected output](figures/step08_monthly_hedge.png)

![Revenue with and without the hedge](figures/step08_revenue.png)

Results for the memo and the dashboard: `data/processed/hedging.json`.
