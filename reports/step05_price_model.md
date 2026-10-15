# Step 5 report: stochastic price model

Generated 2026-10-15 20:14 UTC by `ppa-lab prices`.
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
| Mean (EUR/MWh)            | 90.4      | 91.1           | 88.7 to 93.3        | yes               |
| Standard deviation        | 57.6      | 55.6           | 53.6 to 57.8        | yes               |
| 1% quantile               | -20.1     | -19.4          | -22.0 to -16.7      | yes               |
| 5% quantile               | -0.1      | -1.6           | -2.6 to -0.7        | no                |
| Median                    | 91.4      | 90.4           | 88.3 to 92.8        | yes               |
| 95% quantile              | 173.7     | 178.1          | 173.8 to 182.6      | no                |
| 99% quantile              | 246.8     | 245.2          | 235.1 to 256.2      | yes               |
| Share of negative hours   | 6.2%      | 6.0%           | 5.4% to 6.6%        | yes               |
| Autocorrelation, 1 hour   | 0.921     | 0.915          | 0.910 to 0.919      | no                |
| Autocorrelation, 24 hours | 0.700     | 0.590          | 0.566 to 0.614      | no                |
| Autocorrelation, 1 week   | 0.548     | 0.511          | 0.477 to 0.545      | no                |

Outside the range: 5% quantile, 95% quantile, Autocorrelation, 1 hour, Autocorrelation, 24 hours, Autocorrelation, 1 week.

## 3. Delivery year 2027

Forward: **EEX German Power Cal-27 base 140.21 EUR/MWh (quote of 2026-10-09, via tacto.ai)**; level uncertainty 0.12 (transformed units),
500 paths.

| Item | Value |
|---|---|
| Average simulated price | 140.41 EUR/MWh |
| Annual average per path, 5% / 50% / 95% | 105.3 / 139.3 / 180.6 EUR/MWh |
| Hourly prices, 1% / 99% quantile | -7.5 / 343.5 EUR/MWh |
| Share of negative hours | 2.3% |

## 4. Teaser for Step 6: what solar earns under these prices

The solar park's 2025 weather year priced with the simulated 2027 paths gives a capture rate of **0.700** (5-95%: 0.645 to 0.740). With the real 2025 prices it was **0.542**. The model knows the average midday dip, but not that sunny days are cheaper than cloudy ones: prices and weather are still independent. Step 6 links them. Part of the gap is the level: the paths average 140 EUR/MWh, 2025 averaged 89, and in this model the capture rate rises with the level (Step 7 shows the sensitivity).

## 5. Charts

![Daily profile](figures/step05_profile.png)

![Distribution](figures/step05_distribution.png)

![Sample paths](figures/step05_paths.png)
