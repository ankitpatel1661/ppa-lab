# Step 5 report: stochastic price model

Generated 2026-10-15 20:40 UTC by `ppa-lab prices`.
Data: CC BY 4.0 - Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE). Hourly day-ahead prices (quarter-hours averaged).

## 1. Model and calibration

y = arcsinh(P / 120) = monthly level + daily shape (season x day type x hour)
\+ daily factor D (AR(1) across days) + intraday pattern (whole historical days, same season).
Negative prices have their own scale: y = −a arcsinh(|P| / 15), with a so that −500 EUR/MWh maps where it does with 120 (the choice of b: Step 6 report, section 3).


| Item | Value |
|---|---|
| Calibration window | 2024-01-01 to 2026-09-30 (24,095 hours) |
| Daily factor: AR(1) coefficient phi | 0.511 per day |
| Daily factor: half-life | 1.03 days |
| Daily shock standard deviation by season | autumn 0.179, spring 0.154, summer 0.132, winter 0.149 |
| Historical days in the resampling pool | 998 |
| Saved parameters | `data/processed/price_model.json` |

## 2. Validation against history (calibration window, 200 paths)

Same calendar and monthly levels as history; does history fall inside the 5-95% range
of the simulated paths?

| Statistic                 | History   | Model (mean)   | Model 5-95% range   | History inside?   |
|:--------------------------|:----------|:---------------|:--------------------|:------------------|
| Mean (EUR/MWh)            | 90.4      | 91.1           | 88.8 to 93.4        | yes               |
| Standard deviation        | 57.6      | 55.9           | 54.0 to 58.0        | yes               |
| 1% quantile               | -20.1     | -18.4          | -20.8 to -15.9      | yes               |
| 5% quantile               | -0.1      | -1.4           | -2.4 to -0.5        | no                |
| Median                    | 91.4      | 89.8           | 87.6 to 92.1        | yes               |
| 95% quantile              | 173.7     | 179.6          | 175.5 to 184.0      | no                |
| 99% quantile              | 246.8     | 246.4          | 236.3 to 257.2      | yes               |
| Share of negative hours   | 6.2%      | 5.9%           | 5.3% to 6.5%        | yes               |
| Autocorrelation, 1 hour   | 0.921     | 0.916          | 0.912 to 0.920      | no                |
| Autocorrelation, 24 hours | 0.700     | 0.607          | 0.584 to 0.632      | no                |
| Autocorrelation, 1 week   | 0.548     | 0.527          | 0.493 to 0.562      | yes               |

Outside the range: 5% quantile, 95% quantile, Autocorrelation, 1 hour, Autocorrelation, 24 hours.

## 3. Delivery year 2027

Forward: **EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai)**; level uncertainty 0.12 (transformed units),
500 paths.

| Item | Value |
|---|---|
| Average simulated price | 140.43 EUR/MWh |
| Annual average per path, 5% / 50% / 95% | 105.4 / 139.3 / 180.6 EUR/MWh |
| Hourly prices, 1% / 99% quantile | -14.8 / 347.9 EUR/MWh |
| Share of negative hours | 3.8% |

## 4. Teaser for Step 6: what solar earns under these prices

The solar park's 2025 weather year priced with the simulated 2027 paths gives a capture rate of **0.580** (5-95%: 0.510 to 0.627). With the real 2025 prices it was **0.542**. The model knows the average midday dip, but not that sunny days are cheaper than cloudy ones: prices and weather are still independent. Step 6 links them. Part of the gap is the level: the paths average 140 EUR/MWh, 2025 averaged 89, and in this model the capture rate rises with the level (Step 7 shows the sensitivity).

## 5. Charts

![Daily profile](figures/step05_profile.png)

![Distribution](figures/step05_distribution.png)

![Sample paths](figures/step05_paths.png)
