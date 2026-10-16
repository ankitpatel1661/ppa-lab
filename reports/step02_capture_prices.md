# Step 2 report: capture prices of German solar and wind

Generated 2026-10-16 07:37 UTC by `ppa-lab capture`.
Data: CC BY 4.0 - Bundesnetzagentur | SMARD.de, via Energy-Charts (Fraunhofer ISE). Bidding zone DE-LU,
delivery days 2021-01-01 to 2026-09-30 (local time, Europe/Berlin).
Official market values: netztransparenz.de (file `netztransparenz_market_values_monthly.csv`).

Capture price = sum(price x energy) / sum(energy) over the quarter-hours of the period;
capture rate = capture price / time-weighted base price. Technologies:
Solar, Wind onshore, Wind offshore.

## 1. Capture prices and capture rates by year

| Year             | Technology    |   Base price (EUR/MWh) |   Capture price (EUR/MWh) |   Capture rate |   Energy (TWh) | Energy at negative prices   |
|:-----------------|:--------------|-----------------------:|--------------------------:|---------------:|---------------:|:----------------------------|
| 2021             | Solar         |                  96.85 |                     75.99 |          0.785 |           45.3 | 4.2%                        |
| 2021             | Wind onshore  |                  96.85 |                     80.74 |          0.834 |           90.3 | 3.7%                        |
| 2021             | Wind offshore |                  96.85 |                     92.36 |          0.954 |           24   | 2.3%                        |
| 2022             | Solar         |                 235.45 |                    220.99 |          0.939 |           54.3 | 1.6%                        |
| 2022             | Wind onshore  |                 235.45 |                    168.31 |          0.715 |           97.2 | 1.7%                        |
| 2022             | Wind offshore |                 235.45 |                    194.47 |          0.826 |           24.8 | 1.1%                        |
| 2023             | Solar         |                  95.18 |                     72.25 |          0.759 |           53.9 | 8.3%                        |
| 2023             | Wind onshore  |                  95.18 |                     78.44 |          0.824 |          115.9 | 5.8%                        |
| 2023             | Wind offshore |                  95.18 |                     86.56 |          0.91  |           23.5 | 4.1%                        |
| 2024             | Solar         |                  78.51 |                     46.48 |          0.592 |           59.7 | 18.3%                       |
| 2024             | Wind onshore  |                  78.51 |                     64.54 |          0.822 |          110.6 | 6.3%                        |
| 2024             | Wind offshore |                  78.51 |                     71.4  |          0.909 |           25.7 | 4.6%                        |
| 2025             | Solar         |                  89.32 |                     45.95 |          0.514 |           70.1 | 24.2%                       |
| 2025             | Wind onshore  |                  89.32 |                     77.27 |          0.865 |          105.1 | 7.6%                        |
| 2025             | Wind offshore |                  89.32 |                     85.53 |          0.958 |           26.1 | 4.4%                        |
| 2026 (to 30 Sep) | Solar         |                 107.72 |                     55.68 |          0.517 |           76.2 | 22.8%                       |
| 2026 (to 30 Sep) | Wind onshore  |                 107.72 |                     95.37 |          0.885 |           77.7 | 7.1%                        |
| 2026 (to 30 Sep) | Wind offshore |                 107.72 |                    101.65 |          0.944 |           20.5 | 5.5%                        |

## 2. Reconciliation with the official annual market values

| metric                             |   year |   ours |   published |   difference |   tolerance | status               |
|:-----------------------------------|-------:|-------:|------------:|-------------:|------------:|:---------------------|
| capture_price_solar_ct_kwh         |   2025 |  4.595 |       4.508 |        0.087 |         0.1 | within tolerance     |
| capture_price_solar_ct_kwh         |   2024 |  4.648 |       4.624 |        0.024 |         0.1 | within tolerance     |
| capture_price_solar_ct_kwh         |   2023 |  7.225 |       7.2   |        0.025 |         0.1 | within tolerance     |
| capture_price_solar_ct_kwh         |   2022 | 22.099 |      22.306 |       -0.207 |         0.1 | explained difference |
| capture_price_solar_ct_kwh         |   2021 |  7.599 |       7.552 |        0.047 |         0.1 | within tolerance     |
| capture_price_wind_onshore_ct_kwh  |   2025 |  7.727 |       7.441 |        0.286 |         0.1 | explained difference |
| capture_price_wind_onshore_ct_kwh  |   2024 |  6.454 |       6.293 |        0.161 |         0.1 | explained difference |
| capture_price_wind_onshore_ct_kwh  |   2023 |  7.844 |       7.621 |        0.223 |         0.1 | explained difference |
| capture_price_wind_onshore_ct_kwh  |   2022 | 16.831 |      16.272 |        0.559 |         0.1 | explained difference |
| capture_price_wind_onshore_ct_kwh  |   2021 |  8.074 |       7.854 |        0.22  |         0.1 | explained difference |
| capture_price_wind_offshore_ct_kwh |   2025 |  8.553 |       8.059 |        0.494 |         0.1 | explained difference |
| capture_price_wind_offshore_ct_kwh |   2024 |  7.14  |       6.777 |        0.363 |         0.1 | explained difference |
| capture_price_wind_offshore_ct_kwh |   2023 |  8.656 |       8.187 |        0.469 |         0.1 | explained difference |
| capture_price_wind_offshore_ct_kwh |   2022 | 19.447 |      18.349 |        1.098 |         0.1 | explained difference |
| capture_price_wind_offshore_ct_kwh |   2021 |  9.236 |       9.017 |        0.219 |         0.1 | explained difference |
| nonnegative_share_solar_pct        |   2025 | 75.773 |      75     |        0.773 |         1   | within tolerance     |
| nonnegative_share_solar_pct        |   2024 | 81.718 |      81     |        0.718 |         1   | within tolerance     |
| nonnegative_share_wind_onshore_pct |   2025 | 92.39  |      90     |        2.39  |         1   | explained difference |
| nonnegative_share_wind_onshore_pct |   2024 | 93.708 |      92     |        1.708 |         1   | explained difference |

