# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-15 07:40 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The scenarios average
140.98 EUR/MWh in 2027. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

| Park       | Structure                                        | Strike (EUR/MWh)   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-------------------------------------------------|:-------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract)                           | spot               |                       4.9  |                 3.23 |                            1.67 | 34%               |
| Solar park | Pay-as-produced PPA                              | 89.13              |                       4.9  |                 4.48 |                            0.42 | 9%                |
| Solar park | Pay-as-produced, nothing paid at negative prices | 89.13              |                       4.48 |                 3.97 |                            0.52 | 12%               |
| Solar park | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       4.9  |                 3.36 |                            1.54 | 31%               |
| Solar park | Baseload PPA (band = average output)             | 140.98             |                       4.9  |                 4.28 |                            0.62 | 13%               |
| Wind park  | Merchant (no contract)                           | spot               |                      14.04 |                10.3  |                            3.74 | 27%               |
| Wind park  | Pay-as-produced PPA                              | 127.90             |                      14.04 |                12.89 |                            1.15 | 8%                |
| Wind park  | Pay-as-produced, nothing paid at negative prices | 127.90             |                      13.64 |                12.47 |                            1.17 | 9%                |
| Wind park  | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                      14.04 |                10.4  |                            3.64 | 26%               |
| Wind park  | Baseload PPA (band = average output)             | 140.98             |                      14.04 |                12.66 |                            1.38 | 10%               |

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

| Park       |   Fair price |   Premium, no hedge |   Premium after baseload hedge |   of which profile |   of which volume (and its link to price) |
|:-----------|-------------:|--------------------:|-------------------------------:|-------------------:|------------------------------------------:|
| Solar park |        89.13 |               28.51 |                           8.04 |               7.71 |                                      0.34 |
| Wind park  |       127.9  |               33.5  |                           4.44 |               1.07 |                                      3.38 |

## 3. Price stack 2027: from the forward to an indicative price

| Layer (EUR/MWh)                        |   Solar park |   Wind park |
|:---------------------------------------|-------------:|------------:|
| Forward (model average baseload price) |       140.98 |      140.98 |
| Shape: capture rate below 1            |       -51.85 |      -13.08 |
| = Fair pay-as-produced price           |        89.13 |      127.9  |
| − Profile and volume risk premium      |         8.04 |        4.44 |
| − Balancing and route to market        |         1.5  |        2    |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        78.59 |      120.45 |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; forwards as above, capture
rate flat unless stated; solar output degrades 0.5% per year. The risk
premium and costs per MWh of the first year are applied to every year (a simplification).

| Case                                   |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:---------------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                              |              61.12 |                    50.57 |             87.55 |                   80.1  |
| Capture rate -2 pp per year            |              54.1  |                    43.56 |             80.46 |                   73.01 |
| Capture rate -1 pp per year            |              57.61 |                    47.07 |             84    |                   76.56 |
| Capture rate +1 pp per year            |              64.63 |                    54.08 |             91.09 |                   83.64 |
| Forward −10%                           |              55.01 |                    44.46 |             78.79 |                   71.35 |
| Forward +10%                           |              67.23 |                    56.69 |             96.3  |                   88.86 |
| Analog days from the whole window      |              66.82 |                    56.28 |             87.99 |                   80.54 |
| Capture rate of the recent price level |              53.66 |                    43.11 |             86    |                   78.56 |

Last row: the capture rate of the recent price level (104.0 EUR/MWh, the analog pool's average), with all prices scaled to the forward (the usual shape-factor view). In the model the capture rate rises with the level, because hours near zero are lifted too; the forward lies outside the levels in the data, so both are shown (METHODOLOGY, section 12).

## 5. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **61.1 EUR/MWh** (first year: forward 141.0 × expected capture rate 0.63 = 89.1). After a profile and volume risk premium of 8.0 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **50.6 EUR/MWh**. Expected annual energy is 55.1 GWh (P50; one-year P90 51.5 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 1.67 m (merchant) to EUR 0.42 m per year: only volume risk is left.

## 6. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
