# Step 6 report: joint weather and price scenarios

Generated 2026-10-15 16:27 UTC by `ppa-lab scenarios`.

Data: CC BY 4.0 - Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE); ERA5 via Open-Meteo (CC BY 4.0 - Open-Meteo.com; contains modified Copernicus Climate Change Service information (ERA5)).

## 1. The weather-price link

The Step 5 model drew each simulated day at random from its season. Here the day's weather
decides: its level responds to the weather anomaly (regression per season on the solar and
wind capacity factors of the two parks and the temperature), and its hourly pattern comes
from one of the 10 historical days within ±30 days of the date whose
weather was closest (analog days). Calibration: 2024-01-01 to
2026-09-30, with the real weather of those days.

Response of the daily price level, in EUR/MWh at 140 EUR/MWh
(capacity factor CF: mean output / capacity):

| Season   |   R² |   +0.1 solar CF |   +0.1 wind CF |   +1 °C |
|:---------|-----:|----------------:|---------------:|--------:|
| autumn   | 0.69 |            -0.8 |          -15.6 |    -1.2 |
| spring   | 0.51 |           -13.8 |          -12.8 |    -1.6 |
| summer   | 0.47 |            -7.3 |          -12.7 |     1.4 |
| winter   | 0.64 |            -6.1 |          -12.3 |    -2.4 |

What weather does not explain still reverts with phi = 0.380 per day (half-life
0.72 days). Analog pool: 998 historical days.

## 2. Validation with the real weather of the calibration window

200 paths each; analog days at least 7 days away from the
simulated day (no peeking). Statistics with history inside the 5-95% range of the paths:
**Step 5: 7 of 11; Step 6:
6 of 11.**

| Statistic                 | History   | Step 5 (independent) (inside?)   | Step 6 (linked) (inside?)   |
|:--------------------------|:----------|:---------------------------------|:----------------------------|
| Mean (EUR/MWh)            | 90.4      | 90.6 (yes)                       | 90.1 (yes)                  |
| Standard deviation        | 57.6      | 56.0 (yes)                       | 56.5 (yes)                  |
| 1% quantile               | -20.1     | -41.4 (no)                       | -45.2 (no)                  |
| 5% quantile               | -0.1      | 0.9 (yes)                        | -3.0 (no)                   |
| Median                    | 91.4      | 90.4 (yes)                       | 91.7 (yes)                  |
| 95% quantile              | 173.7     | 176.4 (yes)                      | 175.2 (yes)                 |
| 99% quantile              | 246.8     | 242.5 (yes)                      | 239.6 (yes)                 |
| Share of negative hours   | 6.2%      | 4.9% (no)                        | 5.6% (no)                   |
| Autocorrelation, 1 hour   | 0.921     | 0.914 (no)                       | 0.917 (no)                  |
| Autocorrelation, 24 hours | 0.700     | 0.593 (no)                       | 0.626 (no)                  |
| Autocorrelation, 1 week   | 0.548     | 0.517 (yes)                      | 0.541 (yes)                 |

Capture rates of the parks in each complete year (median and 5-95% over paths):

|   Year | Park       |   History | Step 5 (independent)   | Step 6 (linked)     |
|-------:|:-----------|----------:|:-----------------------|:--------------------|
|   2024 | Solar park |     0.601 | 0.554 (0.511-0.594)    | 0.498 (0.466-0.531) |
|   2024 | Wind park  |     0.818 | 1.012 (0.983-1.045)    | 0.849 (0.830-0.867) |
|   2025 | Solar park |     0.542 | 0.598 (0.565-0.628)    | 0.546 (0.519-0.573) |
|   2025 | Wind park  |     0.855 | 1.039 (1.012-1.066)    | 0.874 (0.858-0.888) |

History outside the Step 6 range: solar park 2024 (0.601 vs 0.466-0.531), wind park 2024 (0.818 vs 0.830-0.867), wind park 2025 (0.855 vs 0.858-0.888).

## 3. Delivery year 2027: 496 scenarios

31 weather years (1995-2025) x 16 price paths
= 496 scenarios; forward 140.2 EUR/MWh with each quarter at the market's seasonal shape (Q1-Q4: 185.3 / 117.7 / 124.3 / 134.3 EUR/MWh, quotes of 2026-09-14), level uncertainty
0.12. The same scenarios with prices independent of the weather
(Step 5 model) for comparison.

| Park       | Prices      |   Fair PaP price (EUR/MWh) | Capture rate 5/50/95%   | Revenue P10/P50/P90 (EUR m)   |   Corr(energy, baseload price) |
|:-----------|:------------|---------------------------:|:------------------------|:------------------------------|-------------------------------:|
| Solar park | independent |                      97.64 | 0.633 / 0.692 / 0.737   | 8.77 / 11.65 / 14.90          |                           0.01 |
| Solar park | linked      |                      94.45 | 0.606 / 0.668 / 0.716   | 8.47 / 11.31 / 14.61          |                           0.02 |
| Wind park  | independent |                     148.31 | 1.016 / 1.051 / 1.092   | 7.45 / 9.41 / 11.67           |                          -0.01 |
| Wind park  | linked      |                     129.46 | 0.874 / 0.922 / 0.953   | 6.51 / 8.19 / 10.27           |                          -0.15 |

- Ignoring the weather link overstates the fair pay-as-produced price by
  3.20 EUR/MWh (solar park) and 18.84 EUR/MWh (wind park).
- Monte Carlo standard error of the linked fair prices:
  solar park 0.88 EUR/MWh, wind park 1.00 EUR/MWh.
- Does the latest historical capture rate fall inside the linked range?
  Solar park: 2025 history 0.542, linked 5-95% 0.606 to 0.716 (outside); Wind park: 2025 history 0.855, linked 5-95% 0.874 to 0.953 (outside). The comparison mixes in the price level: 2027 is simulated at 140 EUR/MWh, 2025 averaged 89, and in this model the capture rate rises with the level (Step 7 shows the sensitivity); the validation above is the test.

Per-scenario results: `data/processed/scenarios_2027.parquet` (input for Step 7).

### Sensitivity: which historical days represent 2027?

Intraday patterns come from the analog pool. Midday solar dips deepened year by year as
solar capacity grew, so the pool's period matters. The base case above uses the whole
calibration window (as in the validation).

| Analog days from            |   Days in pool |   Solar park: fair price |   Solar park: median capture rate |   Wind park: fair price |   Wind park: median capture rate |
|:----------------------------|---------------:|-------------------------:|----------------------------------:|------------------------:|---------------------------------:|
| 2024-01-01 (whole window)   |            998 |                    94.45 |                             0.668 |                  129.46 |                            0.922 |
| 2025-01-01 (2025 onward)    |            635 |                    89.65 |                             0.635 |                  129.69 |                            0.925 |
| 2025-10-01 (last 12 months) |            363 |                    86    |                             0.609 |                  129.34 |                            0.922 |

## 4. Charts

![Capture rates per scenario](figures/step06_capture_rates.png)

![The weather-price link in daily data](figures/step06_link.png)

![Convergence of the fair price](figures/step06_convergence.png)
