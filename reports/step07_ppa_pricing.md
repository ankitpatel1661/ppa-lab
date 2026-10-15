# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-15 08:38 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The scenarios average
140.98 EUR/MWh in 2027. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

| Park       | Structure                                        | Strike (EUR/MWh)   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-------------------------------------------------|:-------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract)                           | spot               |                       4.78 |                 3.11 |                            1.67 | 35%               |
| Solar park | Pay-as-produced PPA                              | 86.90              |                       4.78 |                 4.37 |                            0.41 | 9%                |
| Solar park | Pay-as-produced, nothing paid at negative prices | 86.90              |                       4.28 |                 3.74 |                            0.54 | 13%               |
| Solar park | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       4.78 |                 3.26 |                            1.52 | 32%               |
| Solar park | Baseload PPA (band = average output)             | 140.98             |                       4.78 |                 4.15 |                            0.63 | 13%               |
| Wind park  | Merchant (no contract)                           | spot               |                      14.35 |                10.62 |                            3.74 | 26%               |
| Wind park  | Pay-as-produced PPA                              | 130.74             |                      14.35 |                13.17 |                            1.18 | 8%                |
| Wind park  | Pay-as-produced, nothing paid at negative prices | 130.74             |                      13.87 |                12.68 |                            1.19 | 9%                |
| Wind park  | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                      14.35 |                10.73 |                            3.62 | 25%               |
| Wind park  | Baseload PPA (band = average output)             | 140.98             |                      14.35 |                12.89 |                            1.46 | 10%               |

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

| Park       |   Fair price |   Premium, no hedge |   Premium after baseload hedge |   of which profile |   of which volume (and its link to price) |
|:-----------|-------------:|--------------------:|-------------------------------:|-------------------:|------------------------------------------:|
| Solar park |        86.9  |               28.58 |                           8.4  |               7.74 |                                      0.66 |
| Wind park  |       130.74 |               33.76 |                           4.72 |               1.23 |                                      3.48 |

## 3. Price stack 2027: from the forward to an indicative price

| Layer (EUR/MWh)                        |   Solar park |   Wind park |
|:---------------------------------------|-------------:|------------:|
| Forward (model average baseload price) |       140.98 |      140.98 |
| Shape: capture rate below 1            |       -54.08 |      -10.24 |
| = Fair pay-as-produced price           |        86.9  |      130.74 |
| − Profile and volume risk premium      |         8.4  |        4.72 |
| − Balancing and route to market        |         1.5  |        2    |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        76    |      123.02 |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; forwards as above. Capture-rate
trend per year after 2027 (base case): solar park -1 pp, wind park +0 pp; solar output degrades
0.5% per year. The risk premium and costs per MWh of the first year
are applied to every year (a simplification).

| Case                                   |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:---------------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                              |              56.08 |                    45.18 |             89.49 |                   81.78 |
| Capture-rate trend 2 pp/yr steeper     |              49.06 |                    38.16 |             82.4  |                   74.69 |
| Capture-rate trend 1 pp/yr steeper     |              52.57 |                    41.67 |             85.95 |                   78.23 |
| Capture-rate trend 1 pp/yr flatter     |              59.59 |                    48.69 |             93.03 |                   85.32 |
| Forward −10%                           |              50.47 |                    39.57 |             80.54 |                   72.83 |
| Forward +10%                           |              61.69 |                    50.79 |             98.44 |                   90.73 |
| Analog days from the whole window      |              62.05 |                    51.16 |             89.76 |                   82.05 |
| Capture rate of the recent price level |              48.92 |                    38.03 |             87.76 |                   80.05 |

Last row: the capture rate of the recent price level (104.0 EUR/MWh, the analog pool's average), with all prices scaled to the forward (the usual shape-factor view). In the model the capture rate rises with the level, because hours near zero are lifted too; the forward lies outside the levels in the data, so both are shown (METHODOLOGY, section 12).

## 5. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **56.1 EUR/MWh** (first year: forward 141.0 × expected capture rate 0.62 = 86.9). After a profile and volume risk premium of 8.4 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **45.2 EUR/MWh**. Expected annual energy is 55.1 GWh (P50; one-year P90 51.5 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 1.67 m (merchant) to EUR 0.41 m per year: only volume risk is left.

## 6. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
