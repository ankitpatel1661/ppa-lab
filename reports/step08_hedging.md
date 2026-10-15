# Step 8 report: hedging with power futures

Generated 2026-10-15 14:10 UTC by `ppa-lab hedging`.

Inputs: the Step 7 scenarios for 2027 (496 scenarios,
analog days from 2025-10-01). Selling a product at its forward pays, per MW,
the sum over its hours of (forward − spot). Forwards below are the model's expected prices,
so every hedge is fair in expectation and only changes the spread.

## 1. The forward curve

| Product   |   Model forward (EUR/MWh) |
|:----------|--------------------------:|
| Cal base  |                    140.99 |
| Cal peak  |                    141.88 |
| Q1        |                    186.33 |
| Q2        |                    118.37 |
| Q3        |                    124.92 |
| Q4        |                    135.09 |

### Market check

| Product   |   Market quote (EUR/MWh) | Quote date   |   Model forward (EUR/MWh) |   Market − model | Source                                                                           |
|:----------|-------------------------:|:-------------|--------------------------:|-----------------:|:---------------------------------------------------------------------------------|
| cal_base  |                   104.24 | 2026-07-31   |                    140.99 |           -36.75 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   113.45 | 2026-08-28   |                    140.99 |           -27.54 | [link](https://www.power2market.com/en/markets) (www.power2market.com)           |
| cal_base  |                   135.8  | 2026-09-14   |                    140.99 |            -5.19 | [link](https://www.power2market.com/de/markets/de/termin) (www.power2market.com) |
| cal_base  |                   126.47 | 2026-09-29   |                    140.99 |           -14.52 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   140.21 | 2026-10-09   |                    140.99 |            -0.78 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |

The model's forward is the market: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The quotes show how fast the level moves: between 104.24 and 140.21 EUR/MWh from 2026-07-31 to 2026-10-09. A 10% move of the whole curve changes the solar park's ten-year indicative price by 5.5 EUR/MWh (Step 7), so an offer must be refreshed with the curve on the day of signing.

## 2. Hedging merchant output

What each park's revenue risk would be if it sold at spot, and with each hedge. Hedge ratio =
MW sold / average output in MW.

| Park       | Strategy                         |   Sold (MW, year average) | Hedge ratio   |   CFaR95 (EUR m) | CFaR reduction   | Variance removed   |
|:-----------|:---------------------------------|--------------------------:|:--------------|-----------------:|:-----------------|:-------------------|
| Solar park | No hedge (merchant)              |                       0   | 0%            |             3.68 | 0%               | 0%                 |
| Solar park | Cal base, 50% of average output  |                       6.9 | 50%           |             1.58 | 57%              | 80%                |
| Solar park | Cal base, 100% of average output |                      13.7 | 100%          |             1.29 | 65%              | 91%                |
| Solar park | Cal base, minimum-variance       |                      11.5 | 84%           |             0.94 | 74%              | 95%                |
| Solar park | Quarters, minimum-variance       |                      11.5 | 84%           |             0.9  | 76%              | 95%                |
| Solar park | Months, minimum-variance         |                      11.9 | 87%           |             0.74 | 80%              | 96%                |
| Wind park  | No hedge (merchant)              |                       0   | 0%            |             2.16 | 0%               | 0%                 |
| Wind park  | Cal base, 50% of average output  |                       3.6 | 50%           |             1.29 | 40%              | 66%                |
| Wind park  | Cal base, 100% of average output |                       7.3 | 100%          |             1.12 | 48%              | 82%                |
| Wind park  | Cal base, minimum-variance       |                       6.5 | 90%           |             1.05 | 51%              | 83%                |
| Wind park  | Quarters, minimum-variance       |                       7.3 | 100%          |             0.88 | 59%              | 86%                |
| Wind park  | Months, minimum-variance         |                       7.4 | 102%          |             0.7  | 68%              | 90%                |

For the solar park, the minimum-variance Cal base hedge sells
11.5 MW (84% of average output) and cuts the cash flow
at risk by 74%; quarters and months add little, and
their monthly amounts are noisy (some even negative): with 496 scenarios the
finer split mostly fits noise.

## 3. The PPA buyer's hedge

Step 7 assumed the buyer sells a band equal to the average output. The minimum-variance band
is smaller, because the parks produce more in cheap hours than a flat band:

| Park       |   Full band (MW) |   Premium, full band | Minimum-variance band (MW)   |   Premium, min-var band |
|:-----------|-----------------:|---------------------:|:-----------------------------|------------------------:|
| Solar park |            13.75 |                  8.3 | 11.41 (83%)                  |                    5.32 |
| Wind park  |             7.3  |                  5.5 | 6.99 (96%)                   |                    5.26 |

## 4. Back-test on history

Cal base sold for year Y at year Y-1's average spot price (a naive forward proxy), at the
minimum-variance ratio of the P50 average output; real futures quotes would replace the proxy.

| Park       |   Year |   Forward proxy (EUR/MWh) |   Realised base (EUR/MWh) |   Merchant (EUR m) |   Hedge P&L (EUR m) |   Hedged (EUR m) |
|:-----------|-------:|--------------------------:|--------------------------:|-------------------:|--------------------:|-----------------:|
| Solar park |   2024 |                     95.18 |                     78.51 |               5.69 |                1.69 |             7.38 |
| Solar park |   2025 |                     78.51 |                     89.32 |               6.15 |               -1.09 |             5.06 |
| Wind park  |   2024 |                     95.18 |                     78.51 |               4.15 |                0.96 |             5.11 |
| Wind park  |   2025 |                     78.51 |                     89.32 |               4.46 |               -0.62 |             3.84 |

Across the back-test years, solar park: merchant revenue moved by EUR 0.46 m between the years, hedged revenue by EUR 2.32 m; wind park: merchant revenue moved by EUR 0.31 m between the years, hedged revenue by EUR 1.27 m. A hedge can lose money in a single year,
and with a naive forward (last year's price) it can even add variation, because the proxy moves
against the realised price. Two years are an illustration, not evidence: the scenario results
in section 2 measure the risk.

## 5. Charts

![Cash flow at risk by hedge](figures/step08_cfar.png)

![Monthly hedge vs expected output](figures/step08_monthly_hedge.png)

![Revenue with and without the hedge](figures/step08_revenue.png)

Results for the memo and the dashboard: `data/processed/hedging.json`.
