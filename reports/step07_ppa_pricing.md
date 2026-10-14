# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-14 07:52 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward assumption 85.0 EUR/MWh; the scenarios average
85.42 EUR/MWh. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

| Park       | Structure                                        | Strike (EUR/MWh)   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-------------------------------------------------|:-------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract)                           | spot               |                       2.26 |                 0.82 |                            1.44 | 64%               |
| Solar park | Pay-as-produced PPA                              | 41.08              |                       2.26 |                 2.06 |                            0.2  | 9%                |
| Solar park | Pay-as-produced, nothing paid at negative prices | 41.08              |                       1.69 |                 1.36 |                            0.32 | 19%               |
| Solar park | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       2.26 |                 1.19 |                            1.07 | 47%               |
| Solar park | Baseload PPA (band = average output)             | 85.42              |                       2.26 |                 1.91 |                            0.35 | 16%               |
| Wind park  | Merchant (no contract)                           | spot               |                       8.21 |                 5.27 |                            2.95 | 36%               |
| Wind park  | Pay-as-produced PPA                              | 74.81              |                       8.21 |                 7.54 |                            0.68 | 8%                |
| Wind park  | Pay-as-produced, nothing paid at negative prices | 74.81              |                       7.44 |                 6.7  |                            0.74 | 10%               |
| Wind park  | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       8.21 |                 5.49 |                            2.72 | 33%               |
| Wind park  | Baseload PPA (band = average output)             | 85.42              |                       8.21 |                 7.34 |                            0.88 | 11%               |

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

| Park       |   Fair price |   Premium, no hedge |   Premium after baseload hedge |   of which profile |   of which volume (and its link to price) |
|:-----------|-------------:|--------------------:|-------------------------------:|-------------------:|------------------------------------------:|
| Solar park |        41.08 |               25.23 |                           5.27 |               4.96 |                                      0.32 |
| Wind park  |        74.81 |               27.88 |                           3.39 |               0.88 |                                      2.5  |

## 3. Price stack 2027: from the forward to an indicative price

| Layer (EUR/MWh)                        |   Solar park |   Wind park |
|:---------------------------------------|-------------:|------------:|
| Forward (model average baseload price) |        85.42 |       85.42 |
| Shape: capture rate below 1            |       -44.34 |      -10.61 |
| = Fair pay-as-produced price           |        41.08 |       74.81 |
| − Profile and volume risk premium      |         5.27 |        3.39 |
| − Balancing and route to market        |         1.5  |        2    |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        33.31 |       68.43 |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; flat forward and capture rate
unless stated; solar output degrades 0.5% per year. The risk premium
and costs per MWh of the first year are applied to every year (a simplification).

| Case                              |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:----------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                         |              41.08 |                    33.31 |             74.81 |                   68.43 |
| Capture rate -2 pp per year       |              34.28 |                    26.51 |             67.94 |                   61.56 |
| Capture rate -1 pp per year       |              37.68 |                    29.91 |             71.38 |                   64.99 |
| Capture rate +1 pp per year       |              44.48 |                    36.71 |             78.25 |                   71.86 |
| Forward −10%                      |              36.97 |                    29.2  |             67.33 |                   60.95 |
| Forward +10%                      |              45.19 |                    37.42 |             82.3  |                   75.91 |
| Analog days from the whole window |              48.66 |                    40.89 |             75.35 |                   68.97 |

## 5. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **41.1 EUR/MWh** (first year: forward 85.4 × expected capture rate 0.48 = 41.1). After a profile and volume risk premium of 5.3 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **33.3 EUR/MWh**. Expected annual energy is 55.1 GWh (P50; one-year P90 51.5 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 1.44 m (merchant) to EUR 0.20 m per year: only volume risk is left.

## 6. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
