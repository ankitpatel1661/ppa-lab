# Step 5 report: stochastic price model

Generated 2026-10-14 07:00 UTC by `ppa-lab prices`.
Data: CC BY 4.0 - Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE). Hourly day-ahead prices (quarter-hours averaged).

## 1. Model and calibration

y = arcsinh(P / 120) = monthly level + daily shape (season x day type x hour)
\+ daily factor D (AR(1) across days) + intraday pattern (whole historical days, same season).

| Item | Value |
|---|---|
| Calibration window | 2024-01-01 to 2026-09-30 (24,095 hours) |
| Daily factor: AR(1) coefficient phi | 0.521 per day |
| Daily factor: half-life | 1.06 days |
| Daily shock standard deviation by season | autumn 0.174, spring 0.137, summer 0.117, winter 0.149 |
| Historical days in the resampling pool | 998 |
| Saved parameters | `data/processed/price_model.json` |

## 2. Validation against history (calibration window, 200 paths)

Same calendar and monthly levels as history; does history fall inside the 5-95% range
of the simulated paths?

| Statistic                 | History   | Model (mean)   | Model 5-95% range   | History inside?   |
|:--------------------------|:----------|:---------------|:--------------------|:------------------|
| Mean (EUR/MWh)            | 90.4      | 90.6           | 88.2 to 92.8        | yes               |
| Standard deviation        | 57.6      | 56.0           | 54.0 to 58.2        | yes               |
| 1% quantile               | -20.1     | -41.4          | -46.7 to -35.6      | no                |
| 5% quantile               | -0.1      | 0.9            | -2.4 to 3.9         | yes               |
| Median                    | 91.4      | 90.4           | 88.4 to 92.6        | yes               |
| 95% quantile              | 173.7     | 176.4          | 172.2 to 181.1      | yes               |
| 99% quantile              | 246.8     | 242.5          | 231.7 to 254.3      | yes               |
| Share of negative hours   | 6.2%      | 4.9%           | 4.3% to 5.4%        | no                |
| Autocorrelation, 1 hour   | 0.921     | 0.914          | 0.910 to 0.919      | no                |
| Autocorrelation, 24 hours | 0.700     | 0.593          | 0.570 to 0.617      | no                |
| Autocorrelation, 1 week   | 0.548     | 0.517          | 0.482 to 0.549      | yes               |

Outside the range: 1% quantile, Share of negative hours, Autocorrelation, 1 hour, Autocorrelation, 24 hours.

## 3. Delivery year 2027

Forward assumption **85.0 EUR/MWh** (illustrative until Step 8), level
uncertainty 0.12 (transformed units), 500 paths.

| Item | Value |
|---|---|
| Average simulated price | 84.91 EUR/MWh |
| Annual average per path, 5% / 50% / 95% | 55.9 / 84.2 / 117.5 EUR/MWh |
| Hourly prices, 1% / 99% quantile | -47.2 / 239.0 EUR/MWh |
| Share of negative hours | 5.7% |

## 4. Teaser for Step 6: what solar earns under these prices

The solar park's 2025 weather year priced with the simulated 2027 paths gives a capture rate of **0.612** (5-95%: 0.446 to 0.693). With the real 2025 prices it was **0.555**. The model knows the average midday dip, but not that sunny days are cheaper than cloudy ones: prices and weather are still independent. Step 6 links them.

## 5. Charts

![Daily profile](figures/step05_profile.png)

![Distribution](figures/step05_distribution.png)

![Sample paths](figures/step05_paths.png)
