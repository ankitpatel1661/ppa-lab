# Step 8 report: hedging with power futures

Generated 2026-11-03 14:27 UTC by `ppa-lab hedging`.

Inputs: the Step 7 scenarios for 2027 (496 scenarios,
analog days from 2025-10-01). Selling a product at its forward pays, per MW,
the sum over its hours of (forward − spot). Forwards below are the model's expected prices,
so every hedge is fair in expectation and only changes the spread.

## 1. The forward curve

| Product   |   Model forward (EUR/MWh) |
|:----------|--------------------------:|
| Cal base  |                    155.35 |
| Cal peak  |                    149.83 |
| Q1        |                    199.52 |
| Q2        |                    129.63 |
| Q3        |                    138.79 |
| Q4        |                    154.16 |

### Market check

| Product   |   Market quote (EUR/MWh) | Quote date   |   Model forward (EUR/MWh) |   Market − model | Source                                                                           |
|:----------|-------------------------:|:-------------|--------------------------:|-----------------:|:---------------------------------------------------------------------------------|
| cal_base  |                   104.24 | 2026-07-31   |                    155.35 |           -51.11 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   113.45 | 2026-08-28   |                    155.35 |           -41.9  | [link](https://www.power2market.com/en/markets) (www.power2market.com)           |
| cal_base  |                   135.8  | 2026-09-14   |                    155.35 |           -19.55 | [link](https://www.power2market.com/de/markets/de/termin) (www.power2market.com) |
| cal_base  |                   126.47 | 2026-09-29   |                    155.35 |           -28.88 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   130.92 | 2026-10-04   |                    155.35 |           -24.43 | [link](https://www.power2market.com/de/markets/de/termin) (www.power2market.com) |
| cal_base  |                   140.21 | 2026-10-09   |                    155.35 |           -15.14 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |
| cal_base  |                   154.42 | 2026-10-23   |                    155.35 |            -0.93 | [link](https://www.tacto.ai/en/energy/electricity-price) (www.tacto.ai)          |

The model's forward is the market: EEX German Power Cal-27 base 154.42 EUR/MWh (quote of 2026-10-23, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 198.4 / 128.8 / 137.9 / 153.2, quotes of 2026-10-04); later years follow the forward curve (2028: 113.94, 2029: 87.93), held flat after 2029. The quotes show how fast the level moves: between 104.24 and 154.42 EUR/MWh from 2026-07-31 to 2026-10-23. A 10% move of the whole curve changes the solar park's ten-year indicative price by 5.7 EUR/MWh (Step 7), so an offer must be refreshed with the curve on the day of signing.

## 2. Hedging merchant output

What each park's revenue risk would be if it sold at spot, and with each hedge. Selling at spot,
a park stops producing at negative prices (Step 7, section 5). Hedge ratio = MW sold / average
output sold in MW.

| Park       | Strategy                         |   Sold (MW, year average) | Hedge ratio   |   CFaR95 (EUR m) | CFaR reduction   | Variance removed   |
|:-----------|:---------------------------------|--------------------------:|:--------------|-----------------:|:-----------------|:-------------------|
| Solar park | No hedge (merchant)              |                       0   | 0%            |             3.24 | 0%               | 0%                 |
| Solar park | Cal base, 50% of average output  |                       5.9 | 50%           |             1.44 | 55%              | 78%                |
| Solar park | Cal base, 100% of average output |                      11.7 | 100%          |             1.2  | 63%              | 91%                |
| Solar park | Cal base, minimum-variance       |                       9.9 | 84%           |             0.92 | 72%              | 94%                |
| Solar park | Quarters, minimum-variance       |                       9.9 | 84%           |             0.89 | 73%              | 94%                |
| Solar park | Months, minimum-variance         |                      10.2 | 87%           |             0.75 | 77%              | 96%                |
| Wind park  | No hedge (merchant)              |                       0   | 0%            |             2.24 | 0%               | 0%                 |
| Wind park  | Cal base, 50% of average output  |                       3.5 | 50%           |             1.41 | 37%              | 64%                |
| Wind park  | Cal base, 100% of average output |                       7   | 100%          |             1.17 | 48%              | 80%                |
| Wind park  | Cal base, minimum-variance       |                       6.4 | 92%           |             1.15 | 49%              | 81%                |
| Wind park  | Quarters, minimum-variance       |                       7.3 | 104%          |             0.97 | 57%              | 85%                |
| Wind park  | Months, minimum-variance         |                       7.4 | 105%          |             0.77 | 66%              | 89%                |

For the solar park, the minimum-variance Cal base hedge sells
9.9 MW (84% of average output) and cuts the cash flow
at risk by 72%; quarters and months add little, and
their monthly amounts are noisy (some even negative): with 496 scenarios the
finer split mostly fits noise.

## 3. The PPA buyer's hedge

Step 7 assumed the buyer sells a band equal to the average output. The minimum-variance band
is smaller, because the parks produce more in cheap hours than a flat band:

| Park       |   Full band (MW) |   Premium, full band | Minimum-variance band (MW)   |   Premium, min-var band |
|:-----------|-----------------:|---------------------:|:-----------------------------|------------------------:|
| Solar park |            13.75 |                11.42 | 10.33 (75%)                  |                    4.96 |
| Wind park  |             7.3  |                 5.64 | 6.98 (96%)                   |                    5.58 |

## 4. Back-test on history

Cal base sold for year Y at year Y-1's average spot price (a naive forward proxy), at the
minimum-variance ratio of the P50 average output; real futures quotes would replace the proxy.

| Park       |   Year |   Forward proxy (EUR/MWh) |   Realised base (EUR/MWh) |   Merchant (EUR m) |   Hedge P&L (EUR m) |   Hedged (EUR m) |
|:-----------|-------:|--------------------------:|--------------------------:|-------------------:|--------------------:|-----------------:|
| Solar park |   2024 |                     95.18 |                     78.51 |               5.69 |                1.71 |             7.4  |
| Solar park |   2025 |                     78.51 |                     89.32 |               6.15 |               -1.1  |             5.05 |
| Wind park  |   2024 |                     95.18 |                     78.51 |               4.15 |                0.98 |             5.13 |
| Wind park  |   2025 |                     78.51 |                     89.32 |               4.46 |               -0.63 |             3.83 |

Across the back-test years, solar park: merchant revenue moved by EUR 0.46 m between the years, hedged revenue by EUR 2.35 m; wind park: merchant revenue moved by EUR 0.31 m between the years, hedged revenue by EUR 1.31 m. A hedge can lose money in a single year,
and with a naive forward (last year's price) it can even add variation, because the proxy moves
against the realised price. Two years are an illustration, not evidence: the scenario results
in section 2 measure the risk.

## 5. Charts

![Cash flow at risk by hedge](figures/step08_cfar.png)

![Monthly hedge vs expected output](figures/step08_monthly_hedge.png)

![Revenue with and without the hedge](figures/step08_revenue.png)

Results for the memo and the dashboard: `data/processed/hedging.json`.
