# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-15 14:10 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The scenarios average
140.99 EUR/MWh in 2027. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

| Park       | Structure                                        | Strike (EUR/MWh)   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-------------------------------------------------|:-------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract)                           | spot               |                      10.36 |                 6.68 |                            3.68 | 35%               |
| Solar park | Pay-as-produced PPA                              | 86.00              |                      10.36 |                 9.58 |                            0.77 | 7%                |
| Solar park | Pay-as-produced, nothing paid at negative prices | 86.00              |                       9.28 |                 8.13 |                            1.15 | 12%               |
| Solar park | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                      10.36 |                 7.05 |                            3.3  | 32%               |
| Solar park | Baseload PPA (band = average output)             | 140.99             |                      10.36 |                 9.07 |                            1.29 | 12%               |
| Wind park  | Merchant (no contract)                           | spot               |                       8.27 |                 6.1  |                            2.16 | 26%               |
| Wind park  | Pay-as-produced PPA                              | 129.34             |                       8.27 |                 7.31 |                            0.96 | 12%               |
| Wind park  | Pay-as-produced, nothing paid at negative prices | 129.34             |                       8.03 |                 7.09 |                            0.94 | 12%               |
| Wind park  | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       8.27 |                 6.15 |                            2.11 | 26%               |
| Wind park  | Baseload PPA (band = average output)             | 140.99             |                       8.27 |                 7.15 |                            1.12 | 14%               |

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

| Park       |   Fair price |   Premium, no hedge |   Premium after baseload hedge |   of which profile |   of which volume (and its link to price) |
|:-----------|-------------:|--------------------:|-------------------------------:|-------------------:|------------------------------------------:|
| Solar park |        86    |               28.91 |                            8.3 |               7.52 |                                      0.78 |
| Wind park  |       129.34 |               35.04 |                            5.5 |               1.86 |                                      3.65 |

## 3. Price stack 2027: from the forward to an indicative price

| Layer (EUR/MWh)                        |   Solar park |   Wind park |
|:---------------------------------------|-------------:|------------:|
| Forward (model average baseload price) |       140.99 |      140.99 |
| Shape: capture rate below 1            |       -54.99 |      -11.65 |
| = Fair pay-as-produced price           |        86    |      129.34 |
| − Profile and volume risk premium      |         8.3  |        5.5  |
| − Balancing and route to market        |         1.5  |        2    |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        75.19 |      120.83 |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; forwards as above. Capture-rate
trend per year after 2027 (base case): solar park -1 pp, wind park +0 pp; solar output degrades
0.5% per year. The risk premium and costs per MWh of the first year
are applied to every year (a simplification).

| Case                                   |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:---------------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                              |              55.46 |                    44.65 |             88.53 |                   80.02 |
| Capture-rate trend 2 pp/yr steeper     |              48.44 |                    37.64 |             81.44 |                   72.94 |
| Capture-rate trend 1 pp/yr steeper     |              51.95 |                    41.15 |             84.99 |                   76.48 |
| Capture-rate trend 1 pp/yr flatter     |              58.97 |                    48.16 |             92.07 |                   83.57 |
| Forward −10%                           |              49.91 |                    39.11 |             79.68 |                   71.17 |
| Forward +10%                           |              61    |                    50.2  |             97.38 |                   88.88 |
| Analog days from the whole window      |              61.25 |                    50.45 |             88.61 |                   80.11 |
| Capture rate of the recent price level |              48.27 |                    37.46 |             86.59 |                   78.08 |

Last row: the capture rate of the recent price level (104.0 EUR/MWh, the analog pool's average), with all prices scaled to the forward (the usual shape-factor view). In the model the capture rate rises with the level, because hours near zero are lifted too; the forward lies outside the levels in the data, so both are shown (METHODOLOGY, section 12).

## 5. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **55.5 EUR/MWh** (first year: forward 141.0 × expected capture rate 0.61 = 86.0). After a profile and volume risk premium of 8.3 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **44.7 EUR/MWh**. Expected annual energy is 120.9 GWh (P50; one-year P90 113.4 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 3.68 m (merchant) to EUR 0.77 m per year: only volume risk is left.

## 6. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
