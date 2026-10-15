# Step 6 report: joint weather and price scenarios

Generated 2026-10-15 07:40 UTC by `ppa-lab scenarios`.

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
| autumn   | 0.54 |            -0.6 |          -10.4 |    -0.6 |
| spring   | 0.52 |           -14.7 |           -7.5 |    -0.4 |
| summer   | 0.56 |            -9   |           -8   |     1.4 |
| winter   | 0.44 |            -7.9 |           -7.1 |    -2.7 |

What weather does not explain still reverts with phi = 0.456 per day (half-life
0.88 days). Analog pool: 998 historical days.

## 2. Validation with the real weather of the calibration window

200 paths each; analog days at least 7 days away from the
simulated day (no peeking). Statistics with history inside the 5-95% range of the paths:
**Step 5: 7 of 11; Step 6:
6 of 11.**

| Statistic                 | History   | Step 5 (independent) (inside?)   | Step 6 (linked) (inside?)   |
|:--------------------------|:----------|:---------------------------------|:----------------------------|
| Mean (EUR/MWh)            | 90.4      | 90.6 (yes)                       | 91.4 (yes)                  |
| Standard deviation        | 57.6      | 56.0 (yes)                       | 57.2 (yes)                  |
| 1% quantile               | -20.1     | -41.4 (no)                       | -43.3 (no)                  |
| 5% quantile               | -0.1      | 0.9 (yes)                        | -0.4 (yes)                  |
| Median                    | 91.4      | 90.4 (yes)                       | 92.1 (yes)                  |
| 95% quantile              | 173.7     | 176.4 (yes)                      | 178.3 (no)                  |
| 99% quantile              | 246.8     | 242.5 (yes)                      | 245.7 (yes)                 |
| Share of negative hours   | 6.2%      | 4.9% (no)                        | 5.1% (no)                   |
| Autocorrelation, 1 hour   | 0.921     | 0.914 (no)                       | 0.916 (no)                  |
| Autocorrelation, 24 hours | 0.700     | 0.593 (no)                       | 0.621 (no)                  |
| Autocorrelation, 1 week   | 0.548     | 0.517 (yes)                      | 0.536 (yes)                 |

Capture rates of the parks in each complete year (median and 5-95% over paths):

|   Year | Park       |   History | Step 5 (independent)   | Step 6 (linked)     |
|-------:|:-----------|----------:|:-----------------------|:--------------------|
|   2024 | Solar park |     0.622 | 0.572 (0.530-0.607)    | 0.542 (0.513-0.568) |
|   2024 | Wind park  |     0.827 | 1.000 (0.978-1.023)    | 0.865 (0.845-0.883) |
|   2025 | Solar park |     0.555 | 0.617 (0.585-0.646)    | 0.575 (0.548-0.599) |
|   2025 | Wind park  |     0.881 | 1.021 (0.998-1.040)    | 0.893 (0.875-0.911) |

History outside the Step 6 range: solar park 2024 (0.622 vs 0.513-0.568), wind park 2024 (0.827 vs 0.845-0.883).

## 3. Delivery year 2027: 496 scenarios

31 weather years (1995-2025) x 16 price paths
= 496 scenarios; forward 140.2 EUR/MWh, level uncertainty
0.12. The same scenarios with prices independent of the weather
(Step 5 model) for comparison.

| Park       | Prices      |   Fair PaP price (EUR/MWh) | Capture rate 5/50/95%   | Revenue P10/P50/P90 (EUR m)   |   Corr(energy, baseload price) |
|:-----------|:------------|---------------------------:|:------------------------|:------------------------------|-------------------------------:|
| Solar park | independent |                     100.99 | 0.660 / 0.716 / 0.756   | 4.21 / 5.52 / 6.97            |                           0    |
| Solar park | linked      |                      97.45 | 0.631 / 0.691 / 0.733   | 3.99 / 5.33 / 6.77            |                          -0.03 |
| Wind park  | independent |                     142.84 | 0.992 / 1.013 / 1.034   | 12.38 / 15.69 / 19.39         |                           0    |
| Wind park  | linked      |                     128.54 | 0.888 / 0.913 / 0.932   | 11.18 / 14.05 / 17.47         |                          -0.12 |

- Ignoring the weather link overstates the fair pay-as-produced price by
  3.54 EUR/MWh (solar park) and 14.30 EUR/MWh (wind park).
- Monte Carlo standard error of the linked fair prices:
  solar park 0.88 EUR/MWh, wind park 0.98 EUR/MWh.
- Does the latest historical capture rate fall inside the linked range?
  Solar park: 2025 history 0.555, linked 5-95% 0.631 to 0.733 (outside); Wind park: 2025 history 0.881, linked 5-95% 0.888 to 0.932 (outside). The comparison mixes in the price level: 2027 is simulated at 140 EUR/MWh, 2025 averaged 89, and in this model the capture rate rises with the level (Step 7 shows the sensitivity); the validation above is the test.

Per-scenario results: `data/processed/scenarios_2027.parquet` (input for Step 7).

### Sensitivity: which historical days represent 2027?

Intraday patterns come from the analog pool. Midday solar dips deepened year by year as
solar capacity grew, so the pool's period matters. The base case above uses the whole
calibration window (as in the validation).

| Analog days from            |   Days in pool |   Solar park: fair price |   Solar park: median capture rate |   Wind park: fair price |   Wind park: median capture rate |
|:----------------------------|---------------:|-------------------------:|----------------------------------:|------------------------:|---------------------------------:|
| 2024-01-01 (whole window)   |            998 |                    97.45 |                             0.691 |                  128.54 |                            0.913 |
| 2025-01-01 (2025 onward)    |            635 |                    93.23 |                             0.659 |                  128.48 |                            0.912 |
| 2025-10-01 (last 12 months) |            363 |                    89.13 |                             0.632 |                  127.9  |                            0.908 |

## 4. Charts

![Capture rates per scenario](figures/step06_capture_rates.png)

![The weather-price link in daily data](figures/step06_link.png)

![Convergence of the fair price](figures/step06_convergence.png)
