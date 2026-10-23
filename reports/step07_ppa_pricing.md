# Step 7 report: pricing the PPAs and their risk

Generated 2026-10-23 12:28 UTC by `ppa-lab pricing`.

Inputs: the Step 6 joint scenarios for 2027
(496 scenarios: 31 weather years x
16 price paths), with intraday patterns from analog days
from **2025-10-01** on (the most recent regime; the whole window is a sensitivity).
Forward: EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai); its quarters follow the market's seasonal shape (Q1-Q4 185.3 / 117.7 / 124.3 / 134.3, quotes of 2026-09-14); later years follow the forward curve (2028: 104.75, 2029: 87.58), held flat after 2029. The scenarios average
141.06 EUR/MWh in 2027. Risk measures at the 5% quantile.

## 1. What each structure leaves with the producer (2027)

All structures struck at their own fair price. A park that sells at spot, or is not paid at negative prices, stops producing below 0 EUR/MWh, so those structures earn more on average by the value of curtailing (section 5); the plain PPA and the merchant that keeps producing forgo it. The spread of annual revenue is
what changes most: the 95% cash flow at risk.

| Park       | Structure                                                  | Strike (EUR/MWh)   | Output sold or paid   |   Expected revenue (EUR m) |   P5 revenue (EUR m) |   Cash flow at risk 95% (EUR m) | CFaR / expected   |
|:-----------|:-----------------------------------------------------------|:-------------------|:----------------------|---------------------------:|---------------------:|--------------------------------:|:------------------|
| Solar park | Merchant (no contract), curtailing at negative prices      | spot               | 82%                   |                       9.71 |                 6.69 |                            3.02 | 31%               |
| Solar park | Merchant, producing at negative prices                     | spot               | 100%                  |                       9.34 |                 6.09 |                            3.24 | 35%               |
| Solar park | Pay-as-produced PPA                                        | 77.53              | 100%                  |                       9.34 |                 8.64 |                            0.7  | 7%                |
| Solar park | Pay-as-produced, negative-price clause (curtailed, unpaid) | 97.76              | 82%                   |                       9.71 |                 8.42 |                            1.29 | 13%               |
| Solar park | Pay-as-produced, buyer curtails and pays the output        | 80.63              | 100%                  |                       9.71 |                 8.98 |                            0.73 | 7%                |
| Solar park | Baseload PPA (band = average output)                       | 141.06             | 82%                   |                       9.71 |                 8.11 |                            1.6  | 16%               |
| Wind park  | Merchant (no contract), curtailing at negative prices      | spot               | 96%                   |                       8.35 |                 6.25 |                            2.1  | 25%               |
| Wind park  | Merchant, producing at negative prices                     | spot               | 100%                  |                       8.31 |                 6.18 |                            2.13 | 26%               |
| Wind park  | Pay-as-produced PPA                                        | 129.94             | 100%                  |                       8.31 |                 7.34 |                            0.96 | 12%               |
| Wind park  | Pay-as-produced, negative-price clause (curtailed, unpaid) | 136.66             | 96%                   |                       8.35 |                 7.37 |                            0.98 | 12%               |
| Wind park  | Pay-as-produced, buyer curtails and pays the output        | 130.63             | 100%                  |                       8.35 |                 7.38 |                            0.97 | 12%               |
| Wind park  | Baseload PPA (band = average output)                       | 141.06             | 96%                   |                       8.35 |                 7.24 |                            1.11 | 13%               |

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
| − Balancing and route to market        |         2.18 |        1.55 |
| − Credit and liquidity                 |         1    |        1    |
| = Indicative pay-as-produced price     |        63.8  |      121.9  |

Balancing and credit costs are stated assumptions (`[ppa.parks.*]` in `config/project.toml`).

## 4. 10-year price (2027-2036)

Discounted at 6% (mid-year), energy-weighted; forwards as above. Capture rate
after 2027 (base case): solar park the central build-out scenario (section 8); wind park +0 pp a year. Solar output degrades
0.5% per year. The risk premium and costs per MWh of the first year
are applied to every year (a simplification).

