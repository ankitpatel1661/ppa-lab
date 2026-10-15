# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-15 20:50 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The scenarios average
141.06 EUR/MWh in 2027. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

| Park       | Structure                                        | Strike (EUR/MWh)   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-------------------------------------------------|:-------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract)                           | spot               |                       9.34 |                 6.09 |                            3.24 | 35%               |
| Solar park | Pay-as-produced PPA                              | 77.53              |                       9.34 |                 8.64 |                            0.7  | 7%                |
| Solar park | Pay-as-produced, nothing paid at negative prices | 77.53              |                       7.7  |                 6.68 |                            1.02 | 13%               |
| Solar park | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       9.34 |                 6.32 |                            3.02 | 32%               |
| Solar park | Baseload PPA (band = average output)             | 141.06             |                       9.34 |                 7.92 |                            1.42 | 15%               |
| Wind park  | Merchant (no contract)                           | spot               |                       8.31 |                 6.18 |                            2.13 | 26%               |
| Wind park  | Pay-as-produced PPA                              | 129.94             |                       8.31 |                 7.34 |                            0.96 | 12%               |
| Wind park  | Pay-as-produced, nothing paid at negative prices | 129.94             |                       7.94 |                 7.01 |                            0.93 | 12%               |
| Wind park  | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       8.31 |                 6.2  |                            2.1  | 25%               |
| Wind park  | Baseload PPA (band = average output)             | 141.06             |                       8.31 |                 7.19 |                            1.11 | 13%               |

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

| Park       |   Fair price |   Premium, no hedge |   Premium after baseload hedge |   of which profile |   of which volume (and its link to price) |
|:-----------|-------------:|--------------------:|-------------------------------:|-------------------:|------------------------------------------:|
| Solar park |        77.53 |               25.44 |                          10.54 |              10.11 |                                      0.43 |
| Wind park  |       129.94 |               34.81 |                           5.49 |               1.95 |                                      3.55 |

## 3. Price stack 2027: from the forward to an indicative price

| Layer (EUR/MWh)                        |   Solar park |   Wind park |
|:---------------------------------------|-------------:|------------:|
| Forward (model average baseload price) |       141.06 |      141.06 |
| Shape: capture rate below 1            |       -63.54 |      -11.12 |
| = Fair pay-as-produced price           |        77.53 |      129.94 |
| − Profile and volume risk premium      |        10.54 |        5.49 |
| − Balancing and route to market        |         1.5  |        2    |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        64.48 |      121.45 |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; forwards as above. Capture-rate
trend per year after 2027 (base case): solar park -1 pp, wind park +0 pp; solar output degrades
0.5% per year. The risk premium and costs per MWh of the first year
are applied to every year (a simplification).

| Case                                              |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:--------------------------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                                         |              41.15 |                    28.1  |             86.64 |                   78.15 |
| Capture-rate trend 2 pp/yr steeper                |              34.13 |                    21.09 |             79.55 |                   71.06 |
| Capture-rate trend 1 pp/yr steeper                |              37.64 |                    24.6  |             83.09 |                   74.6  |
| Capture-rate trend 1 pp/yr flatter                |              44.65 |                    31.61 |             90.18 |                   81.69 |
| Forward −10%                                      |              34.29 |                    21.25 |             77.22 |                   68.73 |
| Forward +10%                                      |              47.92 |                    34.88 |             96.02 |                   87.53 |
| Analog days from the whole window                 |              41.11 |                    28.07 |             87.06 |                   78.57 |
| Capture rate vs price level: low end of history   |              42.62 |                    29.58 |             87.83 |                   79.33 |
| Capture rate vs price level: high end of history  |              40.49 |                    27.45 |             86.36 |                   77.87 |
| Capture rate less the model's out-of-sample error |              38.37 |                    25.33 |             82.35 |                   73.86 |

Each year's capture rate moves with that year's forward along the model's own response to the price level (section 5), on top of the trend. The two rows on the capture rate vs price level use history's 95% interval for that slope instead, from the recent level (105 EUR/MWh): a flatter slope gives a lower capture rate at the high 2027 forward but a higher one once the curve falls below the recent level. The last row takes the model's mean out-of-sample capture-rate error off every year (solar park +0.029, wind park +0.044; test years 2025, 2026, fitted like 2027; Step 6, section 4): fitted on the years before, the model overstated capture rates even with the price level given. The 2027 scenarios carry history's build-out trend up to 2027 (Step 6, section 4); continued for one more year at the same forward it would move the capture rate by solar park −5.6 pp, wind park +0.3 pp. The base case assumes solar park -1 pp, wind park +0 pp a year after that: storage, flexible demand and curtailment are expected to slow the fall, and a straight line would take solar's capture rate towards zero within a decade (the −2 pp row is the steeper view).

## 5. Does the capture rate rise with the price level?

The price model shifts all hours together in arcsinh units, so a higher price level lifts the hours near zero and solar's capture rate rises with it. The usual shape-factor view scales all hours instead, and the capture rate stays put. The 2027 forward (141 EUR/MWh) lies above the recent level (105) and the curve falls to 88, so the answer moves the price.

History decides: monthly capture rates regressed on ln(average price), with month effects and the technology's share of load (its build-out) held fixed; HC1 standard errors (`analysis/level_effect.py`). The model's slope comes from rebuilding the scenarios at each forward with the same random draws.

| Change of capture rate per unit of ln(price) | Solar park | Wind park |
|---|---|---|
| History 2023-2026: slope (95% interval) | 0.27 (0.10 to 0.45) | 0.02 (−0.09 to 0.14) |
| t-statistic; months | 3.1; 45 | 0.4; 45 |
| History 2021-2026, all years | 0.10 (0.06 to 0.13) | 0.00 (−0.04 to 0.04) |
| Model: recent level (105) to forward 2027 | 0.22 | 0.06 |
| Model: over the tenor's forwards (88 to 141) | 0.24 | 0.07 |

**Solar park**: the capture rate rises with the price level (slope 0.27, t = 3.1), so the shape-factor view (slope 0) is rejected; the model's 0.22 lies inside the 95% interval. **Wind park**: history cannot tell the slope from zero (0.02, t = 0.4); the model's 0.06 lies inside the 95% interval.

Build-out, from the same regression at a fixed price level: solar park −2.90 per unit of its share of load, which grew 1.3 pp a year in 2022-2025: −3.7 pp of capture rate a year (base-case trend −1 pp); wind park −0.36 per unit of its share of load, which grew 0.8 pp a year in 2022-2025: −0.3 pp of capture rate a year (base-case trend +0 pp). The trend assumes that storage, flexible demand and curtailment slow solar's fall; the −2 pp row of section 4 is closer to history's pace.

So the base case moves each year's capture rate along the model's response (chart below); holding the first year's capture rate over the tenor instead (as before v1.5) would give fair prices of solar park 49.6, wind park 88.9 EUR/MWh.

![Capture rate vs price level](figures/step07_level_effect.png)

## 6. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **41.1 EUR/MWh** (first year: forward 141.1 × expected capture rate 0.55 = 77.5). After a profile and volume risk premium of 10.5 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **28.1 EUR/MWh**. Expected annual energy is 120.9 GWh (P50; one-year P90 113.4 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 3.24 m (merchant) to EUR 0.70 m per year: only volume risk is left.

## 7. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