Every reference is within tolerance or has a documented cause.

Sources: 2025 capture_price_solar_ct_kwh: netztransparenz.de JW Solar 2025; 2024 capture_price_solar_ct_kwh: netztransparenz.de JW Solar 2024; 2023 capture_price_solar_ct_kwh: netztransparenz.de JW Solar 2023; 2022 capture_price_solar_ct_kwh: netztransparenz.de JW Solar 2022 (retrieved 15 Oct 2026); 2021 capture_price_solar_ct_kwh: netztransparenz.de JW Solar 2021 (retrieved 15 Oct 2026); 2025 capture_price_wind_onshore_ct_kwh: netztransparenz.de JW Wind an Land 2025; 2024 capture_price_wind_onshore_ct_kwh: netztransparenz.de JW Wind an Land 2024; 2023 capture_price_wind_onshore_ct_kwh: netztransparenz.de JW Wind an Land 2023; 2022 capture_price_wind_onshore_ct_kwh: netztransparenz.de JW Wind an Land 2022 (retrieved 15 Oct 2026); 2021 capture_price_wind_onshore_ct_kwh: netztransparenz.de JW Wind an Land 2021 (retrieved 15 Oct 2026); 2025 capture_price_wind_offshore_ct_kwh: netztransparenz.de JW Wind auf See 2025; 2024 capture_price_wind_offshore_ct_kwh: netztransparenz.de JW Wind auf See 2024; 2023 capture_price_wind_offshore_ct_kwh: netztransparenz.de JW Wind auf See 2023; 2022 capture_price_wind_offshore_ct_kwh: netztransparenz.de JW Wind auf See 2022 (retrieved 15 Oct 2026); 2021 capture_price_wind_offshore_ct_kwh: netztransparenz.de JW Wind auf See 2021 (retrieved 15 Oct 2026); 2025 nonnegative_share_solar_pct: Roedl & Partner, Wind + Sonne = Strom, Feb 2026: PV-Vermarktungsmenge 2025 = 75 %; 2024 nonnegative_share_solar_pct: Roedl & Partner, Feb 2026: PV-Vermarktungsmenge 2024 = 81 %; 2025 nonnegative_share_wind_onshore_pct: Roedl & Partner, Feb 2026: Wind-an-Land-Vermarktungsmenge 2025 = 90 %; 2024 nonnegative_share_wind_onshore_pct: Roedl & Partner, Feb 2026: Wind-an-Land-Vermarktungsmenge 2024 = 92 %.

## 3. Monthly comparison with the official market values

68 complete months compared (Jan 2021 to Aug 2026).

| Series        |   Months |   Mean difference (ct/kWh) |   Mean absolute difference |   Months within ±0.10 | Largest difference   |
|:--------------|---------:|---------------------------:|---------------------------:|----------------------:|:---------------------|
| Spot (base)   |       68 |                     -0.017 |                      0.017 |                    67 | -1.156 (Jun 2024)    |
| Solar         |       68 |                      0.044 |                      0.059 |                    56 | +0.590 (Apr 2026)    |
| Wind offshore |       68 |                      0.506 |                      0.51  |                     9 | +1.646 (Apr 2026)    |
| Wind onshore  |       68 |                      0.306 |                      0.317 |                    14 | +1.428 (Apr 2026)    |

## 4. What the numbers say

- **Solar:** capture rate 0.78 in 2021 and 0.51 in 2025; in 2025 it earned 43.37 EUR/MWh less than baseload, and 24.2% of its energy was produced at negative prices.
- **Wind onshore:** capture rate 0.83 in 2021 and 0.87 in 2025; in 2025 it earned 12.05 EUR/MWh less than baseload, and 7.6% of its energy was produced at negative prices.
- **Wind offshore:** capture rate 0.95 in 2021 and 0.96 in 2025; in 2025 it earned 3.79 EUR/MWh less than baseload, and 4.4% of its energy was produced at negative prices.

## 5. Charts

![Capture rate by month](figures/step02_capture_rate_monthly.png)

![Difference to the official market values](figures/step02_official_gap.png)

![Solar cannibalisation](figures/step02_solar_cannibalisation.png)