| Case                                                                   |   Solar park: fair |   Solar park: indicative | Wind park: fair   | Wind park: indicative   |
|:-----------------------------------------------------------------------|-------------------:|-------------------------:|:------------------|:------------------------|
| Base case                                                              |              35.09 |                    21.37 | 86.64             | 78.60                   |
| Capture-rate trend 2 pp/yr steeper                                     |              28.07 |                    14.35 | 79.55             | 71.51                   |
| Capture-rate trend 1 pp/yr steeper                                     |              31.58 |                    17.86 | 83.09             | 75.05                   |
| Capture-rate trend 1 pp/yr flatter                                     |              38.59 |                    24.87 | 90.18             | 82.14                   |
| Forward −10%                                                           |              29.52 |                    15.8  | 77.22             | 69.18                   |
| Forward +10%                                                           |              40.59 |                    26.87 | 96.02             | 87.98                   |
| Analog days from the whole window                                      |              35.06 |                    21.34 | 87.06             | 79.02                   |
| Capture rate vs price level: low end of history                        |              35.87 |                    22.15 | 87.83             | 79.78                   |
| Capture rate vs price level: high end of history                       |              35.04 |                    21.31 | 86.36             | 78.32                   |
| Capture rate less the model's out-of-sample error                      |              32.94 |                    19.22 | 82.35             | 74.31                   |
| Build-out: Recent pace: solar +16.5 GW, storage +6.5 GWh a year        |              33.73 |                    20.01 | –                 | –                       |
| Build-out: EEG solar target pace: solar +24 GW, storage +12 GWh a year |              31.64 |                    17.92 | –                 | –                       |
| Build-out: Storage boom: solar +17 GW, storage +35 GWh a year          |              43.8  |                    30.08 | –                 | –                       |
| Build-out: Slowdown: solar +12 GW, storage +8 GWh a year               |              36.66 |                    22.94 | –                 | –                       |

Each year's capture rate moves with that year's forward along the model's own response to the price level (section 7), on top of the trend. The two rows on the capture rate vs price level use history's 95% interval for that slope instead, from the recent level (105 EUR/MWh): a flatter slope gives a lower capture rate at the high 2027 forward but a higher one once the curve falls below the recent level. The last row takes the model's mean out-of-sample capture-rate error off every year (solar park +0.029, wind park +0.044; test years 2025, 2026, fitted like 2027; Step 6, section 4): fitted on the years before, the model overstated capture rates even with the price level given. The 2027 scenarios carry history's build-out trend up to 2027 (Step 6, section 4); continued for one more year at the same forward it would move the capture rate by solar park −5.6 pp, wind park +0.3 pp. After that the base case follows: solar park the central build-out scenario (section 8); wind park +0 pp a year; the build-out rows show the other scenarios, and the trend rows move the capture rate by whole points a year on top.

## 5. Negative prices: curtail, and who keeps the value

In hours with negative prices output is worth less than nothing. A park that sells at spot stops producing then: its marginal cost is about zero, and no subsidy is paid at negative prices (§51 EEG). Under a plain pay-as-produced PPA it is paid the strike for every MWh, so it keeps producing and the buyer sells that output at a loss: the value of curtailing is lost to both sides. Three ways to handle it:

- **Plain PPA** (the base case above): nobody curtails; the fair price includes the negative hours.
- **Negative-price clause**: nothing is paid at negative prices and the park curtails. The strike is the fair price of the output delivered, higher per MWh, and the park keeps the value of curtailing, but it takes back volume risk: sunny, cheap years have more negative hours.
- **Deemed output**: the buyer may curtail and pays the curtailed output as if produced. The strike rises by the value of curtailing; the producer's risk stays that of the plain PPA.

