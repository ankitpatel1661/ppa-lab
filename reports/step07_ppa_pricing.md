# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-15 20:07 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The scenarios average
141.05 EUR/MWh in 2027. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their fair price, so the expected revenue is the same (the
negative-price clause at the plain strike costs the producer its output at negative prices).
The spread of annual revenue is what changes: the 95% cash flow at risk.

| Park       | Structure                                        | Strike (EUR/MWh)   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-------------------------------------------------|:-------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract)                           | spot               |                      10.41 |                 7.04 |                            3.37 | 32%               |
| Solar park | Pay-as-produced PPA                              | 86.40              |                      10.41 |                 9.63 |                            0.78 | 7%                |
| Solar park | Pay-as-produced, nothing paid at negative prices | 86.40              |                       8.97 |                 7.9  |                            1.07 | 12%               |
| Solar park | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                      10.41 |                 7.19 |                            3.21 | 31%               |
| Solar park | Baseload PPA (band = average output)             | 141.05             |                      10.41 |                 8.99 |                            1.41 | 14%               |
| Wind park  | Merchant (no contract)                           | spot               |                       8.26 |                 6.14 |                            2.12 | 26%               |
| Wind park  | Pay-as-produced PPA                              | 129.18             |                       8.26 |                 7.3  |                            0.96 | 12%               |
| Wind park  | Pay-as-produced, nothing paid at negative prices | 129.18             |                       7.95 |                 7.03 |                            0.92 | 12%               |
| Wind park  | Merchant + floor at 0 EUR/MWh (premium paid)     | spot               |                       8.26 |                 6.16 |                            2.09 | 25%               |
| Wind park  | Baseload PPA (band = average output)             | 141.05             |                       8.26 |                 7.13 |                            1.12 | 14%               |

## 2. The buyer's risk premium

The buyer of a pay-as-produced PPA takes every MWh at the strike and sells it at spot. It
hedges the price level by selling a baseload band of the expected average output at the
forward; what is left is profile and volume risk. Premium = (expected value − 5% quantile)
per expected MWh.

| Park       |   Fair price |   Premium, no hedge |   Premium after baseload hedge |   of which profile |   of which volume (and its link to price) |
|:-----------|-------------:|--------------------:|-------------------------------:|-------------------:|------------------------------------------:|
| Solar park |        86.4  |               27    |                           9.35 |               8.69 |                                      0.65 |
| Wind park  |       129.18 |               34.56 |                           5.53 |               1.95 |                                      3.59 |

## 3. Price stack 2027: from the forward to an indicative price

| Layer (EUR/MWh)                        |   Solar park |   Wind park |
|:---------------------------------------|-------------:|------------:|
| Forward (model average baseload price) |       141.05 |      141.05 |
| Shape: capture rate below 1            |       -54.65 |      -11.87 |
| = Fair pay-as-produced price           |        86.4  |      129.18 |
| − Profile and volume risk premium      |         9.35 |        5.53 |
| − Balancing and route to market        |         1.5  |        2    |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        74.55 |      120.65 |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; forwards as above. Capture-rate
trend per year after 2027 (base case): solar park -1 pp, wind park +0 pp; solar output degrades
0.5% per year. The risk premium and costs per MWh of the first year
are applied to every year (a simplification).

