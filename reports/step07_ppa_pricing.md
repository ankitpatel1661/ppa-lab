# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-15 19:37 UTC by `ppa-lab pricing`.

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

| Case                                             |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:-------------------------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                                        |              45.66 |                    34.85 |             85.85 |                   77.35 |
| Capture-rate trend 2 pp/yr steeper               |              38.64 |                    27.84 |             78.76 |                   70.26 |
| Capture-rate trend 1 pp/yr steeper               |              42.15 |                    31.35 |             82.31 |                   73.8  |
| Capture-rate trend 1 pp/yr flatter               |              49.17 |                    38.36 |             89.39 |                   80.89 |
| Forward −10%                                     |              37.72 |                    26.92 |             76.33 |                   67.83 |
| Forward +10%                                     |              53.38 |                    42.58 |             95.3  |                   86.8  |
| Analog days from the whole window                |              51.45 |                    40.65 |             85.93 |                   77.43 |
| Capture rate vs price level: low end of history  |              47.66 |                    36.86 |             87.17 |                   78.66 |
| Capture rate vs price level: high end of history |              45.56 |                    34.75 |             85.72 |                   77.22 |

Each year's capture rate moves with that year's forward along the model's own response to the price level (section 5), on top of the trend. The last two rows use history's 95% interval for that slope instead, from the recent level (105 EUR/MWh): a flatter slope gives a lower capture rate at the high 2027 forward but a higher one once the curve falls below the recent level.

## 5. Does the capture rate rise with the price level?

The price model shifts all hours together in arcsinh units, so a higher price level lifts the hours near zero and solar's capture rate rises with it. The usual shape-factor view scales all hours instead, and the capture rate stays put. The 2027 forward (141 EUR/MWh) lies above the recent level (105) and the curve falls to 88, so the answer moves the price.

History decides: monthly capture rates regressed on ln(average price), with month effects and the technology's share of load (its build-out) held fixed; HC1 standard errors (`analysis/level_effect.py`). The model's slope comes from rebuilding the scenarios at each forward with the same random draws.

| Change of capture rate per unit of ln(price) | Solar park | Wind park |
|---|---|---|
| History 2023-2026: slope (95% interval) | 0.27 (0.10 to 0.45) | 0.02 (−0.09 to 0.14) |
| t-statistic; months | 3.1; 45 | 0.4; 45 |
| History 2021-2026, all years | 0.10 (0.06 to 0.13) | 0.00 (−0.04 to 0.04) |
| Model: recent level (105) to forward 2027 | 0.25 | 0.07 |
| Model: over the tenor's forwards (88 to 141) | 0.28 | 0.08 |

**Solar park**: the capture rate rises with the price level (slope 0.27, t = 3.1), so the shape-factor view (slope 0) is rejected; the model's 0.25 lies inside the 95% interval. **Wind park**: history cannot tell the slope from zero (0.02, t = 0.4); the model's 0.07 lies inside the 95% interval.

Build-out, from the same regression at a fixed price level: solar park −2.90 per unit of its share of load, which grew 1.3 pp a year in 2022-2025: −3.7 pp of capture rate a year (base-case trend −1 pp); wind park −0.36 per unit of its share of load, which grew 0.8 pp a year in 2022-2025: −0.3 pp of capture rate a year (base-case trend +0 pp). The trend assumes that storage, flexible demand and curtailment slow solar's fall; the −2 pp row of section 4 is closer to history's pace.

So the base case moves each year's capture rate along the model's response (chart below); holding the first year's capture rate over the tenor instead (as before v1.5) would give fair prices of solar park 55.5, wind park 88.5 EUR/MWh.

![Capture rate vs price level](figures/step07_level_effect.png)

## 6. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **45.7 EUR/MWh** (first year: forward 141.0 × expected capture rate 0.61 = 86.0). After a profile and volume risk premium of 8.3 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **34.9 EUR/MWh**. Expected annual energy is 120.9 GWh (P50; one-year P90 113.4 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 3.68 m (merchant) to EUR 0.77 m per year: only volume risk is left.

## 7. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