| EUR/MWh | Solar park | Wind park |
|---|---|---|
| Output at negative prices, 2027 | 17.5% | 4.4% |
| Their output-weighted mean price | −17.70 | −15.63 |
| Saved by curtailing, per MWh of output | 3.10 | 0.69 |
| Plain PPA: fair price 2027; 10-year indicative | 77.53; 21.37 | 129.94; 78.60 |
| Clause: fair price 2027 per delivered MWh | 97.76 | 136.66 |
| Clause: buyer's premium after a baseload hedge | 14.56 (plain 10.54) | 5.93 (plain 5.49) |
| Clause: 10-year fair; indicative, per delivered MWh | 57.08; 39.34 | 97.00; 88.52 |
| Clause: 10-year indicative per MWh of output (delivered share) | 27.33 (69.5%) | 80.44 (90.9%) |
| Deemed output: fair price 2027 | 80.63 | 130.63 |
| Producer's CFaR95 2027: plain; clause (EUR m) | 0.70; 1.29 | 0.96; 0.98 |

The clause's tenor price follows the curtailed output's capture rate and its delivered share at each year's forward (more negative hours at lower forwards), plus the capture-rate trend and the solar build-out scenario of section 8 (it leaves the delivered share unchanged); the first year's premium and costs apply to every year. In history the parks' output at negative prices grew with the build-out:

| Year | Solar park: output at negative prices; saved per MWh | Wind park: output at negative prices; saved per MWh |
|---|---|---|
| 2021 | 4.1%; 0.93 | 4.0%; 0.67 |
| 2022 | 1.6%; 0.06 | 1.9%; 0.03 |
| 2023 | 7.7%; 1.84 | 6.3%; 0.73 |
| 2024 | 18.1%; 2.86 | 7.1%; 0.75 |
| 2025 | 23.6%; 3.38 | 8.2%; 0.53 |
| 2026 | 23.5%; 4.93 | 8.9%; 1.08 |

2026: January to September. Out of sample (Step 6, section 4) the model put the solar park's output at negative prices 3 percentage points below history, so these values are if anything low.

## 6. The EEG premium against a PPA

### Wind park

The wind park is paid under the EEG market premium model: it sells at spot and the grid operator adds max(AW − MW, 0) per MWh, MW the month's official onshore wind market value. That is a strip of puts on the market value, struck at the award value AW, here **77 EUR/MWh (an assumption: the award is not published; see `[eeg]`)**. To sign a PPA the park would leave the premium (a PPA buyer wants the guarantees of origin, which the EEG does not issue), so the PPA must be worth more than the EEG. MW in a scenario: the park's own capture price that month times 0.968, the ratio of the official value to the park's capture price in 44 months from 2023-01 (sd 0.042). No premium at negative prices (§51 EEG; the park curtails).

Per MWh of output (EUR/MWh):

| Year | Forward | Merchant | Market premium | Under the EEG |
|---|---|---|---|---|
| 2027 | 141.1 | 130.6 | 0.49 | 131.1 |
| 2028 | 104.8 | 95.9 | 4.11 | 100.0 |
| 2029-2036 | 87.6 | 79.6 | 8.88 | 88.5 |

Over 10 years (discounted, energy-weighted) the EEG pays 95.4 EUR/MWh, of which 7.23 premium; after the direct marketer's fee (1.6) **93.8**. A PPA pays 86.6 at its fair price and **78.6** at the indicative price: 15.2 EUR/MWh less than staying in the EEG. The put is worth little at the 2027 forward but much at the lower forwards of later years.

Risk in one delivery year, at two price levels:

| Price level | CFaR95, EUR m: merchant / EEG / PPA | 5% quantile, EUR/MWh: merchant / EEG / PPA |
|---|---|---|
| 2027 forward (140) | 2.10 / 2.03 / 0.96 | 97.8 / 99.4 / 114.9 |
| lowest quoted forward (88) | 1.58 / 0.99 / 0.58 | 55.4 / 73.4 / 69.4 |

The put cuts the merchant's risk most where prices are low, and a PPA removes more of it; but at the lowest forward the EEG's bad year is better than the PPA's (73.4 against 69.4 EUR/MWh): the put floors the price and the EEG keeps the upside. By award value:

| Award value AW (EUR/MWh) | Market premium, ten years | Under the EEG, after the fee |
|---|---|---|
| 60 | 2.30 | 88.9 |
| 70 | 4.76 | 91.4 |
| 77 (assumed) | 7.23 | 93.8 |
| 85 | 10.77 | 97.4 |
| 95 | 16.26 | 102.9 |
| 77, yearly market value | 5.14 | 91.7 |

