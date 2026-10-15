# Step 3 report: PPA structures back-tested

Generated 2026-10-15 14:26 UTC by `ppa-lab ppa`.
Data: CC BY 4.0 - Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE).
Delivery years: 2024, 2025.

**Set-up.** Each park first uses the national generation profile of its technology, scaled to
capacity x full-load hours in every year (measured data); section 2 repeats the back-test with
each park's own modelled profile. A contract for delivery year Y is signed at the
end of Y-1 at Y-1's fair price: the pay-as-produced strike is Y-1's capture price, the
baseload strike Y-1's base price, and the band delivers the expected annual energy flat.
That is a naive stand-in for forward prices. Cash flows are to the producer, per
quarter-hour, without option premiums, balancing or credit costs. Maths: `METHODOLOGY.md`.

**Plan and surprise.** The plan is what each structure would have earned per MWh had the
delivery year looked like the year before (same terms on last year's prices and profile):
the expectation at signing. Surprise = realised − plan is the risk each structure left with
the producer. The worst month shows liquidity: a baseload seller can have negative months.

## 1. Results per park

### Solar Park (Borrentin): 114 MW solar, 1061 full-load hours

Strikes, fixed at the end of the previous year:

|   Delivery year |   PaP strike (EUR/MWh) |   Baseload strike (EUR/MWh) |   Band (MW) |
|----------------:|-----------------------:|----------------------------:|------------:|
|            2024 |                  72.25 |                       95.18 |       13.77 |
|            2025 |                  46.48 |                       78.51 |       13.81 |

Results:

|   Year | Structure                              |   Revenue (EUR m) |   EUR/MWh |   vs merchant (EUR/MWh) |   Plan (EUR/MWh) |   Surprise vs plan |   Worst month (EUR k) |
|-------:|:---------------------------------------|------------------:|----------:|------------------------:|-----------------:|-------------------:|----------------------:|
|   2024 | Merchant (spot)                        |              5.62 |     46.48 |                    0    |            72.25 |             -25.77 |                   212 |
|   2024 | Pay-as-produced PPA                    |              8.74 |     72.25 |                   25.77 |            72.25 |               0    |                   156 |
|   2024 | PaP PPA, no payment at negative prices |              7.14 |     59.04 |                   12.56 |            66.25 |              -7.21 |                   156 |
|   2024 | Baseload PPA                           |              7.64 |     63.14 |                   16.66 |            72.25 |              -9.11 |                   107 |
|   2024 | Merchant + floor                       |              5.96 |     49.26 |                    2.79 |            74.13 |             -24.86 |                   212 |
|   2025 | Merchant (spot)                        |              5.56 |     45.95 |                    0    |            46.48 |              -0.53 |                   234 |
|   2025 | Pay-as-produced PPA                    |              5.62 |     46.48 |                    0.53 |            46.48 |               0    |                   116 |
|   2025 | PaP PPA, no payment at negative prices |              4.26 |     35.22 |                  -10.73 |            37.98 |              -2.76 |                   116 |
|   2025 | Baseload PPA                           |              4.25 |     35.14 |                  -10.81 |            46.48 |             -11.34 |                   -58 |
|   2025 | Merchant + floor                       |              5.96 |     49.25 |                    3.3  |            49.26 |              -0.02 |                   234 |

### Wind Park (Everswinkel): 28.5 MW wind onshore, 2246 full-load hours

Strikes, fixed at the end of the previous year:

|   Delivery year |   PaP strike (EUR/MWh) |   Baseload strike (EUR/MWh) |   Band (MW) |
|----------------:|-----------------------:|----------------------------:|------------:|
|            2024 |                  78.44 |                       95.18 |        7.29 |
|            2025 |                  64.54 |                       78.51 |        7.31 |

Results:

|   Year | Structure                              |   Revenue (EUR m) |   EUR/MWh |   vs merchant (EUR/MWh) |   Plan (EUR/MWh) |   Surprise vs plan |   Worst month (EUR k) |
|-------:|:---------------------------------------|------------------:|----------:|------------------------:|-----------------:|-------------------:|----------------------:|
|   2024 | Merchant (spot)                        |              4.13 |     64.54 |                    0    |            78.44 |             -13.9  |                   171 |
|   2024 | Pay-as-produced PPA                    |              5.02 |     78.44 |                   13.9  |            78.44 |               0    |                   231 |
|   2024 | PaP PPA, no payment at negative prices |              4.7  |     73.5  |                    8.96 |            73.9  |              -0.4  |                   185 |
|   2024 | Baseload PPA                           |              5.2  |     81.2  |                   16.66 |            78.44 |               2.77 |                   268 |
|   2024 | Merchant + floor                       |              4.16 |     65.03 |                    0.49 |            78.91 |             -13.88 |                   177 |
|   2025 | Merchant (spot)                        |              4.95 |     77.27 |                    0    |            64.54 |              12.73 |                   245 |
|   2025 | Pay-as-produced PPA                    |              4.13 |     64.54 |                  -12.73 |            64.54 |               0    |                   224 |
|   2025 | PaP PPA, no payment at negative prices |              3.82 |     59.63 |                  -17.65 |            60.48 |              -0.85 |                   201 |
|   2025 | Baseload PPA                           |              4.25 |     66.46 |                  -10.81 |            64.54 |               1.92 |                   233 |
|   2025 | Merchant + floor                       |              4.97 |     77.71 |                    0.44 |            65.03 |              12.68 |                   247 |

## 2. With each park's own profile (Step 4)

The same contracts, but each park produces its own modelled output (ERA5 weather at the site,
Step 4) instead of the national profile: the park-specific back-test. Revenue per MWh:

| Park                    |   Year |   Merchant (spot) |   Pay-as-produced PPA |   PaP PPA, no payment at negative prices |   Baseload PPA |   Merchant + floor |   Baseload surprise vs plan |   Merchant, national profile |
|:------------------------|-------:|------------------:|----------------------:|-----------------------------------------:|---------------:|-------------------:|----------------------------:|-----------------------------:|
| Solar Park (Borrentin)  |   2024 |             47.22 |                 76.06 |                                    62.29 |          63.89 |              50.08 |                      -12.17 |                        46.48 |
| Solar Park (Borrentin)  |   2025 |             48.38 |                 47.22 |                                    36.07 |          37.57 |              51.76 |                       -9.66 |                        45.95 |
| Wind Park (Everswinkel) |   2024 |             64.26 |                 78    |                                    72.45 |          80.92 |              65.01 |                        2.92 |                        64.54 |
| Wind Park (Everswinkel) |   2025 |             76.34 |                 64.26 |                                    59.05 |          65.53 |              76.87 |                        1.27 |                        77.27 |

The national profile is measured; the site profile is modelled but carries the park's own
weather. Where the two merchant columns differ, the park's location matters for its value.

## 3. What the numbers say (national profile)

- **Solar Park, 2025:** merchant earned 45.95 EUR/MWh. Against that, the pay-as-produced PPA made +0.53 EUR/MWh and the baseload PPA -10.81 EUR/MWh. The negative-price clause cost the producer 11.26 EUR/MWh; a floor at 0 EUR/MWh (or curtailing below it) added +3.30 EUR/MWh. Surprise against plan: merchant -0.53, pay-as-produced +0.00, baseload -11.34 EUR/MWh.
- **Wind Park, 2025:** merchant earned 77.27 EUR/MWh. Against that, the pay-as-produced PPA made -12.73 EUR/MWh and the baseload PPA -10.81 EUR/MWh. The negative-price clause cost the producer 4.91 EUR/MWh; a floor at 0 EUR/MWh (or curtailing below it) added +0.44 EUR/MWh. Surprise against plan: merchant +12.73, pay-as-produced +0.00, baseload +1.92 EUR/MWh.

## 4. Charts

![Revenue per MWh by structure](figures/step03_structures_annual.png)

![Monthly revenue by structure](figures/step03_structures_monthly.png)