| Case                                              |   Solar park: fair |   Solar park: indicative |   Wind park: fair |   Wind park: indicative |
|:--------------------------------------------------|-------------------:|-------------------------:|------------------:|------------------------:|
| Base case                                         |              48.62 |                    36.77 |             86.03 |                   77.49 |
| Capture-rate trend 2 pp/yr steeper                |              41.6  |                    29.76 |             78.94 |                   70.41 |
| Capture-rate trend 1 pp/yr steeper                |              45.11 |                    33.26 |             82.48 |                   73.95 |
| Capture-rate trend 1 pp/yr flatter                |              52.13 |                    40.28 |             89.57 |                   81.04 |
| Forward −10%                                      |              41.49 |                    29.65 |             76.64 |                   68.11 |
| Forward +10%                                      |              55.7  |                    43.85 |             95.38 |                   86.84 |
| Analog days from the whole window                 |              53.66 |                    41.82 |             86.08 |                   77.55 |
| Capture rate vs price level: low end of history   |              49.73 |                    37.89 |             87.24 |                   78.7  |
| Capture rate vs price level: high end of history  |              47.59 |                    35.75 |             85.77 |                   77.24 |
| Capture rate less the model's out-of-sample error |              36.77 |                    24.92 |             82.88 |                   74.34 |

Each year's capture rate moves with that year's forward along the model's own response to the price level (section 5), on top of the trend. The two rows on the capture rate vs price level use history's 95% interval for that slope instead, from the recent level (105 EUR/MWh): a flatter slope gives a lower capture rate at the high 2027 forward but a higher one once the curve falls below the recent level. The last row takes the model's average out-of-sample capture-rate error in 2024-2026 off every year (solar park +0.123, wind park +0.033; Step 6, section 4): fitted on the years before, the model overstated capture rates in every year, because the midday dips deepen as solar capacity grows.

## 5. Does the capture rate rise with the price level?

The price model shifts all hours together in arcsinh units, so a higher price level lifts the hours near zero and solar's capture rate rises with it. The usual shape-factor view scales all hours instead, and the capture rate stays put. The 2027 forward (141 EUR/MWh) lies above the recent level (105) and the curve falls to 88, so the answer moves the price.

History decides: monthly capture rates regressed on ln(average price), with month effects and the technology's share of load (its build-out) held fixed; HC1 standard errors (`analysis/level_effect.py`). The model's slope comes from rebuilding the scenarios at each forward with the same random draws.

| Change of capture rate per unit of ln(price) | Solar park | Wind park |
|---|---|---|
| History 2023-2026: slope (95% interval) | 0.27 (0.10 to 0.45) | 0.02 (−0.09 to 0.14) |
| t-statistic; months | 3.1; 45 | 0.4; 45 |
| History 2021-2026, all years | 0.10 (0.06 to 0.13) | 0.00 (−0.04 to 0.04) |
| Model: recent level (105) to forward 2027 | 0.19 | 0.06 |
| Model: over the tenor's forwards (88 to 141) | 0.20 | 0.07 |

**Solar park**: the capture rate rises with the price level (slope 0.27, t = 3.1), so the shape-factor view (slope 0) is rejected; the model's 0.19 lies inside the 95% interval. **Wind park**: history cannot tell the slope from zero (0.02, t = 0.4); the model's 0.06 lies inside the 95% interval.

Build-out, from the same regression at a fixed price level: solar park −2.90 per unit of its share of load, which grew 1.3 pp a year in 2022-2025: −3.7 pp of capture rate a year (base-case trend −1 pp); wind park −0.36 per unit of its share of load, which grew 0.8 pp a year in 2022-2025: −0.3 pp of capture rate a year (base-case trend +0 pp). The trend assumes that storage, flexible demand and curtailment slow solar's fall; the −2 pp row of section 4 is closer to history's pace.

So the base case moves each year's capture rate along the model's response (chart below); holding the first year's capture rate over the tenor instead (as before v1.5) would give fair prices of solar park 55.7, wind park 88.4 EUR/MWh.

![Capture rate vs price level](figures/step07_level_effect.png)

## 6. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **48.6 EUR/MWh** (first year: forward 141.1 × expected capture rate 0.61 = 86.4). After a profile and volume risk premium of 9.3 EUR/MWh and balancing and credit costs of 2.5 EUR/MWh, the indicative price is **36.8 EUR/MWh**. Expected annual energy is 120.9 GWh (P50; one-year P90 113.4 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 3.37 m (merchant) to EUR 0.78 m per year: only volume risk is left.

## 7. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