For every award value in the range the EEG pays more than a PPA at the indicative price (by 10.3 EUR/MWh even at AW 60). Leaving the EEG for a PPA pays only at a price of at least about 94 EUR/MWh, less what the producer would pay to be rid of the remaining risk, plus the guarantees of origin it could then sell. The PPA price of section 4 is a what-if for this park.

## 7. Does the capture rate rise with the price level?

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

Build-out, from the same regression at a fixed price level: solar park −2.90 per unit of its share of load, which grew 1.3 pp a year in 2022-2025: −3.7 pp of capture rate a year (base case: build-out scenarios, section 8); wind park −0.36 per unit of its share of load, which grew 0.8 pp a year in 2022-2025: −0.3 pp of capture rate a year (base-case trend +0 pp). Section 8 turns this into build-out scenarios, in which storage slows solar's fall.

So the base case moves each year's capture rate along the model's response (chart below); holding the first year's capture rate over the tenor instead (as before v1.5) would give fair prices of solar park 41.0, wind park 88.9 EUR/MWh.

![Capture rate vs price level](figures/step07_level_effect.png)

## 8. Solar and storage build-out after 2027

Until v1.10 solar's capture rate fell 1 percentage point a year after 2027, an assumption. Now it follows build-out scenarios (`[buildout]`). History calibrates the link: solar's share of load grew from 11.3% (2022) to 15.1% (2025) while 49.5 GW of solar were added, 0.077 share points per GW. A GWh of storage takes 0.043 points out of the cheap hours (250 cycles a year, 80% of them charged from solar, 466 TWh of load); only storage beyond history's 6.5 GWh a year counts. On monthly history (45 months) each point of solar share lowered the capture rate by 5.3% (log form, se 0.8); new solar adds most share in sunny months, which weigh 1.38 times as much. The level effect of section 7 and the forward curve stay as they were.

| Scenario | Solar (GW/yr) | Storage (GWh/yr) | Solar share of load (pp/yr) | Capture-rate factor 2030 / 2036 | Solar park: 10-year fair; indicative |
|---|---|---|---|---|---|
| Central (base case) | 17 | 12 | +1.07 | 0.79 / 0.50 | 35.09; 21.37 |
| Recent pace | 16.5 | 6.5 | +1.26 | 0.76 / 0.43 | 33.73; 20.01 |
| EEG solar target pace | 24 | 12 | +1.60 | 0.70 / 0.35 | 31.64; 17.92 |
| Storage boom | 17 | 35 | +0.08 | 0.98 / 0.95 | 43.80; 30.08 |
| Slowdown | 12 | 8 | +0.85 | 0.83 / 0.57 | 36.66; 22.94 |

With the fixed −1 pp a year of v1.10 the 10-year fair price was 41.15 EUR/MWh (solar park). Storage is what decides: in the base case solar's capture rate falls by 8% a year, and only a storage build-out several times history's slows it much. The scenarios extrapolate a link measured on 45 months up to 2025, in which storage was small; flexible demand, exports and curtailment rules are not in it.

## 9. The answer

For a 10-year pay-as-produced PPA (2027-2036) from the solar park, the fair price before risk premia is **35.1 EUR/MWh** (first year: forward 141.1 × expected capture rate 0.55 = 77.5). After a profile and volume risk premium of 10.5 EUR/MWh and balancing and credit costs of 3.2 EUR/MWh, the indicative price is **21.4 EUR/MWh**. Expected annual energy is 120.9 GWh (P50; one-year P90 113.4 GWh). Under the PPA the producer's 95% cash flow at risk falls from EUR 3.02 m (merchant) to EUR 0.70 m per year: only volume risk is left. After 2027 the capture rate follows the central build-out scenario (section 8); across the scenarios the indicative price ranges from 17.9 to 30.1 EUR/MWh, and storage decides where.

## 10. Charts

![Price stack](figures/step07_price_stack.png)

![Revenue by structure](figures/step07_revenue.png)

![The buyer's risk](figures/step07_buyer_risk.png)

Results for Step 9: `data/processed/ppa_pricing.json`.
